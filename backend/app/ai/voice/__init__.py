"""
Voice module - Speech-to-text and text-to-speech
"""
from app.services.voice_service import VoiceService

voice_engine = VoiceService()

__all__ = ["voice_engine", "VoiceService"]
