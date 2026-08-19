"""
Speech Module for Zenix AI.
Provides server-side STT (Speech-to-Text) and TTS (Text-to-Speech) fallback
for environments where Web Speech API is unavailable.

Uses:
- STT: OpenAI Whisper (local) or Silero VITS (fallback)
- TTS: pyttsx3 (offline) or gTTS (online, free)
"""

import os
import io
import ssl
import json
import tempfile
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Dict, Any


# Supported Indian languages for speech
INDIAN_LANGUAGES = {
    "hi": {"name": "Hindi", "bhashini_code": "hi", "gtts_code": "hi"},
    "bn": {"name": "Bengali", "bhashini_code": "bn", "gtts_code": "bn"},
    "te": {"name": "Telugu", "bhashini_code": "te", "gtts_code": "te"},
    "mr": {"name": "Marathi", "bhashini_code": "mr", "gtts_code": "mr"},
    "ta": {"name": "Tamil", "bhashini_code": "ta", "gtts_code": "ta"},
    "gu": {"name": "Gujarati", "bhashini_code": "gu", "gtts_code": "gu"},
    "ur": {"name": "Urdu", "bhashini_code": "ur", "gtts_code": "ur"},
    "kn": {"name": "Kannada", "bhashini_code": "kn", "gtts_code": "kn"},
    "ml": {"name": "Malayalam", "bhashini_code": "ml", "gtts_code": "ml"},
    "or": {"name": "Odia", "bhashini_code": "or", "gtts_code": "or"},
    "pa": {"name": "Punjabi", "bhashini_code": "pa", "gtts_code": "pa"},
    "en": {"name": "English", "bhashini_code": "en", "gtts_code": "en"},
}


class SpeechService:
    """Server-side speech processing service."""

    def __init__(self):
        self._whisper_model = None

    def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = "hi",
        format: str = "webm",
    ) -> Dict[str, Any]:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw audio bytes (webm, wav, mp3, etc.)
            language: Target language code (hi, bn, te, etc.)
            format: Audio format (webm, wav, mp3)

        Returns:
            Dict with 'text', 'confidence', 'language' keys
        """
        # Try Whisper first (if available)
        try:
            return self._transcribe_whisper(audio_data, language, format)
        except Exception as e:
            pass

        # Fallback: Try Google Speech Recognition (free tier)
        try:
            return self._transcribe_google(audio_data, language, format)
        except Exception as e:
            pass

        # Final fallback: return error
        return {
            "text": "",
            "confidence": 0.0,
            "language": language,
            "error": "Speech recognition unavailable. Please type your message.",
        }

    def _transcribe_whisper(
        self, audio_data: bytes, language: str, format: str
    ) -> Dict[str, Any]:
        """Transcribe using OpenAI Whisper (local model)."""
        import whisper

        if self._whisper_model is None:
            self._whisper_model = whisper.load_model("base")

        # Save audio to temp file
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            result = self._whisper_model.transcribe(
                temp_path,
                language=language,
                fp16=False,
            )
            return {
                "text": result["text"].strip(),
                "confidence": result.get("segments", [{}])[0].get("avg_logprob", 0.5),
                "language": language,
            }
        finally:
            os.unlink(temp_path)

    def _transcribe_google(
        self, audio_data: bytes, language: str, format: str
    ) -> Dict[str, Any]:
        """Transcribe using Google Speech Recognition (free tier, limited)."""
        # This is a simple fallback - Google's free API is rate-limited
        # For production, use a proper STT service
        raise NotImplementedError("Google STT fallback not yet implemented")

    def synthesize_speech(
        self,
        text: str,
        language: str = "hi",
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Convert text to speech audio.

        Args:
            text: Text to synthesize
            language: Language code
            speed: Speech speed (0.5 - 2.0)

        Returns:
            Dict with 'audio_data', 'format', 'duration' keys
        """
        # Try gTTS first (Google Text-to-Speech, free)
        try:
            return self._synthesize_gtts(text, language, speed)
        except Exception as e:
            pass

        # Fallback: Try pyttsx3 (offline)
        try:
            return self._synthesize_pyttsx3(text, language, speed)
        except Exception as e:
            pass

        return {
            "audio_data": b"",
            "format": "mp3",
            "duration": 0,
            "error": "Text-to-speech unavailable.",
        }

    def _synthesize_gtts(
        self, text: str, language: str, speed: float
    ) -> Dict[str, Any]:
        """Synthesize using gTTS (Google Text-to-Speech, free)."""
        from gtts import gTTS

        lang_info = INDIAN_LANGUAGES.get(language, INDIAN_LANGUAGES["en"])
        gtts_lang = lang_info["gtts_code"]

        tts = gTTS(text=text, lang=gtts_lang, slow=(speed < 0.8))
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        return {
            "audio_data": audio_buffer.read(),
            "format": "mp3",
            "duration": len(text) * 0.05,  # Rough estimate
        }

    def _synthesize_pyttsx3(
        self, text: str, language: str, speed: float
    ) -> Dict[str, Any]:
        """Synthesize using pyttsx3 (offline TTS)."""
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", int(200 * speed))

        audio_buffer = io.BytesIO()
        engine.save_to_file(text, str(audio_buffer))
        engine.runAndWait()

        return {
            "audio_data": audio_buffer.getvalue(),
            "format": "wav",
            "duration": len(text) * 0.05,
        }

    def get_supported_languages(self) -> Dict[str, str]:
        """Return supported speech languages."""
        return {code: info["name"] for code, info in INDIAN_LANGUAGES.items()}


# Singleton instance
speech_service = SpeechService()
