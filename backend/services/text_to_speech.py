"""
Telugu TTS — Sarvam Bulbul
===========================
Converts Telugu commentary text to speech using Sarvam's Bulbul TTS model.
Bulbul is purpose-built for Indian languages and produces significantly more
natural Telugu prosody, intonation, and rhythm than generic TTS engines.

API reference: https://docs.sarvam.ai/api-reference-docs/text-to-speech
"""

import base64
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


class TeluguTTSService:
    """Converts Telugu text to speech using Sarvam Bulbul TTS."""

    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.speaker = settings.TTS_SPEAKER
        self.model = settings.TTS_MODEL
        self.language = settings.TTS_LANGUAGE
        self.pace = settings.TTS_PACE

    async def synthesize_speech(self, telugu_text: str) -> bytes:
        """Convert Telugu text to WAV audio bytes via Sarvam Bulbul.

        Args:
            telugu_text: Telugu text to synthesize.

        Returns:
            WAV audio bytes.
        """
        payload = {
            "inputs": [telugu_text],
            "target_language_code": self.language,
            "speaker": self.speaker,
            "model": self.model,
            "enable_preprocessing": True,
            "pace": self.pace,
            "pitch": 0,
            "loudness": 1.5,
        }

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    SARVAM_TTS_URL, json=payload, headers=headers
                )
                response.raise_for_status()

            data = response.json()
            # Bulbul returns base64-encoded audio per input
            audio_b64 = data["audios"][0]
            audio_bytes = base64.b64decode(audio_b64)
            logger.info(f"Bulbul TTS generated {len(audio_bytes)} bytes of audio")
            return audio_bytes

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Sarvam TTS HTTP error {e.response.status_code}: {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Sarvam TTS error: {e}")
            raise
