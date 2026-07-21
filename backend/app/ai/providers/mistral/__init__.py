from app.ai.providers.openai_compatible.provider import OpenAICompatibleProvider, OpenAICompatibleConfig


class MistralProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__()

    @property
    def provider_config(self) -> OpenAICompatibleConfig:
        return OpenAICompatibleConfig(
            name="mistral",
            base_url="https://api.mistral.ai",
            default_model="mistral-small-latest",
            priority=30,
            timeout_seconds=120,
            supports_embeddings=True,
            supports_model_discovery=True,
            supports_structured_output=True,
            supports_reasoning=False,
            supports_vision=False,
            supports_tools=True,
        )
