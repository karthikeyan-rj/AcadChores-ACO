from app.ai.providers.openai_compatible.provider import OpenAICompatibleProvider, OpenAICompatibleConfig


class OpenAIProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__()

    @property
    def provider_config(self) -> OpenAICompatibleConfig:
        return OpenAICompatibleConfig(
            name="openai",
            base_url="https://api.openai.com",
            default_model="gpt-4o-mini",
            priority=10,
            timeout_seconds=120,
            supports_embeddings=True,
            supports_model_discovery=True,
            supports_structured_output=True,
            supports_reasoning=False,
            supports_vision=True,
            supports_tools=True,
        )
