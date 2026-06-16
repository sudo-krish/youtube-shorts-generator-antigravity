import logging
import os
import re
import google.genai as genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

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
        return self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        ).text

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
        if "flash" in model:
            response = self.deepseek_client.chat.completions.create(
                model=model,
                messages=messages,
                extra_body={"thinking_mode": False, "thinking": {"type": "disabled"}},
            )
            return response.choices[0].message.content

        # Route mathematical/FFmpeg agents to V4-Pro with Thinking Default
        elif "pro" in model:
            response = self.deepseek_client.chat.completions.create(
                model=model,
                messages=messages,
            )
            # The 'reasoning_content' is isolated. We only return the final validated output.
            text = response.choices[0].message.content
            if text:
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            return text

        else:
            # Fallback
            response = self.deepseek_client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return response.choices[0].message.content

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
            else:
                logger.error(f"LLM Generation failed: {str(actual_error)}")

            raise actual_error
