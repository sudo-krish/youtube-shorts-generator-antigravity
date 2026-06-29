from ..agents import BaseDynamicAgent

PROMPT = """You are the JSON Builder.
You will receive the final, validated Technical Breakdown of multiple video variants.
Your ONLY job is to perfectly map this text into the provided Pydantic JSON Schema.

DO NOT hallucinate new data. ONLY use the data provided in the approved text.
DO NOT OUTPUT ANYTHING BUT RAW JSON. NO MARKDOWN BLOCKS.
"""

class BuilderAgent(BaseDynamicAgent):
    name = "builder"
    prompt_template = PROMPT
    
    def execute(self, payload: dict) -> dict:
        self.logger.info("Builder Agent starting...")
        
        validated_breakdown = payload.get("validated_breakdown", "")
        contents = [
            self.prompt_template,
            f"\n\n=== VALIDATED BREAKDOWN ===\n{validated_breakdown}"
        ]
        
        from ..llm.llm_client import get_llm_client
        from google.genai import types
        import json, re
        
        # In the future we will use the actual response_schema="FactoryTimeline" logic
        client = get_llm_client("deepseek-v4-flash")
        gen_config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
        
        response_text = client.generate_content(
            model="deepseek-v4-flash",
            contents=contents,
            config=gen_config
        )
        
        json_str = response_text
        if "```json" in response_text:
            m = re.search(r"```json\n(.*?)```", response_text, re.DOTALL)
            if m: json_str = m.group(1)
        elif "```" in response_text:
            m = re.search(r"```\n(.*?)```", response_text, re.DOTALL)
            if m: json_str = m.group(1)
            
        try:
            parsed_data = json.loads(json_str)
            return {"shorts": parsed_data}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON for {self.name}: {e}")
            self.logger.error(f"Raw output: {response_text}")
            return {"shorts": {}}

