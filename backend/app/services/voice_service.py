"""
Voice Learning Service - handles speech-to-text and text-to-speech
"""
import os
import tempfile
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logger import get_logger
from app.core.config import settings
from app.models.chat_history import ChatSession, ChatMessage, VoiceSession
from app.services.llm_service import LLMService

logger = get_logger(__name__)


def _setup_ffmpeg():
    """Ensure ffmpeg is in PATH for Whisper subprocess calls."""
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        target_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
        if not os.path.exists(target_exe):
            import shutil
            shutil.copy(ffmpeg_exe, target_exe)
        if ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    except Exception as e:
        logger.warning(f"Could not setup imageio-ffmpeg: {e}")

_setup_ffmpeg()


class VoiceService:
    def __init__(self):
        self.llm_service = LLMService()
        self.whisper_model = None

    async def _load_whisper(self):
        """Load whisper model lazily."""
        if not self.whisper_model:
            _setup_ffmpeg()
            import whisper
            import asyncio
            self.whisper_model = await asyncio.to_thread(whisper.load_model, settings.WHISPER_MODEL_SIZE)
        return self.whisper_model

    async def transcribe_audio(self, audio_content: bytes) -> str:
        """Transcribe audio to text using Whisper."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(audio_content)
            temp_path = f.name

        try:
            model = await self._load_whisper()
            import asyncio
            import torch
            use_fp16 = torch.cuda.is_available()
            result = await asyncio.to_thread(model.transcribe, temp_path, fp16=use_fp16)
            return result["text"]
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def text_to_speech(self, text: str, voice: str = "default") -> str:
        """Convert text to speech."""
        from gtts import gTTS

        os.makedirs(os.path.join(settings.UPLOAD_DIR, "audio"), exist_ok=True)
        file_path = os.path.join(
            settings.UPLOAD_DIR,
            "audio",
            f"tts_{voice}_{os.urandom(8).hex()}.mp3",
        )

        tts = gTTS(text=text, lang="en")
        tts.save(file_path)

        return f"/uploads/audio/{os.path.basename(file_path)}"

    async def process_voice_input(
        self,
        user_id: int,
        audio_content: bytes,
        syllabus_id: Optional[int] = None,
        session_id: Optional[int] = None,
        voice: str = "default",
        db: AsyncSession = None,
    ) -> dict:
        """Process voice input: STT -> response -> TTS."""
        transcript = await self.transcribe_audio(audio_content)

        messages = [{"role": "user", "content": transcript}]

        context = ""
        if syllabus_id:
            from app.services.vector_service import VectorService
            vs = VectorService()
            try:
                docs = vs.similarity_search(f"syllabus_{syllabus_id}", transcript, k=3)
                context = "\n".join([d.page_content for d in docs])
            except Exception:
                pass

        if context:
            messages = [
                {"role": "system", "content": f"You are a helpful AI tutor. Context: {context}"}
            ] + messages

        response = await self.llm_service.chat_completion(messages)

        audio_url = await self.text_to_speech(response, voice)

        session_result = await db.execute(
            select(ChatSession).where(
                ChatSession.user_id == user_id,
                ChatSession.syllabus_id == syllabus_id,
            )
        )
        session = session_result.scalars().first()

        if not session:
            session = ChatSession(
                user_id=user_id,
                title=transcript[:50],
                syllabus_id=syllabus_id,
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

        user_msg = ChatMessage(session_id=session.id, role="user", content=transcript, sequence=1)
        db.add(user_msg)

        ai_msg = ChatMessage(session_id=session.id, role="assistant", content=response, sequence=2)
        db.add(ai_msg)

        voice_session = VoiceSession(
            user_id=user_id,
            session_id=session.id,
            transcript=transcript,
            response_text=response,
            voice_used=voice,
        )
        db.add(voice_session)

        await db.commit()

        return {
            "transcript": transcript,
            "response": response,
            "audio_url": audio_url,
            "session_id": session.id,
        }

    async def get_user_sessions(self, user_id: int, db: AsyncSession) -> List:
        result = await db.execute(
            select(VoiceSession).where(VoiceSession.user_id == user_id)
        )
        return result.scalars().all()
