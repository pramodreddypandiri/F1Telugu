import io
import logging

import edge_tts

from config import settings

logger = logging.getLogger(__name__)


class TeluguTTSService:
    """Converts Telugu text to natural speech using Microsoft Edge TTS (free)."""

    def __init__(self):
        self.voice = settings.TTS_VOICE_NAME
        self.rate = settings.TTS_SPEAKING_RATE

    async def synthesize_speech(self, telugu_text: str) -> bytes:
        """Convert Telugu text to MP3 audio bytes.

        Args:
            telugu_text: Telugu text to convert to speech.

        Returns:
            MP3 audio bytes.
        """
        # Convert speaking rate to Edge TTS format (e.g. 1.1 → "+10%")
        rate_percent = int((self.rate - 1.0) * 100)
        rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        try:
            communicate = edge_tts.Communicate(
                telugu_text,
                voice=self.voice,
                rate=rate_str,
            )

            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            audio_data = audio_buffer.getvalue()
            logger.info(f"TTS generated {len(audio_data)} bytes of audio")
            return audio_data

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            raise
