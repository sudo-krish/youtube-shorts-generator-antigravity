import google.genai as genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from modules.ai.service import ai_service
from ..llm_client import BaseLLMClient

class GeminiClient(BaseLLMClient):
    """Google GenAI (Gemini) implementation."""
    
    def __init__(self):
        super().__init__()
        self.client = genai.Client()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_content(
        self, model: str, contents: list, config: types.GenerateContentConfig = None
    ) -> str:
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            
            # Tracking tokens (Gemini Free Tier = $0)
            try:
                if response.usage_metadata:
                    prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                    completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
                    if prompt_tokens > 0 or completion_tokens > 0:
                        model_id = ai_service.get_or_create_model("gemini", model)
                        ai_service.log_usage(model_id, prompt_tokens, completion_tokens, 0.0)
            except Exception as e:
                self.logger.warning(f"Failed to log Gemini usage: {e}")
                
            return response.text
            
        except Exception as e:
            try:
                from google.genai.errors import ClientError
            except ImportError:
                ClientError = None

            actual_error = e
            if isinstance(e, RetryError) and e.last_attempt:
                actual_error = e.last_attempt.exception()

            if (
                ClientError
                and isinstance(actual_error, ClientError)
                and (
                    "429" in str(actual_error)
                    or getattr(
                        actual_error, "code", getattr(actual_error, "status_code", None)
                    )
                    == 429
                )
            ):
                self.logger.error(f"Gemini API Rate Limit Exhausted: {str(actual_error)}")
                try:
                    model_id = ai_service.get_or_create_model("gemini", model)
                    ai_service.log_rate_limit(model_id, str(actual_error))
                except Exception:
                    pass
            else:
                self.logger.error(f"Gemini Generation failed: {str(actual_error)}")

            raise actual_error
