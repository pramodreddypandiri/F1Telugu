import asyncio
import logging

from deepgram import DeepgramClient

from config import settings

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """Real-time speech-to-text using Deepgram's WebSocket streaming API (SDK v5)."""

    def __init__(self):
        self.client = DeepgramClient(api_key=settings.DEEPGRAM_API_KEY)
        self.transcript_buffer: list[str] = []

    async def transcribe_stream(self, audio_chunks, on_sentence):
        """Process audio chunks through Deepgram's live transcription.

        Args:
            audio_chunks: async generator yielding audio bytes
            on_sentence: async callback called with each complete sentence
        """
        try:
            with self.client.listen.v1.connect(
                model="nova-2",
                language="en",
                punctuate="true",
                encoding="linear16",
                sample_rate=str(settings.AUDIO_SAMPLE_RATE),
                interim_results="false",
                endpointing="300",
            ) as ws:
                logger.info("Deepgram live transcription started")

                async for chunk in audio_chunks:
                    ws.send(chunk)

                    # Check for results
                    for message in ws:
                        transcript = self._extract_transcript(message)
                        if transcript:
                            await self._handle_transcript(transcript, on_sentence)

                logger.info("Deepgram transcription finished")

        except Exception as e:
            logger.error(f"Deepgram transcription error: {e}")
            raise

    def _extract_transcript(self, message) -> str | None:
        """Extract transcript text from a Deepgram message."""
        try:
            if hasattr(message, "channel"):
                return message.channel.alternatives[0].transcript
            if isinstance(message, dict):
                return message["channel"]["alternatives"][0]["transcript"]
        except (IndexError, KeyError, AttributeError):
            pass
        return None

    async def _handle_transcript(self, transcript: str, on_sentence):
        """Buffer transcripts and emit complete sentences."""
        if not transcript.strip():
            return

        logger.info(f"Transcript: {transcript}")
        self.transcript_buffer.append(transcript)

        # Emit when we have a complete sentence or buffer is large
        if transcript.rstrip().endswith((".", "!", "?")) or len(self.transcript_buffer) >= 5:
            complete_text = " ".join(self.transcript_buffer)
            self.transcript_buffer = []
            await on_sentence(complete_text)


class BatchSpeechToText:
    """Batch speech-to-text using Deepgram's pre-recorded API (SDK v5).

    Useful for testing with audio files.
    """

    def __init__(self):
        self.client = DeepgramClient(api_key=settings.DEEPGRAM_API_KEY)

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe an audio chunk to text."""
        try:
            response = self.client.listen.v1.media.transcribe_file(
                file=audio_data,
                model="nova-2",
                language="en",
                punctuate="true",
            )

            transcript = response.results.channels[0].alternatives[0].transcript
            return transcript

        except Exception as e:
            logger.error(f"Batch transcription error: {e}")
            return ""
