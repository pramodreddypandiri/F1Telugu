import asyncio
import logging

from services.audio_capture import YouTubeAudioCapture, AudioFileCapture
from services.speech_to_text import BatchSpeechToText
from services.dataset_collector import DatasetCollector
from services.text_to_speech import TeluguTTSService

logger = logging.getLogger(__name__)


class CommentaryPipeline:
    """Orchestrates the full commentary pipeline:
    Audio → STT → Translation → TTS → Broadcast

    Works as a streaming pipeline - no need to know video length.
    """

    def __init__(self, broadcast_audio_fn, broadcast_leaderboard_fn=None, race_name: str = None):
        self.broadcast_audio = broadcast_audio_fn
        self.broadcast_leaderboard = broadcast_leaderboard_fn
        self.race_name = race_name

        self._stt_service = None
        self._dataset_collector = None
        self._tts_service = None

        self._running = False
        self._capture = None

    @property
    def stt_service(self):
        if self._stt_service is None:
            self._stt_service = BatchSpeechToText()
        return self._stt_service

    @property
    def dataset_collector(self):
        if self._dataset_collector is None:
            self._dataset_collector = DatasetCollector(race_name=self.race_name)
        return self._dataset_collector

    @property
    def tts_service(self):
        if self._tts_service is None:
            self._tts_service = TeluguTTSService()
        return self._tts_service

    async def process_sentence(self, english_text: str):
        """English text → classify → Telugu text → Telugu audio → Broadcast"""
        try:
            logger.info(f"Processing: {english_text[:80]}...")

            telugu_text = await self.dataset_collector.generate_telugu_commentary(
                english_text
            )

            if not telugu_text:
                logger.info("Filler detected, skipping TTS/broadcast")
                return

            audio_data = await self.tts_service.synthesize_speech(telugu_text)
            await self.broadcast_audio(audio_data)

            logger.info("Pipeline cycle complete")

        except Exception as e:
            logger.error(f"Pipeline error: {e}")

    async def run_live(self, youtube_url: str):
        """Run the streaming pipeline from a YouTube live stream or video.

        Continuously: capture audio → transcribe → translate → TTS → broadcast
        Runs until the stream ends or stop() is called.
        """
        self._running = True
        logger.info(f"Starting live pipeline for: {youtube_url}")

        self._capture = YouTubeAudioCapture(youtube_url, chunk_duration=10)
        chunk_num = 0

        try:
            async for chunk in self._capture.get_audio_chunks():
                if not self._running:
                    logger.info("Pipeline stopped by user")
                    break

                chunk_num += 1
                logger.info(f"Chunk {chunk_num} ({len(chunk)} bytes)")

                english_text = await self.stt_service.transcribe_audio(chunk)
                if not english_text.strip():
                    logger.info(f"Chunk {chunk_num}: no speech detected, skipping")
                    continue

                logger.info(f"Chunk {chunk_num} EN: {english_text[:80]}...")
                await self.process_sentence(english_text)

            logger.info(f"Pipeline finished after {chunk_num} chunks")

        except Exception as e:
            logger.error(f"Live pipeline error: {e}")
        finally:
            self._running = False
            if self._capture:
                await self._capture.stop()

    async def run_from_file(self, file_path: str):
        """Run the pipeline from a local audio file (for testing)."""
        self._running = True
        logger.info(f"Starting file pipeline for: {file_path}")

        capture = AudioFileCapture(file_path)

        try:
            async for chunk in capture.get_audio_chunks():
                if not self._running:
                    break

                english_text = await self.stt_service.transcribe_audio(chunk)
                if english_text.strip():
                    await self.process_sentence(english_text)

        except Exception as e:
            logger.error(f"File pipeline error: {e}")
        finally:
            self._running = False

    async def test_translation_only(self, english_text: str) -> dict:
        """Test translation + TTS without audio capture or STT."""
        telugu_text = await self.dataset_collector.generate_telugu_commentary(
            english_text
        )
        audio_data = b""
        if telugu_text:
            audio_data = await self.tts_service.synthesize_speech(telugu_text)

        return {
            "english": english_text,
            "telugu": telugu_text,
            "event_stats": self.dataset_collector.get_stats(),
            "audio_size_bytes": len(audio_data),
            "audio": audio_data,
        }

    def stop(self):
        """Stop the pipeline and finalize dataset collection."""
        self._running = False
        if self._capture:
            asyncio.create_task(self._capture.stop())
        if self._dataset_collector:
            self._dataset_collector.finish()
        logger.info("Pipeline stop requested")
