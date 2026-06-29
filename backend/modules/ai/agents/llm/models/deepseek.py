import os
import re
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from modules.ai.service import ai_service
from ..llm_client import BaseLLMClient

class DeepSeekClient(BaseLLMClient):
    """DeepSeek implementation using OpenAI client."""

    def __init__(self):
        super().__init__()
        import openai
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment")
        self.client = openai.OpenAI(
            api_key=api_key, base_url="https://api.deepseek.com"
        )

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def generate_content(
        self, model: str, contents: list, config: types.GenerateContentConfig = None
    ) -> str:
        try:
            # DeepSeek uses OpenAI format messages: [{"role": "user", "content": "..."}]
            messages = []
            for content in contents:
                if isinstance(content, str):
                    messages.append({"role": "user", "content": content})
                else:
                    messages.append({"role": "user", "content": str(content)})

            kwargs = {}
            if config:
                if getattr(config, "response_schema", None):
                    import json
                    schema_dict = config.response_schema.model_json_schema()
                    schema_str = json.dumps(schema_dict, indent=2)
                    schema_instruction = f"\\n\\nYou MUST respond with raw JSON that perfectly matches the following JSON Schema. Do NOT wrap the JSON in markdown blocks or backticks. Only output valid JSON:\\n{schema_str}"
                    messages[-1]["content"] += schema_instruction
                if getattr(config, "response_mime_type", None) == "application/json":
                    kwargs["response_format"] = {"type": "json_object"}

            # Route creative/formatting agents to V4-Flash with Thinking Disabled
            if "flash" in model.lower():
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    extra_body={"thinking_mode": False, "thinking": {"type": "disabled"}},
                    **kwargs
                )
                text = response.choices[0].message.content
            # Route mathematical/FFmpeg agents to V4-Pro with Thinking Default
            elif "pro" in model.lower():
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs
                )
                text = response.choices[0].message.content
                if text:
                    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            else:
                # Fallback
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs
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
                        
                    model_id = ai_service.get_or_create_model("deepseek", model)
                    ai_service.log_usage(model_id, prompt_tokens, completion_tokens, cost)
            except Exception as e:
                self.logger.warning(f"Failed to log DeepSeek usage: {e}")

            return text
            
        except Exception as e:
            try:
                import openai
            except ImportError:
                openai = None

            actual_error = e
            if isinstance(e, RetryError) and e.last_attempt:
                actual_error = e.last_attempt.exception()

            if openai and isinstance(actual_error, openai.RateLimitError):
                self.logger.error(f"DeepSeek API Rate Limit Hit: {str(actual_error)}")
                try:
                    model_id = ai_service.get_or_create_model("deepseek", model)
                    ai_service.log_rate_limit(model_id, str(actual_error))
                except Exception:
                    pass
            else:
                self.logger.error(f"DeepSeek Generation failed: {str(actual_error)}")

            raise actual_error
