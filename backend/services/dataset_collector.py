"""
Dataset Collection Service
===========================
Plugs into the pipeline between Deepgram (STT) and Edge TTS.
Classifies commentary by event type, generates Telugu translation, and logs
English-Telugu pairs to a JSONL file for future model fine-tuning.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from groq import Groq

from config import settings

logger = logging.getLogger(__name__)

DATASET_DIR = Path(__file__).resolve().parent.parent / "datasets"
DATASET_DIR.mkdir(exist_ok=True)

# ── Classification prompt (runs on a small fast model) ──────────────────────

CLASSIFY_PROMPT = """You are an F1 commentary classifier. Given an English commentary line, classify it into ONE of these types:

- hype: Overtakes, crashes, dramatic moments, celebrations, collisions, race wins
- tension: Close battles, gap closing, DRS zones, last few laps, wheel-to-wheel
- info: Pit stops, tire changes, strategy calls, penalties, grid positions, weather updates
- filler: Parade laps, cars circulating normally, generic observations, repetitive updates

Respond with ONLY the event type word. Nothing else."""

# ── Telugu generation prompt (energy-aware) ─────────────────────────────────

COMMENTARY_PROMPT = """You are a passionate Telugu Formula 1 commentator broadcasting LIVE on TV.

CRITICAL RULES:
1. NEVER do word-by-word translation. Rewrite as a natural Telugu commentator would say it.
2. Keep F1 terms in English: DRS, pit stop, undercut, overcut, soft/medium/hard tires, safety car, VSC, red flag, etc.
3. Keep driver names and team names in English.
4. Match your energy to the event type provided.

ENERGY GUIDE:
- [HYPE]: Go WILD! Use "అబ్బా!", "ఏమి move రా!", "అద్భుతం!", "భలే!", elongate words for emphasis. Be dramatic.
- [TENSION]: Build suspense. "చూడండి...", "gap తగ్గుతోంది...", "ఏం జరుగుతుందో...", short punchy sentences.
- [INFO]: Be clear and brief. State the fact naturally in Telugu. No need for excitement.
- [FILLER]: Output EXACTLY "##SKIP##" — do not translate filler lines.

Output ONLY the Telugu commentary. No explanations, no English, no brackets."""


def _classify_event(client: Groq, english_text: str) -> str:
    """Classify a commentary line into an event type using a small fast model."""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": CLASSIFY_PROMPT},
                {"role": "user", "content": english_text},
            ],
            max_tokens=10,
            temperature=0,
        )
        event_type = response.choices[0].message.content.strip().lower()
        if event_type not in ("hype", "tension", "info", "filler"):
            event_type = "info"
        return event_type
    except Exception as e:
        logger.warning(f"Classification failed: {e}, defaulting to 'info'")
        return "info"


def _generate_telugu(client: Groq, english_text: str, event_type: str, context: str = "") -> str:
    """Generate natural Telugu commentary with energy matching the event type."""
    user_message = f"[{event_type.upper()}] {english_text}"
    if context:
        user_message += f"\nRace context: {context}"

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": COMMENTARY_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Telugu generation failed: {e}")
        return ""


class DatasetCollector:
    """Drop-in replacement for TeluguCommentaryAgent that also logs
    every English→Telugu pair to a JSONL dataset file."""

    def __init__(self, race_name: str | None = None):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.race_name = race_name or datetime.now().strftime("%Y-%m-%d")
        self.dataset_file = DATASET_DIR / f"race_{self.race_name}.jsonl"
        self.stats = {"hype": 0, "tension": 0, "info": 0, "filler": 0, "total": 0}
        self.current_context = ""

        logger.info(f"DatasetCollector saving to: {self.dataset_file}")

    def set_context(self, context: str):
        """Update race context (e.g. from leaderboard scraper)."""
        self.current_context = context

    def update_race_context(self, leaderboard_data: dict):
        """Update context from leaderboard data (same interface as TeluguCommentaryAgent)."""
        positions = leaderboard_data.get("positions", [])
        leader = positions[0]["driver_name"] if positions else "Unknown"
        top_3 = ", ".join(p["driver_name"] for p in positions[:3])
        lap = leaderboard_data.get("current_lap", "?")
        total = leaderboard_data.get("total_laps", "?")
        self.current_context = f"Leader: {leader}, Top 3: {top_3}, Lap: {lap}/{total}"

    async def generate_telugu_commentary(self, english_text: str, context: str | None = None) -> str:
        """Classify, translate, and log a commentary line.

        Returns Telugu text, or empty string if the line was filler.
        """
        ctx = context or self.current_context

        # 1. Classify
        event_type = _classify_event(self.client, english_text)
        self.stats[event_type] += 1
        self.stats["total"] += 1

        # 2. Translate
        telugu_text = _generate_telugu(self.client, english_text, event_type, ctx)

        # 3. Skip filler
        is_skipped = telugu_text == "##SKIP##" or event_type == "filler"
        if is_skipped:
            telugu_text = ""

        # 4. Log to dataset
        entry = {
            "input": {
                "event_type": event_type,
                "english": english_text,
                "context": ctx,
            },
            "output": telugu_text,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "race": self.race_name,
                "skipped": is_skipped,
                "model": settings.LLM_MODEL,
            },
        }
        with open(self.dataset_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # 5. Periodic stats
        if self.stats["total"] % 50 == 0:
            self._log_stats()

        return telugu_text

    def _log_stats(self):
        logger.info(
            f"[DatasetCollector] Race: {self.race_name} | "
            f"Total: {self.stats['total']} | "
            f"Hype: {self.stats['hype']} | Tension: {self.stats['tension']} | "
            f"Info: {self.stats['info']} | Filler: {self.stats['filler']}"
        )

    def finish(self):
        """Call at end of race/stream to log final stats."""
        logger.info("=" * 60)
        logger.info(f"RACE COMPLETE: {self.race_name}")
        self._log_stats()
        logger.info(f"Dataset file: {self.dataset_file}")
        logger.info("=" * 60)

    def get_stats(self) -> dict:
        """Return current collection stats."""
        return {
            "race_name": self.race_name,
            "dataset_file": str(self.dataset_file),
            **self.stats,
        }
