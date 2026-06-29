import os
import json
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from modules.ai.service import ai_service
from ..llm_client import BaseLLMClient

class OllamaClient(BaseLLMClient):
    """Local Ollama implementation using OpenAI client."""

    def __init__(self):
        super().__init__()
        import openai
        # Default Ollama port is 11434
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.client = openai.OpenAI(
            api_key="ollama", # Required by the client but ignored by Ollama
            base_url=base_url
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_content(
        self, model: str, contents: list, config: types.GenerateContentConfig = None
    ) -> str:
        try:
            # Strip prefix if it exists (e.g. "ollama/llama3" -> "llama3")
            actual_model = model.replace("ollama/", "") if model.startswith("ollama/") else model

            messages = []
            for content in contents:
                if isinstance(content, str):
                    messages.append({"role": "user", "content": content})
                else:
                    messages.append({"role": "user", "content": str(content)})

            kwargs = {}
            if config:
                if getattr(config, "response_schema", None):
                    schema_dict = config.response_schema.model_json_schema()
                    schema_str = json.dumps(schema_dict, indent=2)
                    schema_instruction = f"\\n\\nYou MUST respond with raw JSON that perfectly matches the following JSON Schema. Do NOT wrap the JSON in markdown blocks or backticks. Only output valid JSON:\\n{schema_str}"
                    messages[-1]["content"] += schema_instruction
                
                # Ollama supports json mode natively in newer versions
                if getattr(config, "response_mime_type", None) == "application/json":
                    kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(
                model=actual_model,
                messages=messages,
                **kwargs
            )
            
            text = response.choices[0].message.content

            # Tracking tokens (Ollama = $0 cost)
            try:
                if hasattr(response, 'usage') and response.usage:
                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                        
                    model_id = ai_service.get_or_create_model("ollama", actual_model)
                    ai_service.log_usage(model_id, prompt_tokens, completion_tokens, 0.0)
            except Exception as e:
                self.logger.warning(f"Failed to log Ollama usage: {e}")

            return text
            
        except Exception as e:
            try:
                import openai
            except ImportError:
                openai = None

            actual_error = e
            if isinstance(e, RetryError) and e.last_attempt:
                actual_error = e.last_attempt.exception()
            
            if openai and isinstance(actual_error, openai.APIConnectionError):
                self.logger.error("Could not connect to Ollama. Is it running on localhost:11434?")

            self.logger.error(f"Ollama Generation failed: {str(actual_error)}")
            raise actual_error
