# Telugu F1 Live Commentary System - Design Document

## Project Overview

**Problem Statement:**  
Formula 1 broadcasts provide live commentary in English. Many Telugu-speaking fans would prefer to experience the race with Telugu commentary.

**Solution:**  
A real-time system that captures English F1 commentary from YouTube, translates it to Telugu using AI, converts it to natural Telugu speech, and streams it to users alongside a live leaderboard.

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT SOURCES                            │
├─────────────────────────┬───────────────────────────────────────┤
│  YouTube Live Stream    │         Formula1.com                   │
│  (English Commentary)   │         (Live Timing Data)             │
└───────────┬─────────────┴──────────────┬────────────────────────┘
            │                            │
            ▼                            ▼
┌───────────────────────┐    ┌──────────────────────────┐
│  Audio Capture        │    │  Web Scraper             │
│  (yt-dlp/Streamlink)  │    │  (Selenium/Playwright)   │
└───────────┬───────────┘    └────────────┬─────────────┘
            │                             │
            │ Audio Chunks (5-10s)        │ JSON Data (1-2s intervals)
            ▼                             ▼
┌───────────────────────┐    ┌──────────────────────────┐
│  Speech-to-Text       │    │  Race Context Store      │
│  (Whisper/Deepgram)   │    │  (Redis/In-Memory)       │
└───────────┬───────────┘    └────────────┬─────────────┘
            │                             │
            │ English Transcript          │ Race Data
            ▼                             ▼
            ┌─────────────────────────────┐
            │   AI Commentary Agent       │
            │   (GPT-4/Claude API)        │
            │   English → Telugu          │
            └──────────────┬──────────────┘
                           │
                           │ Telugu Text
                           ▼
            ┌─────────────────────────────┐
            │   Text-to-Speech Service    │
            │   (Google Cloud TTS - te-IN)│
            └──────────────┬──────────────┘
                           │
                           │ Telugu Audio Chunks
                           ▼
            ┌─────────────────────────────┐
            │   WebSocket Server          │
            │   (Socket.io/Native WS)     │
            └──────────────┬──────────────┘
                           │
                           │ Real-time Stream
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                      FRONTEND CLIENT                           │
├────────────────────────┬──────────────────────────────────────┤
│  Telugu Audio Player   │    Live Leaderboard Display          │
│  (Web Audio API)       │    (React Components)                │
└────────────────────────┴──────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Input Sources

#### A. YouTube Live Stream Capture
**Purpose:** Extract English commentary audio from live F1 broadcasts on YouTube

**Technologies:**
- `yt-dlp` - Command-line YouTube downloader with live stream support
- `streamlink` - Alternative stream extraction tool
- `Puppeteer/Playwright` - Fallback browser automation

**Implementation:**
```python
import subprocess
import asyncio

class YouTubeAudioCapture:
    def __init__(self, youtube_url):
        self.youtube_url = youtube_url
        self.process = None
    
    async def start_capture(self):
        """Start capturing audio stream from YouTube"""
        command = [
            'yt-dlp',
            '-f', 'bestaudio',
            '-o', '-',
            '--no-playlist',
            '--live-from-start',
            self.youtube_url
        ]
        
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        return self.process.stdout
    
    async def get_audio_chunks(self, chunk_duration=5):
        """Yield audio chunks of specified duration"""
        # Implementation for chunking audio data
        pass
```

**Key Challenges:**
- YouTube rate limiting and bot detection
- Stream availability and reliability
- Audio quality consistency

**Solutions:**
- Rotate user agents and use proper headers
- Implement automatic reconnection logic
- Monitor stream health and switch sources if needed

---

#### B. Formula1.com Leaderboard Scraper
**Purpose:** Extract real-time race position data, lap times, and race events

**Data Points to Capture:**
- Driver positions (1st, 2nd, 3rd, etc.)
- Lap times and sector times
- Gap to leader/car ahead
- Pit stop status
- Tire compound information
- Current lap number / Total laps
- Race status (Green flag, Safety Car, Red flag)

**Technologies:**
- Selenium or Playwright (headless browser)
- BeautifulSoup (HTML parsing)
- Redis (caching layer)

**Implementation:**
```python
from playwright.async_api import async_playwright
import asyncio

class F1LeaderboardScraper:
    def __init__(self):
        self.url = "https://www.formula1.com/en/racing/2024.html"
        self.browser = None
        self.page = None
    
    async def initialize(self):
        """Initialize headless browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        await self.page.goto(self.url)
    
    async def scrape_leaderboard(self):
        """Scrape current race positions and data"""
        leaderboard_data = {
            'timestamp': datetime.now().isoformat(),
            'current_lap': None,
            'total_laps': None,
            'positions': []
        }
        
        # Extract position data
        positions = await self.page.query_selector_all('.driver-position')
        
        for pos in positions:
            driver_data = {
                'position': await pos.get_attribute('data-position'),
                'driver_name': await pos.query_selector('.driver-name').inner_text(),
                'team': await pos.query_selector('.team-name').inner_text(),
                'gap': await pos.query_selector('.gap').inner_text(),
                'last_lap_time': await pos.query_selector('.lap-time').inner_text()
            }
            leaderboard_data['positions'].append(driver_data)
        
        return leaderboard_data
    
    async def monitor_live_updates(self, callback, interval=2):
        """Continuously monitor and push updates"""
        while True:
            data = await self.scrape_leaderboard()
            await callback(data)
            await asyncio.sleep(interval)
```

**Update Frequency:** Poll every 1-2 seconds during active race

---

### 2. Backend Processing Pipeline

#### A. Speech-to-Text Service
**Purpose:** Convert English audio to text transcripts in real-time

**Service Options:**

| Service | Latency | Accuracy | Cost | Streaming Support |
|---------|---------|----------|------|-------------------|
| OpenAI Whisper API | ~2-3s | Excellent | $0.006/min | No (batch) |
| Deepgram | <1s | Excellent | $0.0125/min | Yes |
| Google Cloud STT | ~1-2s | Very Good | $0.024/min | Yes |
| Azure Speech | ~1-2s | Very Good | $1/hour | Yes |

**Recommended:** Deepgram for lowest latency streaming

**Implementation:**
```python
from deepgram import Deepgram
import asyncio

class SpeechToTextService:
    def __init__(self, api_key):
        self.deepgram = Deepgram(api_key)
        self.transcript_buffer = []
    
    async def transcribe_stream(self, audio_stream):
        """Real-time transcription of audio stream"""
        
        deepgram_connection = await self.deepgram.transcription.live({
            'punctuate': True,
            'language': 'en',
            'model': 'nova-2',
            'encoding': 'linear16',
            'sample_rate': 16000
        })
        
        async def on_transcript(result):
            transcript = result['channel']['alternatives'][0]['transcript']
            if transcript:
                self.transcript_buffer.append(transcript)
                # Yield complete sentences
                if transcript.endswith(('.', '!', '?')):
                    complete_text = ' '.join(self.transcript_buffer)
                    self.transcript_buffer = []
                    return complete_text
        
        deepgram_connection.on('transcript_received', on_transcript)
        
        # Stream audio data
        async for chunk in audio_stream:
            deepgram_connection.send(chunk)
```

---

#### B. AI Commentary Agent
**Purpose:** Translate English commentary to natural, energetic Telugu commentary

**LLM Options:**
- OpenAI GPT-4 Turbo
- Anthropic Claude Sonnet 4
- Google Gemini Pro

**System Prompt Design:**
```python
TELUGU_COMMENTARY_SYSTEM_PROMPT = """
You are an energetic Formula 1 race commentator providing live commentary in Telugu.

Your role:
- Translate English F1 commentary to natural, conversational Telugu
- Maintain the excitement and energy of live sports broadcasting
- Use appropriate Telugu terminology mixed with F1 technical terms

F1 Terminology Guidelines:
- Keep technical terms in English when Telugu equivalent is awkward: DRS, KERS, ERS
- Use Telugu for: 
  * Overtake → ఓవర్‌టేక్ (ovartēk) or దాటడం (dāṭaḍaṁ)
  * Leader → లీడర్ (līḍar) or ముందున్నవాడు (mundunnavāḍu)
  * Pit Stop → పిట్ స్టాప్ (pit stāp)
  * Fastest Lap → వేగవంతమైన ల్యాప్ (vēgavantamaina lyāp)
  * Championship → ఛాంపియన్‌షిప్ (chāmpiyaṉṣip)
  * Safety Car → సేఫ్టీ కార్ (sēphṭī kār)

Tone Guidelines:
- Be conversational, not overly formal
- Use exclamations and emotional expressions
- Build excitement during key moments (overtakes, crashes, close finishes)
- Provide context when relevant

Current Race Context will be provided to help you give informed commentary.

Respond ONLY with Telugu commentary, nothing else.
"""
```

**Implementation:**
```python
from anthropic import Anthropic

class TeluguCommentaryAgent:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
        self.race_context = {}
    
    def update_race_context(self, leaderboard_data):
        """Update agent's knowledge of current race state"""
        self.race_context = {
            'leader': leaderboard_data['positions'][0]['driver_name'],
            'top_3': [p['driver_name'] for p in leaderboard_data['positions'][:3]],
            'current_lap': leaderboard_data['current_lap'],
            'total_laps': leaderboard_data['total_laps'],
            'recent_position_changes': self._detect_position_changes(leaderboard_data)
        }
    
    async def generate_telugu_commentary(self, english_text):
        """Convert English commentary to Telugu"""
        
        context_info = f"""
Current Race State:
- Leader: {self.race_context.get('leader', 'Unknown')}
- Top 3: {', '.join(self.race_context.get('top_3', []))}
- Lap: {self.race_context.get('current_lap', '?')} / {self.race_context.get('total_laps', '?')}
- Recent Events: {self.race_context.get('recent_position_changes', 'None')}
"""
        
        user_prompt = f"""{context_info}

English Commentary:
"{english_text}"

Provide Telugu commentary:"""
        
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0.7,
            system=TELUGU_COMMENTARY_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": user_prompt
            }]
        )
        
        telugu_commentary = message.content[0].text
        return telugu_commentary
    
    def _detect_position_changes(self, current_data):
        """Detect position changes from previous state"""
        # Implementation to track position changes
        pass
```

**Optimization Strategies:**
- Cache common phrases and translations
- Use temperature 0.7 for natural variation
- Implement retry logic for API failures
- Monitor token usage to control costs

---

#### C. Text-to-Speech Service
**Purpose:** Convert Telugu text to natural, expressive Telugu speech

**Service Comparison:**

| Service | Telugu Support | Voice Quality | Latency | Cost |
|---------|---------------|---------------|---------|------|
| Google Cloud TTS | ✅ te-IN (Wavenet) | Excellent | ~1-2s | $16/1M chars |
| Azure TTS | ✅ te-IN (Neural) | Very Good | ~1-2s | $16/1M chars |
| ElevenLabs | ⚠️ Multilingual | Excellent | ~2-3s | $0.30/1K chars |
| AWS Polly | ❌ No Telugu | N/A | N/A | N/A |

**Recommended:** Google Cloud TTS (Wavenet voices)

**Available Telugu Voices:**
- `te-IN-Standard-A` - Female (Standard quality)
- `te-IN-Standard-B` - Male (Standard quality)
- `te-IN-Wavenet-A` - Female (Premium quality)
- `te-IN-Wavenet-B` - Male (Premium quality)

**Implementation:**
```python
from google.cloud import texttospeech
import io

class TeluguTTSService:
    def __init__(self, credentials_path):
        self.client = texttospeech.TextToSpeechClient.from_service_account_json(
            credentials_path
        )
        self.voice_params = texttospeech.VoiceSelectionParams(
            language_code="te-IN",
            name="te-IN-Wavenet-B",  # Male voice for sports commentary
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )
    
    async def synthesize_speech(self, telugu_text):
        """Convert Telugu text to audio"""
        
        # Add SSML for better control
        ssml_text = f"""
        <speak>
            <prosody rate="110%" pitch="+2st">
                {telugu_text}
            </prosody>
        </speak>
        """
        
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.1,  # Slightly faster for excitement
            pitch=1.0,
            effects_profile_id=['headphone-class-device']
        )
        
        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=self.voice_params,
            audio_config=audio_config
        )
        
        return response.audio_content
    
    async def synthesize_with_cache(self, text, cache_store):
        """Use caching for repeated phrases"""
        cache_key = f"tts:{text}"
        
        # Check cache
        cached_audio = await cache_store.get(cache_key)
        if cached_audio:
            return cached_audio
        
        # Generate and cache
        audio = await self.synthesize_speech(text)
        await cache_store.set(cache_key, audio, expire=3600)
        
        return audio
```

**Audio Quality Settings:**
- Sample Rate: 24kHz (high quality)
- Bit Rate: 128kbps
- Format: MP3 or Opus (for streaming)
- Speaking Rate: 1.1x (natural for sports commentary)
- Pitch: +1 to +2 semitones (adds excitement)

---

#### D. WebSocket Server
**Purpose:** Real-time bidirectional communication between backend and frontend

**Technology:** Socket.io (built on WebSocket protocol)

**Events:**
- `audio_chunk` - Telugu audio data streaming
- `leaderboard_update` - Race position updates
- `race_event` - Special events (crashes, safety car, etc.)
- `connection_status` - Health monitoring

**Implementation:**
```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import socketio
import asyncio

# Initialize FastAPI and Socket.io
app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

# Store active connections
active_connections = set()

@sio.event
async def connect(sid, environ):
    """Handle new client connection"""
    print(f"Client connected: {sid}")
    active_connections.add(sid)
    
    # Send initial race state
    await sio.emit('race_state', {
        'status': 'connected',
        'message': 'తెలుగు కామెంటరీకి స్వాగతం!'  # Welcome to Telugu Commentary
    }, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    print(f"Client disconnected: {sid}")
    active_connections.remove(sid)

async def broadcast_audio_chunk(audio_data):
    """Broadcast Telugu audio to all connected clients"""
    await sio.emit('audio_chunk', {
        'audio': audio_data,
        'timestamp': datetime.now().isoformat()
    })

async def broadcast_leaderboard_update(leaderboard_data):
    """Broadcast leaderboard updates"""
    await sio.emit('leaderboard_update', leaderboard_data)

async def broadcast_race_event(event_type, event_data):
    """Broadcast special race events"""
    await sio.emit('race_event', {
        'type': event_type,
        'data': event_data,
        'timestamp': datetime.now().isoformat()
    })

# Main processing loop
async def commentary_pipeline():
    """Main pipeline orchestrating all components"""
    
    # Initialize components
    audio_capture = YouTubeAudioCapture(youtube_url)
    stt_service = SpeechToTextService(deepgram_key)
    commentary_agent = TeluguCommentaryAgent(anthropic_key)
    tts_service = TeluguTTSService(google_creds)
    leaderboard_scraper = F1LeaderboardScraper()
    
    # Start audio capture
    audio_stream = await audio_capture.start_capture()
    
    # Start leaderboard monitoring
    asyncio.create_task(
        leaderboard_scraper.monitor_live_updates(
            callback=broadcast_leaderboard_update,
            interval=2
        )
    )
    
    # Process audio chunks
    async for audio_chunk in audio_stream:
        # Speech to Text
        english_text = await stt_service.transcribe_stream(audio_chunk)
        
        if english_text:
            # Generate Telugu commentary
            telugu_text = await commentary_agent.generate_telugu_commentary(english_text)
            
            # Text to Speech
            telugu_audio = await tts_service.synthesize_speech(telugu_text)
            
            # Broadcast to clients
            await broadcast_audio_chunk(telugu_audio)

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
```

**Performance Considerations:**
- Use connection pooling for multiple clients
- Implement rate limiting per client
- Add buffering for smooth audio playback
- Monitor server CPU/memory usage

---

### 3. Frontend Application

#### Technology Stack
- **Framework:** React with Next.js 14
- **State Management:** Zustand or Redux Toolkit
- **WebSocket Client:** Socket.io-client
- **Audio:** Web Audio API or Howler.js
- **UI Library:** Tailwind CSS + shadcn/ui
- **Charts:** Recharts (for race statistics)

#### Component Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── AudioPlayer/
│   │   │   ├── AudioPlayer.jsx
│   │   │   ├── AudioVisualizer.jsx
│   │   │   └── VolumeControl.jsx
│   │   ├── Leaderboard/
│   │   │   ├── Leaderboard.jsx
│   │   │   ├── DriverRow.jsx
│   │   │   ├── PositionBadge.jsx
│   │   │   └── GapIndicator.jsx
│   │   ├── RaceInfo/
│   │   │   ├── RaceHeader.jsx
│   │   │   ├── TrackInfo.jsx
│   │   │   ├── LapCounter.jsx
│   │   │   └── WeatherWidget.jsx
│   │   ├── EventFeed/
│   │   │   ├── EventFeed.jsx
│   │   │   └── EventItem.jsx
│   │   └── Layout/
│   │       ├── Header.jsx
│   │       ├── Footer.jsx
│   │       └── Sidebar.jsx
│   ├── services/
│   │   ├── websocket.js
│   │   ├── audioService.js
│   │   └── storageService.js
│   ├── hooks/
│   │   ├── useWebSocket.js
│   │   ├── useAudioPlayer.js
│   │   └── useLeaderboard.js
│   ├── stores/
│   │   ├── raceStore.js
│   │   └── audioStore.js
│   ├── utils/
│   │   ├── formatters.js
│   │   └── constants.js
│   └── App.jsx
├── public/
│   └── fonts/
│       └── NotoSansTelugu/
└── package.json
```

#### Key Components Implementation

**A. Audio Player Component**
```jsx
import React, { useEffect, useRef, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

const AudioPlayer = () => {
  const audioContextRef = useRef(null);
  const sourceBufferRef = useRef([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(0.8);
  
  const { socket, isConnected } = useWebSocket();
  
  useEffect(() => {
    // Initialize Web Audio API
    audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    
    // Listen for audio chunks
    socket?.on('audio_chunk', handleAudioChunk);
    
    return () => {
      socket?.off('audio_chunk', handleAudioChunk);
      audioContextRef.current?.close();
    };
  }, [socket]);
  
  const handleAudioChunk = async ({ audio, timestamp }) => {
    if (!audioContextRef.current) return;
    
    try {
      // Decode base64 audio
      const audioData = atob(audio);
      const arrayBuffer = new ArrayBuffer(audioData.length);
      const view = new Uint8Array(arrayBuffer);
      
      for (let i = 0; i < audioData.length; i++) {
        view[i] = audioData.charCodeAt(i);
      }
      
      // Decode audio buffer
      const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);
      
      // Play audio
      playAudioBuffer(audioBuffer);
      
    } catch (error) {
      console.error('Error processing audio chunk:', error);
    }
  };
  
  const playAudioBuffer = (buffer) => {
    const source = audioContextRef.current.createBufferSource();
    const gainNode = audioContextRef.current.createGain();
    
    source.buffer = buffer;
    gainNode.gain.value = volume;
    
    source.connect(gainNode);
    gainNode.connect(audioContextRef.current.destination);
    
    source.start(0);
    setIsPlaying(true);
    
    source.onended = () => {
      setIsPlaying(false);
    };
  };
  
  const handleVolumeChange = (newVolume) => {
    setVolume(newVolume);
  };
  
  return (
    <div className="audio-player p-4 bg-gray-900 rounded-lg">
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-white text-sm">
              {isConnected ? 'తెలుగు కామెంటరీ లైవ్' : 'కనెక్ట్ అవుతోంది...'}
            </span>
          </div>
          
          {isPlaying && (
            <div className="audio-visualizer flex gap-1 h-8">
              {[...Array(20)].map((_, i) => (
                <div
                  key={i}
                  className="w-1 bg-orange-500 rounded animate-pulse"
                  style={{
                    height: `${Math.random() * 100}%`,
                    animationDelay: `${i * 0.1}s`
                  }}
                />
              ))}
            </div>
          )}
        </div>
        
        <div className="volume-control flex items-center gap-2">
          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 3.75a.75.75 0 00-1.264-.546L4.703 7H3.167a.75.75 0 00-.7.48A6.985 6.985 0 002 10c0 .887.165 1.737.468 2.52.111.29.39.48.7.48h1.535l4.033 3.796A.75.75 0 0010 16.25V3.75zM15.95 5.05a.75.75 0 00-1.06 1.061 5.5 5.5 0 010 7.778.75.75 0 001.06 1.06 7 7 0 000-9.899z" />
          </svg>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={volume}
            onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
            className="w-24"
          />
        </div>
      </div>
    </div>
  );
};

export default AudioPlayer;
```

**B. Leaderboard Component**
```jsx
import React, { useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

const Leaderboard = () => {
  const [positions, setPositions] = useState([]);
  const [currentLap, setCurrentLap] = useState(0);
  const [totalLaps, setTotalLaps] = useState(0);
  
  const { socket } = useWebSocket();
  
  useEffect(() => {
    socket?.on('leaderboard_update', handleLeaderboardUpdate);
    
    return () => {
      socket?.off('leaderboard_update', handleLeaderboardUpdate);
    };
  }, [socket]);
  
  const handleLeaderboardUpdate = (data) => {
    setPositions(data.positions);
    setCurrentLap(data.current_lap);
    setTotalLaps(data.total_laps);
  };
  
  const getPositionColor = (position) => {
    if (position === 1) return 'bg-yellow-500';
    if (position === 2) return 'bg-gray-400';
    if (position === 3) return 'bg-orange-600';
    return 'bg-gray-700';
  };
  
  return (
    <div className="leaderboard bg-gray-900 rounded-lg p-4">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-white mb-2">లీడర్‌బోర్డ్</h2>
        <div className="text-orange-500 text-lg">
          ల్యాప్: {currentLap} / {totalLaps}
        </div>
      </div>
      
      {/* Column Headers */}
      <div className="grid grid-cols-6 gap-2 text-gray-400 text-sm mb-2 px-2">
        <div>స్థానం</div>
        <div className="col-span-2">డ్రైవర్</div>
        <div>టీం</div>
        <div>గ్యాప్</div>
        <div>ల్యాప్ టైమ్</div>
      </div>
      
      {/* Driver Rows */}
      <div className="space-y-1">
        {positions.map((driver, index) => (
          <div
            key={driver.driver_name}
            className="grid grid-cols-6 gap-2 bg-gray-800 p-3 rounded items-center hover:bg-gray-750 transition-colors"
          >
            {/* Position Badge */}
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full ${getPositionColor(driver.position)} flex items-center justify-center text-white font-bold`}>
                {driver.position}
              </div>
            </div>
            
            {/* Driver Name */}
            <div className="col-span-2 text-white font-semibold">
              {driver.driver_name}
            </div>
            
            {/* Team */}
            <div className="text-gray-300 text-sm">
              {driver.team}
            </div>
            
            {/* Gap */}
            <div className="text-orange-500">
              {driver.position === 1 ? 'లీడర్' : driver.gap}
            </div>
            
            {/* Last Lap Time */}
            <div className="text-gray-400 text-sm font-mono">
              {driver.last_lap_time}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Leaderboard;
```

**C. WebSocket Hook**
```javascript
import { useEffect, useState } from 'react';
import io from 'socket.io-client';

export const useWebSocket = () => {
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  
  useEffect(() => {
    // Connect to WebSocket server
    const newSocket = io(process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000', {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });
    
    newSocket.on('connect', () => {
      console.log('Connected to server');
      setIsConnected(true);
    });
    
    newSocket.on('disconnect', () => {
      console.log('Disconnected from server');
      setIsConnected(false);
    });
    
    newSocket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });
    
    setSocket(newSocket);
    
    return () => {
      newSocket.close();
    };
  }, []);
  
  return { socket, isConnected };
};
```

**D. Main App Layout**
```jsx
import React from 'react';
import AudioPlayer from './components/AudioPlayer/AudioPlayer';
import Leaderboard from './components/Leaderboard/Leaderboard';
import RaceHeader from './components/RaceInfo/RaceHeader';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <div className="container mx-auto px-4 py-6">
        {/* Header */}
        <RaceHeader />
        
        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Left Column - Leaderboard */}
          <div className="lg:col-span-2">
            <Leaderboard />
          </div>
          
          {/* Right Column - Sidebar */}
          <div className="space-y-6">
            {/* Audio Player */}
            <AudioPlayer />
            
            {/* Additional Info */}
            <div className="bg-gray-900 rounded-lg p-4">
              <h3 className="text-white text-lg font-bold mb-2">రేసు సమాచారం</h3>
              <div className="space-y-2 text-gray-300 text-sm">
                <div className="flex justify-between">
                  <span>ట్రాక్:</span>
                  <span className="font-semibold">మోనాకో</span>
                </div>
                <div className="flex justify-between">
                  <span>సర్క్యూట్ పొడవు:</span>
                  <span className="font-semibold">3.337 km</span>
                </div>
                <div className="flex justify-between">
                  <span>మొత్తం ల్యాప్స్:</span>
                  <span className="font-semibold">78</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
```

---

## Data Flow Sequence

### Real-time Commentary Pipeline

```
1. YouTube Audio (0s)
   ↓
2. Audio Capture & Chunking (0-5s chunks)
   ↓
3. Speech-to-Text (~1-2s latency)
   ↓
4. English Text Output
   ↓
5. AI Translation to Telugu (~1-3s latency)
   ↓
6. Telugu Text Output
   ↓
7. Text-to-Speech (~1-2s latency)
   ↓
8. Telugu Audio Chunk
   ↓
9. WebSocket Broadcast (<100ms)
   ↓
10. Frontend Audio Playback

Total Latency: ~8-12 seconds behind live broadcast
```

### Leaderboard Update Pipeline

```
1. Formula1.com Live Timing
   ↓
2. Web Scraper (poll every 1-2s)
   ↓
3. Parse Position Data
   ↓
4. Detect Changes
   ↓
5. Update Race Context Store
   ↓
6. WebSocket Broadcast
   ↓
7. Frontend UI Update

Total Latency: ~2-3 seconds behind F1.com
```

---

## Technical Specifications

### Performance Requirements

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| End-to-end latency | < 10s | < 15s |
| Audio chunk processing | < 3s | < 5s |
| Leaderboard update frequency | 1-2s | 3s |
| Concurrent users | 1000+ | 500 minimum |
| Audio quality | 128 kbps MP3 | 96 kbps minimum |
| Uptime during race | 99.9% | 99% |

### Scalability Considerations

**For 1000 concurrent users:**
- **Bandwidth:** ~128 MB/s (128 kbps per user)
- **WebSocket connections:** 1000 simultaneous
- **Server Requirements:**
  - CPU: 8+ cores
  - RAM: 16+ GB
  - Network: 1 Gbps

**Cost Estimates per 2-hour Race:**

| Service | Usage | Cost |
|---------|-------|------|
| Deepgram STT | 120 minutes | $1.50 |
| Claude API (Commentary) | ~720 requests | $5-10 |
| Google Cloud TTS | ~72,000 chars | $1.15 |
| Server Hosting | 2 hours | $2-5 |
| **Total per race** | | **~$10-18** |

**Cost per user:** $0.01 - $0.02 per race (for 1000 users)

---

## Infrastructure & Deployment

### Recommended Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Load Balancer                     │
│                  (NGINX/CloudFlare)                 │
└────────────┬────────────────────────┬───────────────┘
             │                        │
             ▼                        ▼
    ┌─────────────────┐      ┌─────────────────┐
    │  Web Server 1   │      │  Web Server 2   │
    │  (FastAPI)      │      │  (FastAPI)      │
    └────────┬────────┘      └────────┬────────┘
             │                        │
             └────────┬───────────────┘
                      ▼
           ┌─────────────────────┐
           │   Redis Cluster     │
           │   (Session/Cache)   │
           └─────────────────────┘
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
    ┌──────────────┐      ┌──────────────┐
    │  Processing  │      │  Processing  │
    │  Worker 1    │      │  Worker 2    │
    └──────────────┘      └──────────────┘
```

### Technology Stack Summary

**Backend:**
- Python 3.11+
- FastAPI
- Socket.io (Python)
- Redis 7.0
- Celery (task queue)
- Docker & Docker Compose

**Frontend:**
- React 18
- Next.js 14
- TypeScript
- Tailwind CSS
- Socket.io-client

**External Services:**
- Deepgram (STT)
- Anthropic Claude API (LLM)
- Google Cloud TTS (Telugu voice)
- YouTube (video source)

**Infrastructure:**
- AWS EC2 / Google Cloud Compute
- CloudFlare CDN
- Redis Cloud
- Docker containers

### Deployment Strategy

**Development:**
```bash
# Using Docker Compose
docker-compose up -d
```

**Production:**
```bash
# Kubernetes deployment
kubectl apply -f k8s/
```

**CI/CD Pipeline:**
1. GitHub Actions for automated testing
2. Docker image building
3. Push to container registry
4. Deploy to production cluster
5. Health checks and monitoring

---

## Security & Compliance

### Data Privacy
- No user data collection beyond session info
- No PII storage
- GDPR compliant (no tracking)
- Secure WebSocket connections (WSS)

### API Security
- Rate limiting per IP
- API key rotation
- Environment variable secrets
- CORS configuration

### Content Licensing
⚠️ **Important Legal Considerations:**
- YouTube terms of service regarding content reuse
- F1 broadcasting rights
- Fair use considerations
- Potential need for licensing agreements

**Recommendation:** Consult with legal counsel before public deployment

---

## Monitoring & Analytics

### Key Metrics to Track

**System Health:**
- WebSocket connection count
- Audio processing latency
- API response times
- Error rates
- Server CPU/Memory usage

**User Engagement:**
- Concurrent viewers
- Average session duration
- Audio playback quality
- User drop-off points

### Monitoring Tools

- **Application:** Prometheus + Grafana
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana)
- **Alerts:** PagerDuty or similar
- **Error Tracking:** Sentry

---

## Future Enhancements

### Phase 2 Features
1. **Multi-language Support:** Add Tamil, Malayalam, Kannada
2. **Race Highlights:** Generate automatic highlight clips
3. **Driver Radio:** Include team radio communications
4. **Interactive Stats:** Click drivers for detailed stats
5. **Replay Mode:** Rewatch past races with Telugu commentary

### Phase 3 Features
1. **Mobile Apps:** Native iOS/Android apps
2. **AI Avatar:** Visual AI commentator
3. **Social Features:** Chat, reactions, predictions
4. **Premium Features:** Ad-free, HD audio, exclusive content
5. **Multi-camera Views:** Synchronized camera angles

### Advanced AI Features
1. **Contextual Insights:** AI explains race strategy
2. **Predictive Commentary:** AI predicts upcoming moves
3. **Personalized Commentary:** Adjust for user's favorite driver
4. **Voice Cloning:** Clone famous Telugu commentators

---

## Development Roadmap

### MVP Timeline (8-10 weeks)

**Week 1-2: Foundation**
- Set up development environment
- Configure YouTube audio capture
- Basic STT integration
- Simple translation testing

**Week 3-4: Core Pipeline**
- Integrate AI commentary agent
- Implement Telugu TTS
- Build WebSocket server
- Basic frontend layout

**Week 5-6: Leaderboard Integration**
- Build F1.com scraper
- Implement real-time updates
- Design leaderboard UI
- Connect all components

**Week 7-8: Polish & Testing**
- Optimize latency
- Error handling
- UI/UX improvements
- Load testing

**Week 9-10: Beta Launch**
- Deploy to staging
- Invite beta testers
- Gather feedback
- Bug fixes

### Post-MVP Iterations

**Month 3:** Stability improvements, performance optimization
**Month 4:** Additional features (highlights, statistics)
**Month 5:** Mobile-responsive design
**Month 6:** Public launch

---

## Testing Strategy

### Unit Tests
- Audio processing functions
- Text translation accuracy
- WebSocket message handling
- Leaderboard data parsing

### Integration Tests
- End-to-end pipeline
- API integrations
- Database operations
- WebSocket connections

### Load Testing
- Simulate 1000+ concurrent users
- Stress test audio streaming
- Test API rate limits
- Monitor server performance

### User Acceptance Testing
- Telugu native speakers for commentary quality
- F1 fans for accuracy and terminology
- UI/UX testing with target audience

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|------------|
| YouTube blocking | High | Medium | Multiple backup streams, headless browser |
| API cost overruns | Medium | High | Caching, rate limiting, cost alerts |
| Latency issues | High | Medium | Optimize pipeline, parallel processing |
| Legal concerns | High | Low | Legal consultation, fair use compliance |
| TTS quality | Medium | Low | Test multiple voices, user feedback |
| Server downtime | High | Low | Load balancing, auto-scaling, monitoring |

---

## Success Metrics

### Launch Goals (Month 1)
- 500+ concurrent users during a race
- < 12 second average latency
- 95% uptime during races
- Positive user feedback (4+ stars)

### Growth Goals (Month 6)
- 5,000+ concurrent users
- < 10 second average latency
- 99% uptime
- Active community engagement

---

## Conclusion

This Telugu F1 Live Commentary System represents an innovative application of AI technology to make Formula 1 racing more accessible to Telugu-speaking audiences. The system combines real-time audio processing, natural language translation, and text-to-speech synthesis to deliver an engaging live commentary experience.

**Key Strengths:**
- ✅ Real-time processing with acceptable latency
- ✅ High-quality Telugu voice synthesis
- ✅ Live leaderboard integration
- ✅ Scalable architecture
- ✅ Cost-effective operation

**Next Steps:**
1. Finalize technology stack choices
2. Set up development environment
3. Build MVP features in phases
4. Conduct thorough testing
5. Launch beta version
6. Gather user feedback and iterate

**Estimated Budget:**
- Development: 8-10 weeks
- Infrastructure: $50-100/month
- Per-race operating cost: $10-20
- Initial development cost: Variable (depending on team)

This project has strong potential to serve the Telugu-speaking F1 community and could be expanded to other languages and sports in the future.
