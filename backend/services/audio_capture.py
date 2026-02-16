import asyncio
import logging
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)


class YouTubeAudioCapture:
    """Captures audio from a YouTube live stream using yt-dlp."""

    def __init__(self, youtube_url: str, chunk_duration: int = 5):
        self.youtube_url = youtube_url
        self.chunk_duration = chunk_duration
        self.process: subprocess.Popen | None = None
        self._running = False

    async def start_capture(self):
        """Start capturing audio stream from YouTube."""
        logger.info(f"Starting audio capture from: {self.youtube_url}")

        command = [
            "yt-dlp",
            "-f", "bestaudio",
            "-o", "-",
            "--no-playlist",
            "--quiet",
            self.youtube_url,
        ]

        self.process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._running = True
        logger.info("Audio capture started successfully")

    async def get_audio_chunks(self):
        """Yield audio chunks from the live stream.

        Each chunk is raw audio bytes of approximately `chunk_duration` seconds.
        We accumulate bytes from stdout and yield fixed-size chunks.
        """
        if not self.process or not self.process.stdout:
            raise RuntimeError("Audio capture not started. Call start_capture() first.")

        # Approximate bytes per chunk (assuming ~128kbps audio)
        bytes_per_second = 16000  # 128 kbps = 16 KB/s
        chunk_size = bytes_per_second * self.chunk_duration

        buffer = bytearray()

        while self._running:
            try:
                data = await asyncio.wait_for(
                    self.process.stdout.read(4096),
                    timeout=10.0,
                )

                if not data:
                    logger.warning("Audio stream ended")
                    break

                buffer.extend(data)

                # Yield complete chunks
                while len(buffer) >= chunk_size:
                    chunk = bytes(buffer[:chunk_size])
                    buffer = buffer[chunk_size:]
                    yield chunk

            except asyncio.TimeoutError:
                logger.warning("Audio read timeout, stream may be stalled")
                continue
            except Exception as e:
                logger.error(f"Error reading audio stream: {e}")
                break

        # Yield remaining buffer if any
        if buffer:
            yield bytes(buffer)

    async def stop(self):
        """Stop audio capture."""
        self._running = False
        if self.process:
            self.process.terminate()
            await self.process.wait()
            logger.info("Audio capture stopped")


class AudioFileCapture:
    """Captures audio from a local file - useful for testing."""

    def __init__(self, file_path: str, chunk_duration: int = 5):
        self.file_path = file_path
        self.chunk_duration = chunk_duration

    async def get_audio_chunks(self):
        """Yield audio chunks from a local file using ffmpeg."""
        # Convert to raw PCM chunks using ffmpeg
        command = [
            "ffmpeg",
            "-i", self.file_path,
            "-f", "wav",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-",
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # 16000 samples/sec * 2 bytes/sample * chunk_duration
        chunk_size = 16000 * 2 * self.chunk_duration
        buffer = bytearray()

        while True:
            data = await process.stdout.read(4096)
            if not data:
                break

            buffer.extend(data)

            while len(buffer) >= chunk_size:
                chunk = bytes(buffer[:chunk_size])
                buffer = buffer[chunk_size:]
                yield chunk

        if buffer:
            yield bytes(buffer)

        await process.wait()
