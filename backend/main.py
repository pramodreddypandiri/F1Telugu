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
    b64 = base64.b64encode(audio_data).decode("utf-8")
    logger.info(
        f"Broadcasting audio_chunk to {len(active_connections)} clients "
        f"({len(audio_data)} bytes, {len(b64)} b64 chars)"
    )
    await sio.emit(
        "audio_chunk",
        {"audio": b64},
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


@app.post("/api/test/broadcast")
async def test_broadcast(request: TestCommentaryRequest):
    """Test endpoint: translate + TTS + broadcast via WebSocket.

    Use this to test the full frontend audio playback without YouTube.
    """
    result = await pipeline.test_translation_only(request.english_text)
    await broadcast_audio_chunk(result["audio"])
    return {
        "english": result["english"],
        "telugu": result["telugu"],
        "audio_size_bytes": result["audio_size_bytes"],
        "broadcast": True,
        "connected_clients": len(active_connections),
    }


class StartStreamRequest(BaseModel):
    youtube_url: str


@app.post("/api/start")
async def start_pipeline(request: StartStreamRequest):
    """Start the streaming commentary pipeline from a YouTube URL.

    Works with both live streams and regular videos.
    Streams continuously until the video ends or /api/stop is called.
    Audio chunks are broadcast to all connected frontend clients via WebSocket.
    """
    if pipeline._running:
        return {"error": "Pipeline already running. Call /api/stop first."}

    asyncio.create_task(pipeline.run_live(request.youtube_url))
    return {
        "status": "started",
        "youtube_url": request.youtube_url,
        "message": "Streaming Telugu commentary to all connected clients",
    }


@app.post("/api/stop")
async def stop_pipeline():
    """Stop the running pipeline."""
    pipeline.stop()
    return {"status": "stopped"}


if __name__ == "__main__":
    uvicorn.run(socket_app, host=settings.HOST, port=settings.PORT)
