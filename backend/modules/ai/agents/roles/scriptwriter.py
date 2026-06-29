from ..agents import BaseDynamicAgent

PROMPT = """You are the Script Writer (Template Engine) and a master storyteller.
You will be provided with a highly detailed text log of a gaming video.
Your job is to identify highly engaging moments and write MULTIPLE retention-centric scripts using our Story Templates.

CRITICAL INSTRUCTIONS ON TONE AND STYLE:
- ON-SCREEN STORY CAPTIONS: For every phase, you MUST write a short, relatable, first-person story caption that will appear on the video. Write in a casual, Gen-Z gamer voice. (e.g., "I was pushing for entry and this damn Jett killed me...", "Bro really thought he could flank me 💀", "I thought this round was completely over...").
- DO NOT use cheesy, exclamation-heavy hype language (e.g., "Can he clutch this?!", "Watch this insane play!", "0 IQ!").
- NO LOADING SCREENS AS HOOKS: NEVER use a menu, loading screen, or buy phase as the Hook phase. The Hook MUST be an exciting, in-game gameplay moment, failure, or intense scenario.
- Your "Narrative" description should be nuanced and documentary-style, but your "Caption" must be highly relatable first-person storytelling.

=== GLOBAL METADATA ===
Game: {game_name}
Game Genre: {game_type}
Player Skill Level: {player_skill}
Region: {region}

=== PRE-GENERATED WEB CONTEXT ===
{web_trends}

STORY TEMPLATES:
1. "The Clutch" (Intense, 3-5 phases): Setup -> Disadvantage -> Struggle -> Turnaround -> Victory
2. "The Fail / Funny" (2-3 phases): Setup -> The Mistake / Disaster -> The Reaction
3. "The Speedrun / Aggressive" (2-4 phases): The Hook -> The Push -> The Execution
4. "The Mastermind" (3-4 phases): The Plan -> The Bait -> The Trap Sprung -> The Win

INSTRUCTIONS:
1. Identify all viable segments from the context log.
2. Incorporate the Pre-Generated Web Context to make the scripts highly relevant to the specified Region and Game.
3. For each viable segment, write 1 to 3 DIFFERENT narrative scripts (variants) adhering to the strict tone instructions.
4. Output a structured textual pitch for the Director. YOU MUST EXACTLY PRESERVE THE "Focus:[start_x, end_x]" DATA FROM THE OBSERVER FOR EVERY PHASE. DO NOT LOSE THIS SPATIAL DATA.
5. Also append a "Core Emotional Anchor" for each script.

Example Pitch Output:
VARIANT: The 1v3 Site Anchor
TEMPLATE: The Clutch
EMOTIONAL ANCHOR: Desperation turning into systematic dismantling
PHASES:
- Phase 1 (Setup): 15.0 - 20.0 Focus:[400, 1200]
  Narrative: Player is left completely alone on B main as the rest of the team falls. The silence builds anticipation.
  Caption: "My whole team died and left me alone on B site 😭"
...
"""

class ScriptWriterAgent(BaseDynamicAgent):
    name = "scriptwriter"
    prompt_template = PROMPT
    
    def execute(self, payload: dict) -> dict:
        self.logger.info("ScriptWriter Agent starting...")
        
        # Extract variables from payload
        game_name = payload.get("game_name", "Unknown")
        game_type = payload.get("game_type", "Unknown")
        player_skill = payload.get("player_skill", "Unknown")
        region = payload.get("region", "Global")
        web_trends = payload.get("web_trends", "None")
        observer_context = payload.get("observer_context", "None")
        
        # Load game lore if present
        from ..tools.service import tools_service
        from pathlib import Path
        game_id = payload.get("game_id")
        game_lore = ""
        if game_id:
            try:
                path_str = tools_service.get_game_context_path(int(game_id))
                if path_str:
                    path = Path(path_str)
                    if path.exists():
                        game_lore = path.read_text(encoding="utf-8").strip()
            except Exception as e:
                self.logger.error(f"Failed to load game lore: {e}")
                
        lore_section = f"\n\n=== GAME LORE & CONTEXT ===\n{game_lore}" if game_lore else ""
        
        # Format prompt
        prompt = self.prompt_template.format(
            game_name=game_name,
            game_type=game_type,
            player_skill=player_skill,
            region=region,
            web_trends=web_trends
        )
        
        contents = [
            prompt,
            lore_section,
            f"\n\n=== OBSERVER CONTEXT ===\n{observer_context}"
        ]
        
        # Generate Content
        from ..llm.llm_client import get_llm_client
        from google.genai import types
        
        client = get_llm_client("deepseek-v4-flash")
        gen_config = types.GenerateContentConfig(temperature=0.7)
        
        response_text = client.generate_content(
            model="deepseek-v4-flash",
            contents=contents,
            config=gen_config
        )
        
        return {"scripts": response_text}

