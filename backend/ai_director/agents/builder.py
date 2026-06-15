from ai_director.config_manager import get_config
import logging
import json
import google.genai as genai
from google.genai import types

from ai_director.schemas import FactoryTimeline

logger = logging.getLogger(__name__)

BUILDER_PROMPT = """You are the JSON Builder.
You will receive the final, validated Technical Breakdown of multiple video variants.
Your ONLY job is to perfectly map this text into the provided Pydantic JSON Schema.

DO NOT hallucinate new data. ONLY use the data provided in the approved text.
DO NOT OUTPUT ANYTHING BUT RAW JSON. NO MARKDOWN BLOCKS.
"""

class BuilderAgent:
    def __init__(self):
        self.client = genai.Client()

    def execute(self, validated_breakdown: str) -> dict:
        logger.info("Builder Agent generating final JSON schema...")
        response = self.client.models.generate_content(
            model=get_config()["models"]["builder"],
            contents=[BUILDER_PROMPT + "\n\n=== VALIDATED BREAKDOWN ===\n" + validated_breakdown],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=FactoryTimeline
            )
        )
        try:
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Failed to parse Builder JSON: {str(e)}")
            return {"shorts": []}
