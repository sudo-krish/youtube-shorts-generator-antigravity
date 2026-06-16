import logging
import os
import re
import google.genai as genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from database import get_or_create_model, log_model_usage, log_rate_limit

logger = logging.getLogger(__name__)


class LLMClient:
    """Centralized client for handling Google GenAI and DeepSeek interactions with retries."""

    def __init__(self):
        self.client = genai.Client()
        self._openai_client = None

    @property
    def deepseek_client(self):
        if not self._openai_client:
            import openai

            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY not found in environment")
            self._openai_client = openai.OpenAI(
                api_key=api_key, base_url="https://api.deepseek.com"
            )
        return self._openai_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _generate_google(
        self, model: str, contents: list, config: types.GenerateContentConfig = None
    ):
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
                    model_id = get_or_create_model("gemini", model)
                    log_model_usage(model_id, prompt_tokens, completion_tokens, 0.0)
        except Exception as e:
            logger.warning(f"Failed to log Gemini usage: {e}")
            
        return response.text

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _generate_deepseek(self, model: str, contents: list):
        # DeepSeek uses OpenAI format messages: [{"role": "user", "content": "..."}]
        messages = []
        for content in contents:
            if isinstance(content, str):
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "user", "content": str(content)})

        # Route creative/formatting agents to V4-Flash with Thinking Disabled
        if "flash" in model.lower():
            response = self.deepseek_client.chat.completions.create(
                model=model,
                messages=messages,
                extra_body={"thinking_mode": False, "thinking": {"type": "disabled"}},
            )
            text = response.choices[0].message.content
        # Route mathematical/FFmpeg agents to V4-Pro with Thinking Default
        elif "pro" in model.lower():
            response = self.deepseek_client.chat.completions.create(
                model=model,
                messages=messages,
            )
            text = response.choices[0].message.content
            if text:
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        else:
            # Fallback
            response = self.deepseek_client.chat.completions.create(
                model=model,
                messages=messages,
            )
            text = response.choices[0].message.content

        # Tracking tokens and Cost
        try:
            if hasattr(response, 'usage') and response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                
                if "pro" in model.lower():
                    cost = (prompt_tokens / 1_000_000) * 0.435 + (completion_tokens / 1_000_000) * 0.87
                else:
                    cost = (prompt_tokens / 1_000_000) * 0.14 + (completion_tokens / 1_000_000) * 0.28
                    
                model_id = get_or_create_model("deepseek", model)
                log_model_usage(model_id, prompt_tokens, completion_tokens, cost)
        except Exception as e:
            logger.warning(f"Failed to log DeepSeek usage: {e}")

        return text

    def generate_content(
        self, model: str, contents: list, config: types.GenerateContentConfig = None
    ) -> str:
        """Generates content dynamically routing to Gemini or DeepSeek based on model string."""
        try:
            if model.startswith("deepseek"):
                return self._generate_deepseek(model, contents)
            else:
                return self._generate_google(model, contents, config)
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
                logger.error(f"API Rate Limit or Quota Exhausted: {str(actual_error)}")
                try:
                    model_id = get_or_create_model("gemini", model)
                    log_rate_limit(model_id, str(actual_error))
                except Exception:
                    pass
            else:
                try:
                    import openai
                    if isinstance(actual_error, openai.RateLimitError):
                        logger.error(f"DeepSeek API Rate Limit Hit: {str(actual_error)}")
                        try:
                            model_id = get_or_create_model("deepseek", model)
                            log_rate_limit(model_id, str(actual_error))
                        except Exception:
                            pass
                        raise actual_error
                except ImportError:
                    pass
                logger.error(f"LLM Generation failed: {str(actual_error)}")

            raise actual_error
