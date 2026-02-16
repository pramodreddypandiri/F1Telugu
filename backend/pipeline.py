import asyncio
import logging

from services.audio_capture import YouTubeAudioCapture, AudioFileCapture
from services.speech_to_text import SpeechToTextService, BatchSpeechToText
from services.commentary_agent import TeluguCommentaryAgent
from services.text_to_speech import TeluguTTSService
from config import settings

logger = logging.getLogger(__name__)


class CommentaryPipeline:
    """Orchestrates the full commentary pipeline:
    Audio → STT → Translation → TTS → Broadcast
    """

    def __init__(self, broadcast_audio_fn, broadcast_leaderboard_fn=None):
        self.broadcast_audio = broadcast_audio_fn
        self.broadcast_leaderboard = broadcast_leaderboard_fn

        # Lazy-initialized to avoid requiring credentials at import time
        self._stt_service = None
        self._commentary_agent = None
        self._tts_service = None

        self._running = False

    @property
    def stt_service(self):
        if self._stt_service is None:
            self._stt_service = SpeechToTextService()
        return self._stt_service

    @property
    def commentary_agent(self):
        if self._commentary_agent is None:
            self._commentary_agent = TeluguCommentaryAgent()
        return self._commentary_agent

    @property
    def tts_service(self):
        if self._tts_service is None:
            self._tts_service = TeluguTTSService()
        return self._tts_service

    async def process_sentence(self, english_text: str):
        """Process a single English sentence through the pipeline.

        English text → Telugu text → Telugu audio → Broadcast
        """
        try:
            logger.info(f"Processing: {english_text[:60]}...")

            # Step 1: Translate to Telugu
            telugu_text = await self.commentary_agent.generate_telugu_commentary(
                english_text
            )

            # Step 2: Convert to speech
            audio_data = await self.tts_service.synthesize_speech(telugu_text)

            # Step 3: Broadcast to connected clients
            await self.broadcast_audio(audio_data)

            logger.info("Pipeline cycle complete")

        except Exception as e:
            logger.error(f"Pipeline error: {e}")

    async def run_live(self, youtube_url: str):
        """Run the full live pipeline from a YouTube stream."""
        self._running = True
        logger.info(f"Starting live pipeline for: {youtube_url}")

        capture = YouTubeAudioCapture(youtube_url)
        await capture.start_capture()

        try:
            await self.stt_service.transcribe_stream(
                capture.get_audio_chunks(),
                on_sentence=self.process_sentence,
            )
        except Exception as e:
            logger.error(f"Live pipeline error: {e}")
        finally:
            await capture.stop()
            self._running = False

    async def run_from_file(self, file_path: str):
        """Run the pipeline from a local audio file (for testing)."""
        self._running = True
        logger.info(f"Starting file pipeline for: {file_path}")

        capture = AudioFileCapture(file_path)
        batch_stt = BatchSpeechToText()

        try:
            async for chunk in capture.get_audio_chunks():
                if not self._running:
                    break

                # Transcribe chunk
                english_text = await batch_stt.transcribe_audio(chunk)
                if english_text.strip():
                    await self.process_sentence(english_text)

        except Exception as e:
            logger.error(f"File pipeline error: {e}")
        finally:
            self._running = False

    async def test_translation_only(self, english_text: str) -> dict:
        """Test the translation + TTS pipeline with manual text input.

        Useful for testing without audio capture or STT.
        Returns dict with telugu_text and audio_size.
        """
        telugu_text = await self.commentary_agent.generate_telugu_commentary(
            english_text
        )
        audio_data = await self.tts_service.synthesize_speech(telugu_text)

        return {
            "english": english_text,
            "telugu": telugu_text,
            "audio_size_bytes": len(audio_data),
            "audio": audio_data,
        }

    def stop(self):
        """Stop the pipeline."""
        self._running = False
        logger.info("Pipeline stopped")
