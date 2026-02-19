import asyncio
import logging

from services.audio_capture import YouTubeAudioCapture, AudioFileCapture
from services.speech_to_text import BatchSpeechToText
from services.dataset_collector import DatasetCollector
from services.text_to_speech import TeluguTTSService
from services.race_context import RaceContextEngine

logger = logging.getLogger(__name__)


class CommentaryPipeline:
    """Orchestrates the full commentary pipeline:
    Audio → STT → Race Context → Translation (Sarvam-m) → TTS (Bulbul) → Broadcast

    Works as a streaming pipeline — no need to know video length.
    Single pipeline architecture: one Telugu audio stream broadcast to all clients.
    """

    def __init__(
        self,
        broadcast_audio_fn,
        broadcast_leaderboard_fn=None,
        broadcast_commentary_fn=None,
        race_name: str = None,
    ):
        self.broadcast_audio = broadcast_audio_fn
        self.broadcast_leaderboard = broadcast_leaderboard_fn
        self.broadcast_commentary = broadcast_commentary_fn  # English + Telugu text pair
        self.race_name = race_name

        self._stt_service = None
        self._dataset_collector = None
        self._tts_service = None
        self._race_context = None

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

    @property
    def race_context(self):
        if self._race_context is None:
            self._race_context = RaceContextEngine()
        return self._race_context

    async def _start_race_context(self):
        """Start race context engine and begin leaderboard broadcast loop."""
        await self.race_context.start()
        asyncio.create_task(self._leaderboard_broadcast_loop())

    async def _leaderboard_broadcast_loop(self):
        """Push leaderboard updates to frontend every 10 seconds."""
        while self._running:
            leaderboard = self.race_context.get_leaderboard()
            if leaderboard and self.broadcast_leaderboard:
                await self.broadcast_leaderboard(leaderboard)
                # Keep dataset collector context in sync
                if self._dataset_collector:
                    self._dataset_collector.update_race_context(leaderboard)
            await asyncio.sleep(10)

    async def process_sentence(self, english_text: str):
        """English text → classify → Telugu text (Sarvam-m) → audio (Bulbul) → broadcast"""
        try:
            logger.info(f"Processing: {english_text[:80]}...")

            # Inject live race context into the commentary prompt
            context = self.race_context.get_context_string() if self._race_context else ""

            telugu_text = await self.dataset_collector.generate_telugu_commentary(
                english_text, context=context
            )

            if not telugu_text:
                logger.info("Filler detected, skipping TTS/broadcast")
                return

            # Broadcast text pair (Telugu + English side by side on frontend)
            if self.broadcast_commentary:
                await self.broadcast_commentary(
                    english=english_text, telugu=telugu_text
                )

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

        # Start race context engine in parallel
        await self._start_race_context()

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
        context = self.race_context.get_context_string() if self._race_context else ""
        telugu_text = await self.dataset_collector.generate_telugu_commentary(
            english_text, context=context
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
        if self._race_context:
            asyncio.create_task(self._race_context.stop())
        if self._dataset_collector:
            self._dataset_collector.finish()
        logger.info("Pipeline stop requested")
