import logging

from groq import Groq

from config import settings

logger = logging.getLogger(__name__)

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


class TeluguCommentaryAgent:
    """Translates English F1 commentary to energetic Telugu using Groq (Llama)."""

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.race_context: dict = {}

    def update_race_context(self, leaderboard_data: dict):
        """Update the agent's knowledge of current race state."""
        positions = leaderboard_data.get("positions", [])
        self.race_context = {
            "leader": positions[0]["driver_name"] if positions else "Unknown",
            "top_3": [p["driver_name"] for p in positions[:3]],
            "current_lap": leaderboard_data.get("current_lap", "?"),
            "total_laps": leaderboard_data.get("total_laps", "?"),
        }

    async def generate_telugu_commentary(self, english_text: str) -> str:
        """Convert English commentary to Telugu.

        Args:
            english_text: The English commentary text to translate.

        Returns:
            Telugu commentary text.
        """
        context_info = self._build_context_string()

        user_prompt = f"""{context_info}

English Commentary:
"{english_text}"

Provide Telugu commentary:"""

        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                messages=[
                    {"role": "system", "content": TELUGU_COMMENTARY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )

            telugu_text = response.choices[0].message.content
            logger.info(f"Telugu commentary generated: {telugu_text[:80]}...")
            return telugu_text

        except Exception as e:
            logger.error(f"Commentary generation error: {e}")
            raise

    def _build_context_string(self) -> str:
        """Build a context string from current race state."""
        if not self.race_context:
            return "No race context available."

        top_3 = ", ".join(self.race_context.get("top_3", []))
        return f"""Current Race State:
- Leader: {self.race_context.get('leader', 'Unknown')}
- Top 3: {top_3}
- Lap: {self.race_context.get('current_lap', '?')} / {self.race_context.get('total_laps', '?')}"""
