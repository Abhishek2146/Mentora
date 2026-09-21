# Group Memory Service - LLM-based memory extraction and management

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logger import get_logger
from app.services.llm_service import LLMService

logger = get_logger(__name__)

# Default empty memory structure
EMPTY_MEMORY: Dict[str, Any] = {
    "group_profile": {
        "subject": "",
        "current_topics": [],
    },
    "learning_context": {
        "weak_topics": [],
        "strong_topics": [],
        "frequently_discussed_topics": [],
    },
    "preferences": {
        "explanation_style": "simple",
        "use_examples": True,
        "preferred_language": "English",
    },
    "important_discussions": [],
    "group_goals": [],
    "ai_context": {
        "last_discussed_topic": "",
        "pending_questions": [],
    },
}

# Limits to prevent unbounded memory growth
ARRAY_LIMITS = {
    "weak_topics": 15,
    "strong_topics": 15,
    "frequently_discussed_topics": 20,
    "group_goals": 10,
    "pending_questions": 10,
    "important_discussions": 20,
    "current_topics": 10,
}

MEMORY_EXTRACTION_PROMPT = """You are a memory extraction system for an AI study group tutor.

Your job is to analyze a conversation between a study group member and the AI tutor,
and decide what useful information should be remembered for future interactions.

CURRENT GROUP MEMORY:
{current_memory}

RECENT GROUP CONVERSATION:
{conversation}

CURRENT INTERACTION:
Member asked: {question}
AI responded: {response}

TASK:
Extract ONLY meaningful, useful information that would help future tutoring sessions.
Do NOT extract trivial information. Do NOT extract every topic mentioned.

Return STRICT JSON with this exact structure:
{{
    "should_update_memory": true/false,
    "updates": {{
        "group_profile": {{
            "subject": "detected subject if clear",
            "current_topics": ["topics currently being studied"]
        }},
        "learning_context": {{
            "weak_topics": ["topics members struggle with"],
            "strong_topics": ["topics members understand well"],
            "frequently_discussed_topics": ["topics that come up often"]
        }},
        "preferences": {{
            "explanation_style": "simple/detailed/technical",
            "use_examples": true/false,
            "preferred_language": "English/etc"
        }},
        "important_discussions": [
            {{
                "topic": "topic name",
                "summary": "brief summary of the discussion",
                "created_at": "ISO timestamp"
            }}
        ],
        "group_goals": ["goals mentioned by members"],
        "ai_context": {{
            "last_discussed_topic": "most recent topic",
            "pending_questions": ["unanswered questions"]
        }}
    }}
}}

RULES:
- Only include fields that have meaningful new information
- If nothing important was learned, set should_update_memory to false
- Do NOT duplicate existing information already in the current memory
- Only return the JSON, no other text
- Keep summaries brief (max 100 chars)
- Maximum 3 important_discussions per extraction
- Maximum 3 pending_questions per extraction
"""


class MemoryService:
    """Service for managing study group memory using LLM extraction."""

    def __init__(self):
        self.llm_service = LLMService()

    def get_empty_memory(self) -> Dict[str, Any]:
        """Return a fresh empty memory structure."""
        import copy
        return copy.deepcopy(EMPTY_MEMORY)

    def format_memory_for_prompt(self, memory: Dict[str, Any]) -> str:
        """Format memory as a readable string for the AI tutor prompt."""
        if not memory or memory == {}:
            return "No group memory available yet."

        parts = []

        profile = memory.get("group_profile", {})
        if profile.get("subject"):
            parts.append(f"Subject: {profile['subject']}")
        if profile.get("current_topics"):
            parts.append(f"Current topics: {', '.join(profile['current_topics'])}")

        ctx = memory.get("learning_context", {})
        if ctx.get("weak_topics"):
            parts.append(f"Topics members find difficult: {', '.join(ctx['weak_topics'])}")
        if ctx.get("strong_topics"):
            parts.append(f"Topics members understand well: {', '.join(ctx['strong_topics'])}")
        if ctx.get("frequently_discussed_topics"):
            parts.append(f"Frequently discussed: {', '.join(ctx['frequently_discussed_topics'])}")

        prefs = memory.get("preferences", {})
        if prefs.get("explanation_style") and prefs["explanation_style"] != "simple":
            parts.append(f"Preferred explanation style: {prefs['explanation_style']}")
        if prefs.get("use_examples") is False:
            parts.append("Prefers explanations without examples")
        if prefs.get("preferred_language") and prefs["preferred_language"] != "English":
            parts.append(f"Preferred language: {prefs['preferred_language']}")

        discussions = memory.get("important_discussions", [])
        if discussions:
            recent = discussions[-3:]
            parts.append("Recent important discussions:")
            for d in recent:
                parts.append(f"  - {d.get('topic', '')}: {d.get('summary', '')}")

        goals = memory.get("group_goals", [])
        if goals:
            parts.append(f"Group goals: {'; '.join(goals)}")

        ai_ctx = memory.get("ai_context", {})
        if ai_ctx.get("last_discussed_topic"):
            parts.append(f"Last discussed topic: {ai_ctx['last_discussed_topic']}")
        if ai_ctx.get("pending_questions"):
            parts.append(f"Pending questions: {'; '.join(ai_ctx['pending_questions'])}")

        return "\n".join(parts) if parts else "No group memory available yet."

    async def extract_memory(
        self,
        current_memory: Dict[str, Any],
        conversation: str,
        question: str,
        response: str,
    ) -> Dict[str, Any]:
        """Use LLM to extract meaningful information from a conversation.

        Returns the memory update dict or empty dict if nothing to update.
        """
        try:
            prompt = MEMORY_EXTRACTION_PROMPT.format(
                current_memory=json.dumps(current_memory, indent=2),
                conversation=conversation,
                question=question,
                response=response[:1500],  # limit response length
            )

            messages = [
                {"role": "system", "content": "You are a memory extraction system. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ]

            raw = await self.llm_service.chat_completion(messages, temperature=0.3)

            # Extract JSON from response (handle markdown code blocks)
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                json_lines = []
                in_block = False
                for line in lines:
                    if line.strip().startswith("```") and not in_block:
                        in_block = True
                        continue
                    elif line.strip().startswith("```") and in_block:
                        break
                    elif in_block:
                        json_lines.append(line)
                raw = "\n".join(json_lines)

            result = json.loads(raw)

            if not isinstance(result, dict):
                logger.warning("Memory extraction returned non-dict: %s", type(result))
                return {}

            if not result.get("should_update_memory"):
                return {}

            updates = result.get("updates", {})
            if not isinstance(updates, dict):
                return {}

            return updates

        except json.JSONDecodeError as e:
            logger.warning("Memory extraction returned invalid JSON: %s", e)
            return {}
        except Exception as e:
            logger.error("Memory extraction failed: %s", str(e))
            return {}

    def merge_memory(
        self,
        existing: Dict[str, Any],
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Safely merge memory updates into existing memory.

        Rules:
        - Scalar values are overwritten
        - Lists are appended to (deduplicated)
        - important_discussions are appended (limited by ARRAY_LIMITS)
        - Nested dicts are merged recursively
        """
        if not updates:
            return existing

        import copy
        result = copy.deepcopy(existing)

        for key, new_value in updates.items():
            if key not in result:
                result[key] = new_value
                continue

            old_value = result[key]

            if isinstance(old_value, dict) and isinstance(new_value, dict):
                result[key] = self._merge_dict(old_value, new_value)
            elif isinstance(old_value, list) and isinstance(new_value, list):
                result[key] = self._merge_list(key, old_value, new_value)
            else:
                # Scalar override
                result[key] = new_value

        return result

    def _merge_dict(
        self,
        existing: Dict[str, Any],
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Recursively merge two dicts."""
        import copy
        result = copy.deepcopy(existing)

        for key, new_value in updates.items():
            if key not in result:
                result[key] = new_value
                continue

            old_value = result[key]

            if isinstance(old_value, dict) and isinstance(new_value, dict):
                result[key] = self._merge_dict(old_value, new_value)
            elif isinstance(old_value, list) and isinstance(new_value, list):
                result[key] = self._merge_list(key, old_value, new_value)
            else:
                if new_value:  # only overwrite if truthy
                    result[key] = new_value

        return result

    def _merge_list(
        self,
        key: str,
        existing: List[Any],
        new_items: List[Any],
    ) -> List[Any]:
        """Merge two lists with deduplication and size limits."""
        combined = list(existing)
        for item in new_items:
            if item not in combined:
                combined.append(item)

        limit = ARRAY_LIMITS.get(key, 20)
        return combined[:limit]

    def validate_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize memory structure.

        Ensures all expected keys exist and values are correct types.
        Removes any invalid data.
        """
        if not isinstance(memory, dict):
            return self.get_empty_memory()

        result = self.get_empty_memory()

        # Merge valid fields
        for section in ["group_profile", "learning_context", "preferences", "ai_context"]:
            if section in memory and isinstance(memory[section], dict):
                result[section] = self._merge_dict(result[section], memory[section])

        # Handle lists
        if "important_discussions" in memory:
            if isinstance(memory["important_discussions"], list):
                valid = []
                for d in memory["important_discussions"][-ARRAY_LIMITS["important_discussions"]:]:
                    if isinstance(d, dict) and "topic" in d and "summary" in d:
                        valid.append({
                            "topic": str(d["topic"])[:100],
                            "summary": str(d["summary"])[:200],
                            "created_at": d.get("created_at", ""),
                        })
                result["important_discussions"] = valid

        if "group_goals" in memory:
            if isinstance(memory["group_goals"], list):
                result["group_goals"] = [
                    str(g)[:200] for g in memory["group_goals"]
                ][:ARRAY_LIMITS["group_goals"]]

        # Enforce array limits
        for field, limit in ARRAY_LIMITS.items():
            for section in [result]:
                if field in section and isinstance(section[field], list):
                    section[field] = section[field][:limit]

        ctx = result.get("learning_context", {})
        for field in ["weak_topics", "strong_topics", "frequently_discussed_topics"]:
            if field in ctx and isinstance(ctx[field], list):
                ctx[field] = ctx[field][:limit]

        profile = result.get("group_profile", {})
        if "current_topics" in profile and isinstance(profile["current_topics"], list):
            profile["current_topics"] = profile["current_topics"][:ARRAY_LIMITS["current_topics"]]

        ai_ctx = result.get("ai_context", {})
        if "pending_questions" in ai_ctx and isinstance(ai_ctx["pending_questions"], list):
            ai_ctx["pending_questions"] = ai_ctx["pending_questions"][:ARRAY_LIMITS["pending_questions"]]

        return result
