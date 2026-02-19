"""
Race Context Engine
====================
Fetches live F1 timing data from the OpenF1 API (api.openf1.org — free, no key needed)
and provides structured race context for LLM prompt injection.

Refreshes every 10 seconds. Provides:
  - Formatted context string  → injected into Sarvam-m commentary prompt
  - Structured leaderboard    → broadcast to frontend via WebSocket

OpenF1 API docs: https://openf1.org
"""

import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPENF1_BASE = "https://api.openf1.org/v1"
REFRESH_INTERVAL = 10  # seconds — matches design doc spec


class RaceContextEngine:
    """Live race context from OpenF1 API.

    Single pipeline architecture: one context string shared across all
    commentary chunks, refreshed every 10 seconds in the background.
    """

    def __init__(self):
        self._session_key: Optional[int] = None
        self._session_info: dict = {}
        self._drivers: dict = {}        # driver_number → driver info
        self._latest_positions: dict = {}  # driver_number → latest position record
        self._latest_laps: dict = {}    # driver_number → latest lap record
        self._leaderboard: dict = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background refresh loop."""
        self._running = True
        await self._fetch_latest_session()
        if self._session_key:
            await self._fetch_drivers()
            await self._fetch_data()
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info(f"RaceContextEngine started (session_key={self._session_key})")

    async def stop(self):
        """Stop the refresh loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _fetch_latest_session(self):
        """Find the most recent live session (Race, Qualifying, or Practice)."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{OPENF1_BASE}/sessions",
                    params={"session_key": "latest"},
                )
                if resp.status_code == 200:
                    sessions = resp.json()
                    if sessions:
                        session = sessions[-1]
                        self._session_key = session.get("session_key")
                        self._session_info = session
                        logger.info(
                            f"Session: {session.get('session_name')} | "
                            f"Circuit: {session.get('circuit_short_name')} | "
                            f"Key: {self._session_key}"
                        )
        except Exception as e:
            logger.warning(f"Failed to fetch latest session: {e}")

    async def _fetch_drivers(self):
        """Fetch driver roster for this session (name, team, number)."""
        if not self._session_key:
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{OPENF1_BASE}/drivers",
                    params={"session_key": self._session_key},
                )
                if resp.status_code == 200:
                    for driver in resp.json():
                        num = driver.get("driver_number")
                        if num is not None:
                            self._drivers[num] = driver
                    logger.info(f"Loaded {len(self._drivers)} drivers")
        except Exception as e:
            logger.warning(f"Failed to fetch drivers: {e}")

    async def _refresh_loop(self):
        """Refresh position and lap data every 10 seconds."""
        while self._running:
            try:
                await self._fetch_data()
            except Exception as e:
                logger.warning(f"Race context refresh error: {e}")
            await asyncio.sleep(REFRESH_INTERVAL)

    async def _fetch_data(self):
        """Fetch latest position and lap data from OpenF1."""
        if not self._session_key:
            return

        async with httpx.AsyncClient(timeout=10) as client:
            # Position data
            pos_resp = await client.get(
                f"{OPENF1_BASE}/position",
                params={"session_key": self._session_key},
            )

            # Latest lap data (for lap count)
            lap_resp = await client.get(
                f"{OPENF1_BASE}/laps",
                params={"session_key": self._session_key},
            )

        if pos_resp.status_code == 200:
            self._update_positions(pos_resp.json())

        if lap_resp.status_code == 200:
            self._update_laps(lap_resp.json())

        self._build_leaderboard()

    def _update_positions(self, position_data: list):
        """Keep only the latest position record per driver."""
        for record in position_data:
            num = record.get("driver_number")
            if num is None:
                continue
            existing = self._latest_positions.get(num)
            if existing is None or record.get("date", "") > existing.get("date", ""):
                self._latest_positions[num] = record

    def _update_laps(self, lap_data: list):
        """Keep only the latest lap record per driver."""
        for record in lap_data:
            num = record.get("driver_number")
            if num is None:
                continue
            existing = self._latest_laps.get(num)
            existing_lap = existing.get("lap_number", 0) if existing else 0
            if record.get("lap_number", 0) >= existing_lap:
                self._latest_laps[num] = record

    def _build_leaderboard(self):
        """Assemble a sorted leaderboard from position + lap + driver data."""
        sorted_positions = sorted(
            self._latest_positions.values(),
            key=lambda x: x.get("position", 99),
        )

        positions = []
        for record in sorted_positions:
            num = record.get("driver_number")
            driver = self._drivers.get(num, {})
            lap_record = self._latest_laps.get(num, {})

            lap_duration = lap_record.get("lap_duration")
            last_lap_str = (
                _format_lap_time(lap_duration) if lap_duration else "—"
            )

            positions.append({
                "position": record.get("position"),
                "driver_number": num,
                "driver_name": driver.get("full_name", f"Car {num}"),
                "driver_code": driver.get("name_acronym", "???"),
                "team": driver.get("team_name", "Unknown"),
                "team_colour": f"#{driver.get('team_colour', 'ffffff')}",
                "gap": "—",           # OpenF1 doesn't expose gap directly
                "last_lap_time": last_lap_str,
            })

        # Determine current lap from the leader's lap data
        leader_num = sorted_positions[0].get("driver_number") if sorted_positions else None
        current_lap = 0
        if leader_num is not None:
            current_lap = self._latest_laps.get(leader_num, {}).get("lap_number", 0)

        session_name = self._session_info.get("session_name", "")
        total_laps = self._session_info.get("total_laps") or 0

        self._leaderboard = {
            "session_key": self._session_key,
            "session_name": session_name,
            "circuit": self._session_info.get("circuit_short_name", ""),
            "country": self._session_info.get("country_name", ""),
            "positions": positions,
            "current_lap": current_lap,
            "total_laps": total_laps,
        }

    def get_leaderboard(self) -> dict:
        """Return the current structured leaderboard for WebSocket broadcast."""
        return self._leaderboard

    def get_context_string(self) -> str:
        """Return a compact context string for LLM prompt injection."""
        positions = self._leaderboard.get("positions", [])
        if not positions:
            return ""

        leader = positions[0].get("driver_name", "Unknown")
        top_3 = " | ".join(
            f"P{p['position']} {p['driver_name']}"
            for p in positions[:3]
        )
        lap = self._leaderboard.get("current_lap", "?")
        total = self._leaderboard.get("total_laps", "?")
        circuit = self._leaderboard.get("circuit", "")
        session = self._leaderboard.get("session_name", "")

        parts = [f"Leader: {leader}", f"Top 3: [{top_3}]"]
        if lap and total:
            parts.append(f"Lap: {lap}/{total}")
        if circuit:
            parts.append(f"Circuit: {circuit}")
        if session:
            parts.append(f"Session: {session}")

        return " | ".join(parts)


def _format_lap_time(seconds: float) -> str:
    """Format lap duration in seconds to M:SS.mmm string."""
    try:
        total_s = float(seconds)
        minutes = int(total_s // 60)
        remaining = total_s - minutes * 60
        return f"{minutes}:{remaining:06.3f}"
    except (TypeError, ValueError):
        return "—"
