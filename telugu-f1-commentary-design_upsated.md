# Telugu F1 Live Commentary System — Design Document

**Version:** 2.2  
**Last Updated:** February 2026  
**Author:** Pramod  

---

## 1. Project Overview

### Problem Statement
Formula 1 races are broadcast exclusively in English, creating a language barrier for Telugu-speaking fans who may follow the sport but struggle to engage with fast-paced technical commentary in real time.

### Solution
A real-time AI pipeline that listens to live F1 English commentary, understands race context, and delivers energetic, natural-sounding Telugu audio commentary with minimal latency — treating the AI not as a translator but as a **Telugu F1 commentator** receiving English briefing notes.

### Goals
- Deliver Telugu commentary within **3–5 seconds** of English broadcast
- Produce **natural, energetic Telugu** — not literal word-for-word translation
- Support **live race sessions** (Practice, Qualifying, Race)
- Scale to handle **concurrent Telugu-speaking fans** without degradation
- Continuously improve output quality through prompt evaluation

---

## 2. System Architecture

### High-Level Pipeline

```
YouTube Live Stream
       │
       ▼
  yt-dlp + ffmpeg          ← Audio extraction & chunking
       │
       ▼
  Deepgram nova-2           ← Speech-to-Text (English)
       │
       ▼
  Race Context Engine       ← Live leaderboard + event classifier
       │
       ▼
  Sarvam-m LLM              ← Commentary rewriting (English → Telugu)
       │
       ▼
  Sarvam Bulbul TTS         ← Telugu speech synthesis
       │
       ▼
  Socket.io WebSocket       ← Real-time audio streaming
       │
       ▼
  React / Next.js Frontend  ← User-facing web app
```

### Key Design Principle
> The LLM is a **Telugu F1 commentator** who receives English briefing notes — not a translator.  
> F1 technical terms (DRS, pit stop, sector time, VSC) are preserved in English within Telugu sentences.

---

## 3. Component Breakdown

### 3.1 Audio Ingestion
- **Tool:** `yt-dlp` + `ffmpeg`
- **Function:** Extract audio stream from YouTube Live, chunk into 3–5 second segments
- **Output:** PCM audio buffer → Deepgram

### 3.2 Speech-to-Text
- **Service:** Deepgram nova-2
- **Language:** English
- **Mode:** Streaming (real-time)
- **Cost:** ~$0.0043/min of audio processed

### 3.3 Race Context Engine
- **Live Leaderboard:** Scraped from Formula1.com
- **Data:** Driver positions, gap times, lap count, tyre compounds, pit status
- **Event Classifier:** Labels each commentary chunk as:
  - `hype` — overtake, crash, dramatic moment
  - `tension` — battle, close gap, safety car
  - `info` — lap times, strategy, pit stop
  - `filler` — generic commentary, no action

### 3.4 LLM Commentary Rewriter
- **Service:** Sarvam-m
- **Why Sarvam-m:** Purpose-built for Indian languages including Telugu — produces more natural, culturally appropriate output vs generic multilingual models
- **Prompt Strategy:** Commentator persona, not translator. The model is instructed to behave as an energetic Telugu F1 commentator receiving English briefing notes
- **Context Injected:** Current race positions, event type, recent events, driver names
- **Output:** Telugu Unicode text
- **Quality lever:** Prompt engineering — tuning commentator persona, event-type instructions, and race context injection before considering any model changes

### 3.5 Text-to-Speech
- **Service:** Sarvam Bulbul TTS
- **Language:** Telugu
- **Why Bulbul:** Purpose-built for Indian languages — significantly more natural Telugu prosody, intonation, and rhythm compared to generic TTS engines
- **Output:** MP3/WAV audio chunk → WebSocket

### 3.6 WebSocket Delivery
- **Technology:** Socket.io
- **Pattern:** Server generates one Telugu audio stream → broadcasts to all connected clients (no per-user LLM/TTS calls)
- **Latency target:** < 500ms from TTS output to client playback

### 3.7 Frontend
- **Framework:** React / Next.js
- **Features:**
  - Live Telugu audio playback
  - Live leaderboard display
  - Session info (Race / Quali / Practice)
  - Commentary text display (Telugu + English side by side)
  - Mobile responsive

---

## 4. Budget & Cost Analysis

### 4.1 API Costs Per Race (2-hour race session)

| Service | Usage | Rate | Cost per Race |
|---|---|---|---|
| Deepgram nova-2 STT | ~120 min audio | $0.0043/min | ~$0.52 |
| Sarvam-m LLM | ~500K tokens | TBD — verify at sarvam.ai | TBD |
| Sarvam Bulbul TTS | ~120 min output audio | TBD — verify at sarvam.ai | TBD |
| **Total API Cost** | | | **~$1–5 per race (est.)** |

> ⚠️ Sarvam API pricing (Sarvam-m and Bulbul) needs to be confirmed at [sarvam.ai](https://sarvam.ai) before finalizing budget.

### 4.2 Frontend Hosting

| Option | Cost | Best For |
|---|---|---|
| Vercel (Hobby) | Free | Dev / small scale (<100 users) |
| Vercel (Pro) | $20/month | Up to 1000 users, better performance |
| Railway / Render | $5–20/month | Full-stack + WebSocket backend |
| VPS (Hetzner/DigitalOcean) | $6–20/month | Full control, Socket.io at scale |

> Note: Vercel does not support persistent Socket.io connections — the WebSocket backend must be hosted separately on a VPS or container service regardless of frontend choice.

### 4.3 Backend / WebSocket Server

| Concurrent Users | Recommended Infra | Est. Monthly Cost |
|---|---|---|
| < 50 | Single VPS (2GB RAM) | $6–10/month |
| 50–500 | Single VPS (4–8GB RAM) | $15–40/month |
| 500–5000 | Load-balanced VPS or managed container | $50–200/month |

### 4.4 Monthly Cost Summary (Race Weekend Estimate)

Assuming 1 race weekend (FP1, FP2, FP3, Quali, Race = ~8 hours of sessions):

| Item | Cost |
|---|---|
| API costs (all sessions) | ~$5–15 (pending Sarvam pricing) |
| Hosting (monthly, ~500 users) | ~$25–50 |
| **Total per race weekend** | **~$30–65** |
| **Total per F1 season (24 races)** | **~$720–1,560/year** |

---

## 5. Prompt Evaluation Pipeline

Rather than fine-tuning a model, quality improvement is driven entirely through **iterative prompt engineering** backed by a structured evaluation loop.

### 5.1 Data Logging
- Every English input → Telugu output pair is logged during live sessions
- Each pair tagged with: event type, race context, timestamp, session type

### 5.2 Evaluation Workflow
1. Review logged pairs after each race/session
2. Rate each pair (1–5 scale) for naturalness, energy, and accuracy
3. Identify patterns in low-rated outputs (e.g. flat filler commentary, awkward driver name handling)
4. Update prompt instructions to address identified weaknesses
5. Re-test on next session

### 5.3 Prompt Iteration Areas
- **Commentator persona** — energy level, Telugu expressions, exclamations
- **Event-type handling** — different tone/language for hype vs info vs filler moments
- **Technical term preservation** — ensuring F1 terms stay in English within Telugu sentences
- **Driver name handling** — natural pronunciation guidance for Telugu context
- **Race context utilization** — how well the model uses leaderboard data in commentary

### 5.4 When to Reconsider Fine-tuning
Fine-tuning should only be revisited if prompt engineering is genuinely exhausted — meaning output quality has plateaued despite multiple prompt iterations and the gap between desired and actual output cannot be bridged through instructions alone.

---

## 6. Latency Budget

| Stage | Target Latency |
|---|---|
| Audio chunking (ffmpeg) | 0–100ms |
| Deepgram STT | 200–400ms |
| Race context injection | < 50ms |
| Sarvam-m LLM generation | 400–900ms |
| Sarvam Bulbul TTS synthesis | 300–700ms |
| WebSocket delivery | < 100ms |
| **Total end-to-end** | **~1.0–2.3 seconds** |

> Perceived delay from broadcast to Telugu audio: **3–5 seconds** (includes source stream buffering)

---

## 7. Scalability Considerations

- **Single pipeline architecture:** One English audio stream → one Telugu audio stream → broadcast to all users. LLM and TTS are called once per chunk regardless of concurrent user count.
- **WebSocket rooms:** Socket.io rooms per session type (Race, Quali, Practice)
- **Audio caching:** Pre-generated audio chunks buffered server-side; clients receive the same stream
- **Race context refresh:** Leaderboard data cached and refreshed every 10 seconds

---

## 8. Tech Stack Summary

| Layer | Technology |
|---|---|
| Stream Ingestion | yt-dlp, ffmpeg |
| Speech-to-Text | Deepgram nova-2 |
| Language Model | Sarvam-m |
| Text-to-Speech | Sarvam Bulbul (Telugu) |
| Real-time Transport | Socket.io |
| Frontend | React, Next.js |
| Race Data | Formula1.com scraper |
| Hosting | Vercel (frontend) + VPS (backend/WebSocket) |

---

## 9. Open Questions / Next Steps

- [ ] Confirm Sarvam-m and Bulbul API pricing at sarvam.ai
- [ ] Finalize target concurrent user count for infra sizing
- [ ] Decide VPS provider for WebSocket backend (Hetzner / Railway / Render)
- [ ] Benchmark Sarvam-m latency for Telugu commentary generation
- [ ] Benchmark Bulbul TTS latency for Telugu audio synthesis
- [ ] Run first prompt evaluation cycle after next F1 session
- [ ] Test full pipeline end-to-end on Practice or Qualifying session

---

## 10. Risk & Mitigations

| Risk | Mitigation |
|---|---|
| YouTube stream URL changes mid-race | Auto-retry with yt-dlp on failure |
| Sarvam API rate limits or downtime | Implement queue + retry logic; cache recent audio chunks |
| Formula1.com blocks scraper | Rate limiting + user-agent rotation |
| High concurrent users overwhelm WebSocket server | Single pipeline architecture — TTS/LLM called once per chunk, not per user |
| Telugu commentary sounds unnatural | Iterative prompt engineering backed by structured evaluation loop |
| Latency spikes during race peak moments | Pre-buffer 2–3 chunks ahead; graceful degradation to text-only |

---

*This document is a living specification. Update after each major pipeline change or race test.*
