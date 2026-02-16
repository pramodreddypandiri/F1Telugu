import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # API Keys
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # YouTube
    YOUTUBE_STREAM_URL: str = os.getenv("YOUTUBE_STREAM_URL", "")

    # Audio settings
    AUDIO_CHUNK_DURATION: int = 5  # seconds
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_FORMAT: str = "mp3"

    # TTS settings
    TTS_VOICE_NAME: str = "te-IN-MohanNeural"
    TTS_SPEAKING_RATE: float = 1.1
    TTS_PITCH: float = 1.0

    # Commentary settings
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_MAX_TOKENS: int = 500
    LLM_TEMPERATURE: float = 0.7


settings = Settings()
