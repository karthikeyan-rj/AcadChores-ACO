from app.ai.providers.openai_compatible.provider import OpenAICompatibleProvider, OpenAICompatibleConfig


class GroqProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__()

    @property
    def provider_config(self) -> OpenAICompatibleConfig:
        return OpenAICompatibleConfig(
            name="groq",
            base_url="https://api.groq.com/openai",
            default_model="llama-3.3-70b-versatile",
            priority=20,
            timeout_seconds=60,
            supports_embeddings=False,
            supports_model_discovery=True,
            supports_structured_output=True,
            supports_reasoning=False,
            supports_vision=False,
            supports_tools=True,
        )
