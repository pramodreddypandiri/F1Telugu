# F1 తెలుగు కామెంటరీ — Telugu F1 Live Commentary

Real-time AI pipeline that listens to live Formula 1 English commentary and delivers energetic, natural-sounding **Telugu audio commentary** with 3–5 seconds of latency.

The AI is treated as a **Telugu F1 commentator** receiving English briefing notes — not a translator. F1 technical terms (DRS, pit stop, sector time, VSC) are preserved in English within Telugu sentences.

---

## Pipeline

```
YouTube Live Stream
       │
       ▼
  yt-dlp + ffmpeg          ← Audio extraction & chunking (10s chunks)
       │
       ▼
  Deepgram nova-2           ← Speech-to-Text (English)
       │
       ▼
  Race Context Engine       ← Live leaderboard via OpenF1 API
       │
       ▼
  Sarvam-m LLM              ← Commentary rewriting (English → Telugu)
       │
       ▼
  Sarvam Bulbul TTS         ← Telugu speech synthesis
       │
       ▼
  Socket.io WebSocket       ← Real-time audio streaming (broadcast once → all clients)
       │
       ▼
  Next.js Frontend          ← Live audio + leaderboard + commentary feed
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Stream ingestion | yt-dlp, ffmpeg |
| Speech-to-Text | Deepgram nova-2 |
| Language model | Sarvam-m |
| Text-to-Speech | Sarvam Bulbul v2 (Telugu) |
| Event classification | Groq llama-3.1-8b-instant (optional) |
| Real-time transport | Socket.io |
| Backend framework | FastAPI + uvicorn |
| Frontend | Next.js (React) |
| Race data | OpenF1 API |
| Caching | Redis |

---

## Project Structure

```
F1Telugu/
├── backend/
│   ├── main.py              # FastAPI app + Socket.io server + REST endpoints
│   ├── pipeline.py          # CommentaryPipeline orchestrator
│   ├── requirements.txt
│   ├── config/
│   │   └── settings.py      # Env-based configuration
│   ├── services/
│   │   ├── audio_capture.py     # yt-dlp + ffmpeg audio chunking
│   │   ├── speech_to_text.py    # Deepgram nova-2 STT
│   │   ├── commentary_agent.py  # Sarvam-m LLM commentary rewriter
│   │   ├── text_to_speech.py    # Sarvam Bulbul TTS
│   │   ├── race_context.py      # OpenF1 leaderboard engine
│   │   └── dataset_collector.py # English→Telugu pair logging
│   ├── datasets/            # Logged commentary pairs per race
│   └── utils/
└── frontend/
    └── src/
        ├── app/
        │   └── page.tsx         # Main UI layout
        ├── components/
        │   ├── AudioPlayer/     # Live Telugu audio playback
        │   ├── CommentaryFeed/  # English + Telugu side-by-side feed
        │   ├── Leaderboard/     # Live race standings
        │   └── RaceInfo/        # Session info + connection status
        ├── hooks/
        │   └── useWebSocket.ts  # Socket.io client hook
        └── services/
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (local or hosted)
- `ffmpeg` installed and on PATH
- API keys: Deepgram, Sarvam, Groq (optional)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
DEEPGRAM_API_KEY=your_deepgram_key
SARVAM_API_KEY=your_sarvam_key
GROQ_API_KEY=your_groq_key        # Optional — used for fast event classification
REDIS_URL=redis://localhost:6379
HOST=0.0.0.0
PORT=8000
```

Start the backend:

```bash
python main.py
```

The server runs at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
```

Create a `.env.local` file in `frontend/`:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

Start the frontend:

```bash
npm run dev
```

The app runs at `http://localhost:3000`.

---

## API Reference

### Start commentary pipeline

```http
POST /api/start
Content-Type: application/json

{
  "youtube_url": "https://www.youtube.com/watch?v=LIVE_STREAM_ID",
  "race_name": "2025-bahrain-gp"
}
```

### Stop pipeline

```http
POST /api/stop
```

### Test translation (no YouTube required)

```http
POST /api/test/translate
Content-Type: application/json

{ "english_text": "Verstappen takes the lead into Turn 1!" }
```

Returns Telugu text + base64-encoded audio.

### Test broadcast (translate + push to all connected clients)

```http
POST /api/test/broadcast
Content-Type: application/json

{ "english_text": "Safety car is deployed on lap 23." }
```

### Race context / leaderboard

```http
GET /api/race/context
```

### Dataset collection stats

```http
GET /api/dataset/stats
```

### Health check

```http
GET /health
```

---

## WebSocket Events

The frontend connects via Socket.io. Events emitted by the server:

| Event | Payload | Description |
|---|---|---|
| `race_state` | `{ status, message }` | Connection confirmation |
| `audio_chunk` | `{ audio: "<base64 mp3>" }` | Telugu audio chunk to play |
| `commentary_text` | `{ english, telugu }` | Text pair for display |
| `leaderboard_update` | leaderboard array | Race standings (every 10s) |
| `race_event` | `{ type, data }` | Special race events |

---

## Configuration

Key settings in `backend/config/settings.py` (all overridable via env):

| Setting | Default | Description |
|---|---|---|
| `AUDIO_CHUNK_DURATION` | 5s | Audio chunk size fed to STT |
| `TTS_SPEAKER` | `abhilash` | Bulbul v2 voice (`abhilash`, `anushka`, `manisha`, `vidya`, `arya`, `karun`, `hitesh`) |
| `TTS_PACE` | 1.2 | Speech pace (faster = more live energy) |
| `LLM_TEMPERATURE` | 0.7 | Commentary creativity |
| `DATASET_COLLECTION` | `True` | Log English→Telugu pairs for evaluation |

---

## Dataset Collection

Every session automatically logs English→Telugu commentary pairs to `backend/datasets/`. Each entry includes:

- English transcript
- Telugu commentary output
- Event type (`hype` / `tension` / `info` / `filler`)
- Race context snapshot (driver positions, lap)
- Timestamp

These logs drive iterative **prompt evaluation** — rating output quality after each session and refining the commentator prompt, not the model.

---

## Latency Budget

| Stage | Target |
|---|---|
| Audio chunking (ffmpeg) | 0–100ms |
| Deepgram STT | 200–400ms |
| Race context injection | < 50ms |
| Sarvam-m LLM generation | 400–900ms |
| Sarvam Bulbul TTS synthesis | 300–700ms |
| WebSocket delivery | < 100ms |
| **Total end-to-end** | **~1.0–2.3 seconds** |

Perceived delay from broadcast to Telugu audio: **3–5 seconds** (includes source stream buffering).

---

## Scalability

Single pipeline architecture: one English stream → one Telugu audio stream → broadcast to all users. LLM and TTS are called **once per chunk**, not per connected user. The number of concurrent listeners does not increase API cost.

---

## Cost Estimate (per race)

| Service | Est. Cost |
|---|---|
| Deepgram nova-2 STT (~120 min) | ~$0.52 |
| Sarvam-m LLM | TBD (verify at sarvam.ai) |
| Sarvam Bulbul TTS | TBD (verify at sarvam.ai) |
| **Total API per race** | **~$1–5 (est.)** |

Full season estimate (24 races + practice/quali): ~$720–$1,560/year including hosting.
