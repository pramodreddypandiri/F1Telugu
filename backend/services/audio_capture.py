import asyncio
import logging
import struct
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)


def wrap_pcm_as_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """Wrap raw PCM data with a valid WAV header."""
    data_size = len(pcm_data)
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,       # file size - 8
        b"WAVE",
        b"fmt ",
        16,                   # fmt chunk size
        1,                    # PCM format
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_data


class YouTubeAudioCapture:
    """Captures audio from a YouTube live stream using yt-dlp + ffmpeg.

    Uses a shell pipe: yt-dlp → ffmpeg → raw PCM → WAV-wrapped chunks
    Works with both live streams and regular videos.
    """

    def __init__(self, youtube_url: str, chunk_duration: int = 10):
        self.youtube_url = youtube_url
        self.chunk_duration = chunk_duration
        self._process = None
        self._running = False

    async def get_audio_chunks(self):
        """Stream audio from YouTube and yield WAV-wrapped PCM chunks."""
        self._running = True

        yt_dlp_bin = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "venv", "bin", "yt-dlp",
        )
        if not os.path.exists(yt_dlp_bin):
            yt_dlp_bin = "yt-dlp"

        # Shell pipe: yt-dlp streams audio → ffmpeg converts to raw PCM
        shell_cmd = (
            f'{yt_dlp_bin} -f bestaudio -o - --no-playlist --quiet '
            f'"{self.youtube_url}" | '
            f'ffmpeg -i pipe:0 -f s16le -acodec pcm_s16le -ar 16000 -ac 1 '
            f'-loglevel error pipe:1'
        )

        logger.info(f"Starting YouTube audio capture: {self.youtube_url}")

        self._process = await asyncio.create_subprocess_shell(
            shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        logger.info("Audio capture pipeline started (yt-dlp | ffmpeg → PCM)")

        # 16000 samples/sec * 2 bytes/sample * chunk_duration
        chunk_size = 16000 * 2 * self.chunk_duration
        buffer = bytearray()

        while self._running:
            try:
                data = await asyncio.wait_for(
                    self._process.stdout.read(4096),
                    timeout=30.0,
                )

                if not data:
                    logger.info("Audio stream ended")
                    break

                buffer.extend(data)

                while len(buffer) >= chunk_size:
                    pcm_chunk = bytes(buffer[:chunk_size])
                    buffer = buffer[chunk_size:]
                    yield wrap_pcm_as_wav(pcm_chunk)

            except asyncio.TimeoutError:
                logger.warning("Audio read timeout, stream may have ended")
                break
            except Exception as e:
                logger.error(f"Error reading audio stream: {e}")
                break

        # Yield remaining buffer
        if buffer:
            yield wrap_pcm_as_wav(bytes(buffer))

        await self.stop()

    async def stop(self):
        """Stop audio capture."""
        self._running = False
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
        logger.info("Audio capture stopped")


class AudioFileCapture:
    """Captures audio from a local file - useful for testing."""

    def __init__(self, file_path: str, chunk_duration: int = 5):
        self.file_path = file_path
        self.chunk_duration = chunk_duration

    async def get_audio_chunks(self):
        """Yield audio chunks from a local file using ffmpeg.

        Each chunk is wrapped with a WAV header so Deepgram can decode it.
        """
        # Output raw PCM (s16le) so we can wrap each chunk with a WAV header
        command = [
            "ffmpeg",
            "-i", self.file_path,
            "-f", "s16le",
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
                pcm_chunk = bytes(buffer[:chunk_size])
                buffer = buffer[chunk_size:]
                yield wrap_pcm_as_wav(pcm_chunk)

        if buffer:
            yield wrap_pcm_as_wav(bytes(buffer))

        await process.wait()
