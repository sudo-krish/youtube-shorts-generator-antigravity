from ..agents import BaseDynamicAgent
import json
import logging

logger = logging.getLogger(__name__)

SUGGEST_PROMPT_TEMPLATE = """You are an expert creative assistant for gaming content creators.
Based on the following project context, generate exactly 3 distinct, highly engaging prompts that the user can click on to start writing their video script. 
Keep the prompts concise (under 20 words each) and highly specific to the game and genre.

Context:
Game: {game_name}
Genre: {genre}
Theme: {theme}

Format your output as a pure JSON list of strings. Do not include markdown formatting or backticks.
Example: ["Write a rant about matchmaking", "Tell a story about the final boss", "Explain the lore of the main character"]
"""

GENERATE_SCRIPT_TEMPLATE = """You are an expert gaming scriptwriter.
Write a detailed, engaging video script based on the following context and user prompt.
The script should be written in a natural, spoken tone, ready to be read by a narrator.

Context:
Game: {game_name}
Genre: {genre}
Theme: {theme}

User Prompt: {prompt}

Write the script clearly, divided into paragraphs. Do not include camera directions or visual notes, just the spoken narrative text.
"""

class IdeationAgent(BaseDynamicAgent):
    name = "ideation"
    
    def execute(self, payload: dict) -> dict:
        action = payload.get("action", "suggest")
        game_name = payload.get("game_name", "Unknown")
        genre = payload.get("genre", "Unknown")
        theme = payload.get("theme", "Unknown")
        
        from ..llm.llm_client import get_llm_client
        from google.genai import types
        
        client = get_llm_client("deepseek-v4-flash")
        gen_config = types.GenerateContentConfig(temperature=0.7)
        
        if action == "suggest":
            prompt = SUGGEST_PROMPT_TEMPLATE.format(game_name=game_name, genre=genre, theme=theme)
            try:
                response = client.generate_content(
                    model="deepseek-v4-flash",
                    contents=[prompt],
                    config=gen_config
                )
                
                # Try to parse the response as JSON
                try:
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text[7:-3]
                    elif text.startswith("```"):
                        text = text[3:-3]
                    suggestions = json.loads(text.strip())
                except json.JSONDecodeError:
                    # Fallback if DeepSeek doesn't output valid JSON
                    lines = response.text.split('\n')
                    suggestions = [line.strip('- ').strip('"') for line in lines if line.strip()][:3]
                    
                return {"suggestions": suggestions}
            except Exception as e:
                logger.error(f"Failed to generate suggestions: {e}")
                return {"suggestions": ["Write a story about this game", "Explain a funny moment", "Discuss the latest patch"]}
                
        elif action == "generate":
            user_prompt = payload.get("prompt", "Write a generic gaming script.")
            prompt = GENERATE_SCRIPT_TEMPLATE.format(
                game_name=game_name, 
                genre=genre, 
                theme=theme, 
                prompt=user_prompt
            )
            
            try:
                response = client.generate_content(
                    model="deepseek-v4-flash",
                    contents=[prompt],
                    config=gen_config
                )
                return {"script": response.text}
            except Exception as e:
                logger.error(f"Failed to generate script: {e}")
                raise Exception(f"Script generation failed: {e}")
                
        else:
            raise ValueError(f"Unknown action for IdeationAgent: {action}")
