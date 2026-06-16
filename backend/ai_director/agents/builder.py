from ai_director.config_manager import get_config
import logging
import json
from ai_director.llm_client import LLMClient
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
    def execute(self, validated_breakdown: str) -> dict:
        logger.info("Builder Agent generating final JSON schema...")
        client = LLMClient()
        response_text = client.generate_content(
            model=get_config()["models"]["builder"],
            contents=[
                BUILDER_PROMPT
                + "\n\n=== VALIDATED BREAKDOWN ===\n"
                + validated_breakdown
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=FactoryTimeline,
            ),
        )
        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, list):
                return {"shorts": parsed}
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse Builder JSON: {str(e)}")
            return {"shorts": []}
