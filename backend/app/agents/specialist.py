from app.orchestrator.config_manager import get_config
import logging
from app.orchestrator.llm_client import LLMClient
from google.genai import types

logger = logging.getLogger(__name__)

SPECIALIST_PROMPT = """You are the YouTube Shorts Specialist and Final Polish Editor.
You will receive the Editor's rough Technical Breakdown for multiple video variants.
Your job is to optimize this breakdown for maximum algorithmic retention and fix any mathematical timestamp errors.

=== GLOBAL METADATA ===
Game: {game_name}
Region: {region}
Vibe: {vibe}

=== PRE-GENERATED YOUTUBE CONTEXT ===
{youtube_rules}

=== CAPABILITIES MENU ===
{capabilities}

=== PRE-GENERATED MATH VALIDATION REPORT ===
{math_report}

INSTRUCTIONS:
1. Pacing & Hooks: Review the phase durations against the YouTube Context. Does the first phase have a strong hook? Is the total duration in the Golden Standard (30-60s) or Snackable (15-30s) zone? Adjust phase durations if needed.
2. Effects Optimization: Look at the Capabilities Menu. Did the Editor miss a good opportunity for a `motion_blur` or a `dynamic_glow`? Add them in to increase retention.
3. Math Fixing (CRITICAL): Read the Math Validation Report. If it says an effect exceeds the Phase Duration, YOU MUST FIX IT by adjusting the `duration` or `relative_start_time` of the effect so it fits perfectly inside the phase.
4. DO NOT OUTPUT JSON. Output the FINAL, polished technical breakdown text using the EXACT same format as the Editor's Breakdown.

Example Final Output Format:
VARIANT: The 1v3 Site Anchor
PHASES:
- Phase 1 (Setup): 15.0 - 20.0 (Duration: 5.0)
  Transition In: "wipeleft"
  Text: "My whole team died and left me alone on B site 😭"
  Effects: [{{'effect_name': 'vhs_overlay', 'relative_start_time': 0.0, 'duration': 5.0}}]
  Punch-ins: [2.5]
...
"""


class SpecialistAgent:
    def execute(
        self,
        editor_breakdown: str,
        metadata: dict,
        math_report: str,
        youtube_rules: str,
        capabilities: str,
    ) -> str:
        logger.info("Specialist Agent acting as Final Editor with YouTube Rules...")
        client = LLMClient()

        prompt = SPECIALIST_PROMPT.format(
            game_name=metadata.get("game_name", "Unknown"),
            region=metadata.get("region", "Global"),
            vibe=metadata.get("vibe", "Standard"),
            math_report=math_report,
            youtube_rules=youtube_rules,
            capabilities=capabilities,
        )

        return client.generate_content(
            model=get_config()["models"]["specialist"],
            contents=[prompt + "\n\n=== EDITOR BREAKDOWN ===\n" + editor_breakdown],
            config=types.GenerateContentConfig(temperature=0.3),
        )
