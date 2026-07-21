from app.ai.providers.openai_compatible.provider import OpenAICompatibleProvider, OpenAICompatibleConfig


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__()

    @property
    def provider_config(self) -> OpenAICompatibleConfig:
        return OpenAICompatibleConfig(
            name="openrouter",
            base_url="https://openrouter.ai/api",
            default_model="anthropic/claude-3.5-sonnet",
            priority=40,
            timeout_seconds=120,
            supports_embeddings=False,
            supports_model_discovery=True,
            supports_structured_output=False,
            supports_reasoning=False,
            supports_vision=True,
            supports_tools=True,
        )
