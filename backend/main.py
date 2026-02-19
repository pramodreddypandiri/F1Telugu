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
    version="2.2.0",
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
    """Broadcast leaderboard updates to all connected clients."""
    await sio.emit("leaderboard_update", leaderboard_data)


async def broadcast_commentary_text(english: str, telugu: str):
    """Broadcast the English + Telugu commentary text pair for side-by-side display."""
    await sio.emit(
        "commentary_text",
        {"english": english, "telugu": telugu},
    )


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
    broadcast_commentary_fn=broadcast_commentary_text,
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
    await broadcast_commentary_text(result["english"], result["telugu"])
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
    race_name: str | None = None  # e.g. "2025-bahrain-gp"


@app.post("/api/start")
async def start_pipeline(request: StartStreamRequest):
    """Start the streaming commentary pipeline from a YouTube URL.

    Works with both live streams and regular videos.
    Streams continuously until the video ends or /api/stop is called.
    Audio chunks are broadcast to all connected frontend clients via WebSocket.
    Race context (OpenF1 leaderboard) refreshes automatically every 10 seconds.
    """
    global pipeline
    if pipeline._running:
        return {"error": "Pipeline already running. Call /api/stop first."}

    # Create a fresh pipeline with the race name for dataset tagging
    pipeline = CommentaryPipeline(
        broadcast_audio_fn=broadcast_audio_chunk,
        broadcast_leaderboard_fn=broadcast_leaderboard,
        broadcast_commentary_fn=broadcast_commentary_text,
        race_name=request.race_name,
    )

    asyncio.create_task(pipeline.run_live(request.youtube_url))
    return {
        "status": "started",
        "youtube_url": request.youtube_url,
        "race_name": pipeline.dataset_collector.race_name,
        "message": "Streaming Telugu commentary to all connected clients",
    }


@app.post("/api/stop")
async def stop_pipeline():
    """Stop the running pipeline and finalize dataset collection."""
    stats = pipeline.dataset_collector.get_stats() if pipeline._dataset_collector else {}
    pipeline.stop()
    return {"status": "stopped", "dataset_stats": stats}


@app.get("/api/dataset/stats")
async def dataset_stats():
    """Get current dataset collection stats."""
    if pipeline._dataset_collector:
        return pipeline.dataset_collector.get_stats()
    return {"message": "No active dataset collection"}


@app.get("/api/race/context")
async def race_context():
    """Get current race context from OpenF1 (leaderboard + session info)."""
    if pipeline._race_context:
        return {
            "leaderboard": pipeline.race_context.get_leaderboard(),
            "context_string": pipeline.race_context.get_context_string(),
        }
    return {"message": "Race context engine not started — call /api/start first"}


if __name__ == "__main__":
    uvicorn.run(socket_app, host=settings.HOST, port=settings.PORT)
