import asyncio
import base64
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import socketio
import uvicorn

from config import settings
from pipeline import CommentaryPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Telugu F1 Live Commentary",
    description="Real-time Telugu commentary for Formula 1 races",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Socket.IO
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Track active connections
active_connections: set[str] = set()


@app.get("/")
async def root():
    return {
        "service": "Telugu F1 Live Commentary",
        "status": "running",
        "active_connections": len(active_connections),
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")
    active_connections.add(sid)
    await sio.emit(
        "race_state",
        {
            "status": "connected",
            "message": "తెలుగు కామెంటరీకి స్వాగతం!",
        },
        room=sid,
    )


@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")
    active_connections.discard(sid)


async def broadcast_audio_chunk(audio_data: bytes):
    """Broadcast Telugu audio to all connected clients."""
    await sio.emit(
        "audio_chunk",
        {
            "audio": base64.b64encode(audio_data).decode("utf-8"),
        },
    )


async def broadcast_leaderboard(leaderboard_data: dict):
    """Broadcast leaderboard updates."""
    await sio.emit("leaderboard_update", leaderboard_data)


async def broadcast_race_event(event_type: str, event_data: dict):
    """Broadcast special race events."""
    await sio.emit(
        "race_event",
        {"type": event_type, "data": event_data},
    )


# Initialize pipeline
pipeline = CommentaryPipeline(
    broadcast_audio_fn=broadcast_audio_chunk,
    broadcast_leaderboard_fn=broadcast_leaderboard,
)


class TestCommentaryRequest(BaseModel):
    english_text: str


@app.post("/api/test/translate")
async def test_translate(request: TestCommentaryRequest):
    """Test endpoint: translate English text to Telugu commentary + audio.

    Use this to test the translation + TTS pipeline without needing
    a live YouTube stream or STT.
    """
    result = await pipeline.test_translation_only(request.english_text)
    return {
        "english": result["english"],
        "telugu": result["telugu"],
        "audio_size_bytes": result["audio_size_bytes"],
        "audio_base64": base64.b64encode(result["audio"]).decode("utf-8"),
    }


@app.post("/api/start-live")
async def start_live_pipeline(youtube_url: str = ""):
    """Start the live commentary pipeline from a YouTube stream."""
    url = youtube_url or settings.YOUTUBE_STREAM_URL
    if not url:
        return {"error": "No YouTube URL provided"}

    asyncio.create_task(pipeline.run_live(url))
    return {"status": "started", "youtube_url": url}


@app.post("/api/stop")
async def stop_pipeline():
    """Stop the running pipeline."""
    pipeline.stop()
    return {"status": "stopped"}


if __name__ == "__main__":
    uvicorn.run(socket_app, host=settings.HOST, port=settings.PORT)
