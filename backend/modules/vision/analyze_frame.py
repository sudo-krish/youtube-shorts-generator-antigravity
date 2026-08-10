import os
import io
import json
import base64
from typing import Dict, Any
import google.generativeai as genai
from core.base_service import BaseNanoService

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

class AnalyzeFrameService(BaseNanoService):
    """
    Nano-Service for analyzing a single video frame using Gemini 1.5 Pro.
    Returns a transcription (aiContext) and narrative suggestions.
    """
    route = "/vision/analyze-frame"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        frame_data_b64 = payload.get("frame_data")
        if not frame_data_b64:
            return {"error": "Missing frame_data in payload"}

        # Strip the data URL prefix if present
        if "," in frame_data_b64:
            frame_data_b64 = frame_data_b64.split(",")[1]

        image_bytes = base64.b64decode(frame_data_b64)

        try:
            model = genai.GenerativeModel("gemini-1.5-pro")
            
            prompt = """
            You are an expert AI video director.
            Look at this frame from a video game and describe exactly what is happening.
            Provide your response in the following JSON format:
            {
                "transcription": "A detailed 1-2 sentence description of the action.",
                "suggestions": [
                    "A short, punchy narrative suggestion for the voiceover (max 6 words).",
                    "Another short narrative suggestion.",
                    "A third short narrative suggestion."
                ]
            }
            Do not include any markdown formatting or code blocks, just raw JSON.
            """

            image_parts = [
                {
                    "mime_type": "image/jpeg",
                    "data": image_bytes
                }
            ]

            response = model.generate_content([prompt, image_parts[0]])
            response_text = response.text.strip()
            
            # Clean up markdown if model ignored the instruction
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            result = json.loads(response_text)
            
            return {
                "aiContext": result.get("transcription", "Vision AI: Analyzed frame."),
                "aiSuggestions": result.get("suggestions", ["Add dramatic slowdown", "Highlight the tension", "Explain the strategy"])
            }
        except Exception as e:
            return {
                "error": str(e),
                "aiContext": f"Vision AI Error: {str(e)}",
                "aiSuggestions": ["Fallback suggestion 1", "Fallback suggestion 2"]
            }
