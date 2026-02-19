import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # API Keys
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")  # Optional: used for fast event classification

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

    # TTS settings (Sarvam Bulbul)
    TTS_SPEAKER: str = "abhilash"  # Male voice on Bulbul v2 (anushka/abhilash/manisha/vidya/arya/karun/hitesh)
    TTS_MODEL: str = "bulbul:v2"
    TTS_LANGUAGE: str = "te-IN"
    TTS_PACE: float = 1.2         # Slightly faster for live commentary energy

    # Commentary LLM settings (Sarvam-m)
    LLM_MODEL: str = "sarvam-m"
    LLM_MAX_TOKENS: int = 500
    LLM_TEMPERATURE: float = 0.7

    # Classification LLM settings (fast small model — Groq if available, else Sarvam-m)
    CLASSIFY_MODEL: str = "llama-3.1-8b-instant"  # Groq fast model for event type labelling

    # Dataset collection
    DATASET_COLLECTION: bool = True  # Enable/disable dataset logging


settings = Settings()
