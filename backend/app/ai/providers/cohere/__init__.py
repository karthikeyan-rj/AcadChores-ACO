from app.ai.providers.openai_compatible.provider import OpenAICompatibleProvider, OpenAICompatibleConfig


class CohereProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__()

    @property
    def provider_config(self) -> OpenAICompatibleConfig:
        return OpenAICompatibleConfig(
            name="cohere",
            base_url="https://api.cohere.com/compatibility",
            default_model="command-a-03-2025",
            priority=50,
            timeout_seconds=120,
            supports_embeddings=True,
            supports_model_discovery=True,
            supports_structured_output=False,
            supports_reasoning=False,
            supports_vision=False,
            supports_tools=True,
        )
