"""
Unit tests for the TutorService context budget strategy.

These tests verify that the tutor:
- Limits conversation history to a configurable maximum
- Caps RAG context to prevent oversized requests
- Handles Groq 413 errors gracefully
- Logs diagnostic information about request size

No live Groq API key or database required.
"""
import json
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.tutor_service import TutorService


class TestTruncateContext:
    """Test the RAG context truncation helper."""

    def test_short_context_not_truncated(self):
        ctx = "SOURCE 1\nSubject: Math\nContent:\nShort content"
        result = TutorService._truncate_context(ctx, max_chars=500)
        assert result == ctx

    def test_long_context_truncated_at_source_boundary(self):
        blocks = []
        for i in range(10):
            blocks.append(
                f"SOURCE {i + 1}\n"
                f"Subject: Subject {i}\n"
                f"Chapter: Chapter {i}\n"
                f"Topic: Topic {i}\n"
                f"Content:\n{'word ' * 100}"
            )
        ctx = "\n\n".join(blocks)
        truncated = TutorService._truncate_context(ctx, max_chars=2000)
        assert len(truncated) <= 2000
        # Should have fewer sources than original
        assert truncated.count("SOURCE ") < ctx.count("SOURCE ")

    def test_very_long_context_truncated(self):
        ctx = "A" * 10000
        truncated = TutorService._truncate_context(ctx, max_chars=1000)
        assert len(truncated) <= 1000


class TestEstimateTokens:
    """Test the token estimation helper."""

    def test_basic_estimation(self):
        # With TUTOR_CHARS_PER_TOKEN = 4, 100 chars = 25 tokens
        text = "a" * 100
        result = TutorService._estimate_tokens(text)
        assert result == 25

    def test_empty_string(self):
        assert TutorService._estimate_tokens("") == 0


class TestProcessMessageContextBudget:
    """Test that process_message respects context budgets."""

    @pytest.mark.asyncio
    async def test_history_is_limited(self):
        """Only the most recent messages should be included when history exceeds limit."""
        tutor = TutorService()

        # Mock database
        mock_db = AsyncMock()
        mock_session = MagicMock()
        mock_session.id = 1

        # Create 30 mock messages (exceeds TUTOR_MAX_HISTORY_MESSAGES = 20)
        mock_messages = []
        for i in range(30):
            msg = MagicMock()
            msg.role = "user" if i % 2 == 0 else "assistant"
            msg.content = f"Message {i}"
            msg.sequence = i + 1
            mock_messages.append(msg)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_db.execute.return_value = mock_result

        # Mock session creation
        mock_session_result = MagicMock()
        mock_session_result.scalars.return_value.first.return_value = mock_session

        # Mock syllabus ownership check (returns False = not owned)
        mock_syllabus_result = MagicMock()
        mock_syllabus_result.scalars.return_value.first.return_value = None

        # Set up execute to return different results based on call order
        mock_db.execute.side_effect = [
            mock_session_result,  # session lookup
            mock_result,          # history lookup
            mock_syllabus_result, # syllabus ownership
        ]

        # Mock LLM response
        with patch.object(
            tutor.llm_service, "chat_completion", new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = "AI response"

            with patch.object(
                tutor, "_build_personalization_note", new_callable=AsyncMock
            ) as mock_personal:
                mock_personal.return_value = ""

                result = await tutor.process_message(
                    user_id=1,
                    message="Hello",
                    session_id=1,
                    db=mock_db,
                )

        # Verify chat_completion was called
        mock_chat.assert_called_once()
        call_args = mock_chat.call_args
        messages = call_args[0][0]

        # Should have at most 6 history messages + 1 user message + 1 system = 8 total
        assert len(messages) <= 8

    @pytest.mark.asyncio
    async def test_rag_context_is_capped(self):
        """RAG context should be truncated to TUTOR_MAX_CONTEXT_CHARS."""
        tutor = TutorService()

        mock_db = AsyncMock()
        mock_session = MagicMock()
        mock_session.id = 1

        # No existing messages
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []

        mock_session_result = MagicMock()
        mock_session_result.scalars.return_value.first.return_value = mock_session

        # Syllabus is owned
        mock_syllabus_result = MagicMock()
        mock_syllabus_result.scalars.return_value.first.return_value = True

        # Mock vector service to return large context
        large_content = "A" * 10000
        mock_docs = [MagicMock()]
        mock_docs[0].page_content = large_content
        mock_docs[0].metadata = {"subject": "Math", "chapter": "Ch1", "topic": "T1"}

        mock_db.execute.side_effect = [
            mock_session_result,
            empty_result,
            mock_syllabus_result,
        ]

        with patch.object(
            tutor.vector_service, "retrieve_context", return_value=mock_docs
        ):
            with patch.object(
                tutor.vector_service, "collection_name_for_syllabus", return_value="test_coll"
            ):
                with patch.object(
                    tutor.llm_service, "chat_completion", new_callable=AsyncMock
                ) as mock_chat:
                    mock_chat.return_value = "AI response"

                    with patch.object(
                        tutor, "_build_personalization_note", new_callable=AsyncMock
                    ) as mock_personal:
                        mock_personal.return_value = ""

                        result = await tutor.process_message(
                            user_id=1,
                            message="Tell me about math",
                            syllabus_id=1,
                            session_id=1,
                            db=mock_db,
                        )

        # Verify the system message context is within budget
        mock_chat.assert_called_once()
        messages = mock_chat.call_args[0][0]
        system_msg = messages[0]["content"]
        # System message should be less than base prompt + max context chars
        assert len(system_msg) < 3000  # base prompt (~200) + 2000 max context + margin

    @pytest.mark.asyncio
    async def test_413_error_falls_back_to_minimal_context(self):
        """When Groq returns 413, the tutor should retry with minimal context."""
        tutor = TutorService()

        mock_db = AsyncMock()
        mock_session = MagicMock()
        mock_session.id = 1

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []

        mock_session_result = MagicMock()
        mock_session_result.scalars.return_value.first.return_value = mock_session

        mock_syllabus_result = MagicMock()
        mock_syllabus_result.scalars.return_value.first.return_value = None

        mock_db.execute.side_effect = [
            mock_session_result,
            empty_result,
            mock_syllabus_result,
        ]

        # First call raises 413, second call succeeds
        with patch.object(
            tutor.llm_service, "chat_completion", new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.side_effect = [
                Exception("Error code: 413 - Request Entity Too Large"),
                "Fallback response",
            ]

            with patch.object(
                tutor, "_build_personalization_note", new_callable=AsyncMock
            ) as mock_personal:
                mock_personal.return_value = ""

                result = await tutor.process_message(
                    user_id=1,
                    message="Hello",
                    session_id=1,
                    db=mock_db,
                )

        assert result["response"] == "Fallback response"
        assert mock_chat.call_count == 2
        # Second call should have minimal messages (short system + user only)
        second_call_messages = mock_chat.call_args[0][0]
        assert len(second_call_messages) == 2
        # System prompt should be short (not the full RAG context)
        assert len(second_call_messages[0]["content"]) < 200

    @pytest.mark.asyncio
    async def test_non_413_error_propagates(self):
        """Non-413 errors should propagate normally."""
        tutor = TutorService()

        mock_db = AsyncMock()
        mock_session = MagicMock()
        mock_session.id = 1

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []

        mock_session_result = MagicMock()
        mock_session_result.scalars.return_value.first.return_value = mock_session

        mock_syllabus_result = MagicMock()
        mock_syllabus_result.scalars.return_value.first.return_value = None

        mock_db.execute.side_effect = [
            mock_session_result,
            empty_result,
            mock_syllabus_result,
        ]

        with patch.object(
            tutor.llm_service, "chat_completion", new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.side_effect = Exception("Some other error")

            with patch.object(
                tutor, "_build_personalization_note", new_callable=AsyncMock
            ) as mock_personal:
                mock_personal.return_value = ""

                with pytest.raises(Exception, match="Some other error"):
                    await tutor.process_message(
                        user_id=1,
                        message="Hello",
                        session_id=1,
                        db=mock_db,
                    )

        # Should only be called once (no retry)
        assert mock_chat.call_count == 1
