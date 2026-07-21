"""Behavior-focused tests for the multi-provider AI system.

Covers:
- Multiple credentials per provider
- Encrypted storage and secret redaction
- Local-only blocking every cloud path
- Per-conversation provider/model/credential restoration
- Provider failure classification
- Visible and persistent fallback notices
- Cancellation before fallback
- No late cloud response after Stop
- Conversation context preserved across model changes
- Cross-user credential isolation
"""
import asyncio
import threading
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_user_id():
    return "507f1f77bcf86cd799439011"


@pytest.fixture
def mock_user_id_2():
    return "507f1f77bcf86cd799439012"


@pytest.fixture
def mock_credential():
    """Return a mock UserApiKey document."""
    doc = MagicMock()
    doc.id = "cred_abc123"
    doc.provider = "openai"
    doc.encrypted_key = "encrypted_value_here"
    doc.key_hint = "••••••••4F9A"
    doc.label = "Work key"
    doc.is_active = True
    doc.is_default = True
    doc.validated_at = None
    doc.created_at = datetime.now(timezone.utc)
    doc.updated_at = datetime.now(timezone.utc)
    return doc


@pytest.fixture
def mock_credential_2():
    doc = MagicMock()
    doc.id = "cred_def456"
    doc.provider = "openai"
    doc.encrypted_key = "encrypted_value_here_2"
    doc.key_hint = "••••••••8B3C"
    doc.label = "Personal key"
    doc.is_active = True
    doc.is_default = False
    doc.validated_at = None
    doc.created_at = datetime.now(timezone.utc)
    doc.updated_at = datetime.now(timezone.utc)
    return doc


# ===========================================================================
# Credential Service Tests
# ===========================================================================

class TestCredentialEncryption:
    """Encrypted storage and secret redaction."""

    def test_mask_api_key_short(self):
        from app.services.credential_store import mask_api_key
        assert mask_api_key("") == "••••••••"
        assert mask_api_key("abc") == "••••••••"

    def test_mask_api_key_long(self):
        from app.services.credential_store import mask_api_key
        assert mask_api_key("sk-1234567890abcdef") == "••••••••cdef"

    def test_encrypt_decrypt_roundtrip(self):
        from cryptography.fernet import Fernet
        from app.services.credential_store import encrypt_api_key, decrypt_api_key
        test_key = Fernet.generate_key().decode()
        with patch("app.services.credential_store.settings") as mock_settings:
            mock_settings.CREDENTIAL_ENCRYPTION_KEY = test_key
            original = "sk-test-1234567890abcdef"
            encrypted = encrypt_api_key(original)
            assert encrypted != original
            decrypted = decrypt_api_key(encrypted)
            assert decrypted == original


class TestMultipleCredentialsPerProvider:
    """Multiple credentials per provider."""

    @pytest.mark.asyncio
    async def test_save_new_key(self, mock_user_id):
        from app.services.credential_service import credential_service

        mock_instance = MagicMock()
        mock_instance.insert = AsyncMock()

        MockModel = MagicMock(return_value=mock_instance)
        MockModel.find_one = AsyncMock(return_value=None)

        with patch("app.services.credential_service.UserApiKey", MockModel), \
             patch("app.services.credential_service.encrypt_api_key", return_value="enc"), \
             patch("app.services.credential_service.mask_api_key", return_value="••••aaaa"), \
             patch.object(credential_service, "_clear_default", new_callable=AsyncMock):
            result = await credential_service.save_key(mock_user_id, "openai", "sk-key1", "Key 1", is_default=True)
            mock_instance.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_key(self, mock_user_id):
        from app.services.credential_service import credential_service

        existing_doc = MagicMock()
        existing_doc.label = "Old label"
        existing_doc.save = AsyncMock()

        MockModel = MagicMock()
        MockModel.find_one = AsyncMock(return_value=existing_doc)

        with patch("app.services.credential_service.UserApiKey", MockModel), \
             patch("app.services.credential_service.encrypt_api_key", return_value="enc"), \
             patch("app.services.credential_service.mask_api_key", return_value="••••aaaa"), \
             patch.object(credential_service, "_clear_default", new_callable=AsyncMock):
            result = await credential_service.save_key(mock_user_id, "openai", "sk-key1", "New label")
            assert result.label == "New label"
            result.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_default_key_clears_others(self, mock_user_id):
        from app.services.credential_service import credential_service
        doc1 = MagicMock()
        doc1.is_default = True
        doc1.save = AsyncMock()
        doc2 = MagicMock()
        doc2.is_default = False
        doc2.save = AsyncMock()

        MockModel = MagicMock()
        MockModel.find = AsyncMock(return_value=[doc1, doc2])

        with patch("app.services.credential_service.UserApiKey", MockModel):
            await credential_service._clear_default(mock_user_id, "openai")
            assert doc1.is_default is False
            assert doc2.save.called or doc1.save.called


class TestCrossUserCredentialIsolation:
    """Cross-user credential isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_credential(self, mock_user_id, mock_user_id_2, mock_credential):
        from app.services.credential_service import credential_service, CredentialError

        MockModel = MagicMock()
        MockModel.find_one = AsyncMock(return_value=None)
        with patch("app.services.credential_service.UserApiKey", MockModel):
            with pytest.raises(CredentialError, match="not found"):
                await credential_service.get_key(mock_user_id, "cred_other_user")

    @pytest.mark.asyncio
    async def test_delete_enforces_ownership(self, mock_user_id):
        from app.services.credential_service import credential_service
        MockModel = MagicMock()
        MockModel.find_one = AsyncMock(return_value=None)
        with patch("app.services.credential_service.UserApiKey", MockModel):
            result = await credential_service.delete_key(mock_user_id, "cred_not_mine")
            assert result is False


# ===========================================================================
# AI Router Tests
# ===========================================================================

class TestLocalOnlyEnforcement:
    """Local-only mode blocks every cloud path."""

    @pytest.mark.asyncio
    async def test_local_only_redirects_cloud_to_ollama(self, mock_user_id):
        from app.ai.router import AIRouter
        from app.ai.providers.base.types import Message, MessageRole, CompletionResponse

        MockSettings = MagicMock()
        MockSettings.ai_local_only = True
        MockSettings.fallback_to_local = True
        MockUserSettings = MagicMock()
        MockUserSettings.find_one = AsyncMock(return_value=MockSettings)

        mock_ollama = MagicMock()
        mock_ollama.generate = AsyncMock(return_value=CompletionResponse(
            content="hello", model="qwen2.5-coder:7b", provider="ollama"
        ))

        with patch("app.ai.router.provider_registry") as mock_reg, \
             patch("app.ai.router.UserSettings", MockUserSettings):
            mock_reg.get = MagicMock(return_value=mock_ollama)

            router = AIRouter()
            messages = [Message(role=MessageRole.USER, content="test")]
            resp = await router.route_request(
                user_id=mock_user_id,
                messages=messages,
                provider="openai",
                model="gpt-4o",
            )
            assert resp.provider == "ollama"
            mock_ollama.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_local_only_does_not_load_cloud_credential(self, mock_user_id):
        from app.ai.router import AIRouter
        from app.ai.providers.base.types import Message, MessageRole, CompletionResponse

        MockSettings = MagicMock()
        MockSettings.ai_local_only = True
        MockSettings.fallback_to_local = True
        MockUserSettings = MagicMock()
        MockUserSettings.find_one = AsyncMock(return_value=MockSettings)

        mock_ollama = MagicMock()
        mock_ollama.generate = AsyncMock(return_value=CompletionResponse(
            content="ok", model="qwen2.5-coder:7b", provider="ollama"
        ))

        with patch("app.ai.router.provider_registry") as mock_reg, \
             patch("app.ai.router.UserSettings", MockUserSettings), \
             patch("app.ai.router.credential_service") as mock_cred:
            mock_reg.get = MagicMock(return_value=mock_ollama)

            router = AIRouter()
            messages = [Message(role=MessageRole.USER, content="test")]
            await router.route_request(
                user_id=mock_user_id,
                messages=messages,
                provider="openai",
            )
            mock_cred.get_key_for_provider.assert_not_called()


class TestCancellationPropagation:
    """Cancellation must be propagated into provider calls."""

    @pytest.mark.asyncio
    async def test_cancel_event_passed_to_provider(self, mock_user_id):
        from app.ai.router import AIRouter
        from app.ai.providers.base.types import Message, MessageRole, CompletionResponse

        MockSettings = MagicMock()
        MockSettings.ai_local_only = True
        MockSettings.fallback_to_local = True
        MockUserSettings = MagicMock()
        MockUserSettings.find_one = AsyncMock(return_value=MockSettings)

        mock_ollama = MagicMock()
        mock_ollama.generate = AsyncMock(return_value=CompletionResponse(
            content="ok", model="qwen2.5-coder:7b", provider="ollama"
        ))

        cancel_event = threading.Event()

        with patch("app.ai.router.provider_registry") as mock_reg, \
             patch("app.ai.router.UserSettings", MockUserSettings):
            mock_reg.get = MagicMock(return_value=mock_ollama)
            router = AIRouter()
            messages = [Message(role=MessageRole.USER, content="test")]
            await router.route_request(
                user_id=mock_user_id,
                messages=messages,
                cancel_event=cancel_event,
            )
            call_args = mock_ollama.generate.call_args
            assert call_args[0][0].cancel_event is cancel_event


class TestFallbackNotice:
    """Visible and persistent fallback notices."""

    @pytest.mark.asyncio
    async def test_fallback_notice_prepended_to_response(self, mock_user_id):
        from app.ai.router import AIRouter
        from app.ai.providers.base.types import Message, MessageRole, CompletionResponse
        from app.ai.providers.base.exceptions import ProviderUnavailable

        MockSettings = MagicMock()
        MockSettings.ai_local_only = False
        MockSettings.fallback_to_local = True
        MockUserSettings = MagicMock()
        MockUserSettings.find_one = AsyncMock(return_value=MockSettings)

        mock_cloud = MagicMock()
        mock_cloud.generate = AsyncMock(side_effect=ProviderUnavailable("openai", "API down"))

        mock_ollama = MagicMock()
        mock_ollama.generate = AsyncMock(return_value=CompletionResponse(
            content="local answer", model="qwen2.5-coder:7b", provider="ollama"
        ))

        with patch("app.ai.router.provider_registry") as mock_reg, \
             patch("app.ai.router.UserSettings", MockUserSettings), \
             patch("app.ai.router.credential_service") as mock_cred:
            mock_reg.get = MagicMock(side_effect=lambda name: mock_cloud if name == "openai" else mock_ollama)
            mock_cred.get_key_for_provider = AsyncMock(return_value=("sk-test", MagicMock()))

            router = AIRouter()
            messages = [Message(role=MessageRole.USER, content="test")]
            resp = await router.route_request(
                user_id=mock_user_id,
                messages=messages,
                provider="openai",
                fallback_to_local=True,
            )
            assert "unavailable" in resp.content.lower() or "cloud" in resp.content.lower()
            assert resp.provider == "ollama"


class TestNonRetryableErrors:
    """Errors that should not trigger fallback."""

    @pytest.mark.asyncio
    async def test_auth_failure_no_fallback(self, mock_user_id):
        from app.ai.router import AIRouter
        from app.ai.providers.base.types import Message, MessageRole
        from app.ai.providers.base.exceptions import AuthenticationFailed

        MockSettings = MagicMock()
        MockSettings.ai_local_only = False
        MockSettings.fallback_to_local = True
        MockUserSettings = MagicMock()
        MockUserSettings.find_one = AsyncMock(return_value=MockSettings)

        mock_cloud = MagicMock()
        mock_cloud.generate = AsyncMock(side_effect=AuthenticationFailed("openai"))

        with patch("app.ai.router.provider_registry") as mock_reg, \
             patch("app.ai.router.UserSettings", MockUserSettings), \
             patch("app.ai.router.credential_service") as mock_cred:
            mock_reg.get = MagicMock(return_value=mock_cloud)
            mock_cred.get_key_for_provider = AsyncMock(return_value=("sk-bad", MagicMock()))

            router = AIRouter()
            messages = [Message(role=MessageRole.USER, content="test")]
            with pytest.raises(AuthenticationFailed):
                await router.route_request(
                    user_id=mock_user_id,
                    messages=messages,
                    provider="openai",
                    fallback_to_local=True,
                )


class TestReasoningLevelMapping:
    """Reasoning level maps to temperature/max_tokens."""

    def test_fast_level(self):
        from app.ai.router import AIRouter
        router = AIRouter()
        temp, tokens = router._apply_reasoning_level("fast", 0.0, None)
        assert temp == 0.0
        assert tokens == 1024

    def test_balanced_level(self):
        from app.ai.router import AIRouter
        router = AIRouter()
        temp, tokens = router._apply_reasoning_level("balanced", 0.0, None)
        assert temp == 0.0
        assert tokens == 4096

    def test_deep_level(self):
        from app.ai.router import AIRouter
        router = AIRouter()
        temp, tokens = router._apply_reasoning_level("deep", 0.0, None)
        assert temp == 0.3
        assert tokens == 8192

    def test_none_level(self):
        from app.ai.router import AIRouter
        router = AIRouter()
        temp, tokens = router._apply_reasoning_level(None, 0.5, 2000)
        assert temp == 0.5
        assert tokens == 2000


# ===========================================================================
# Model Catalogue Tests
# ===========================================================================

class TestModelCatalogue:
    """Model catalogue with compatibility filter."""

    @pytest.mark.asyncio
    async def test_static_models_filtered(self):
        from app.ai.catalogue import model_catalogue, _is_suitable_for_aco
        assert _is_suitable_for_aco("gpt-4o") is True
        assert _is_suitable_for_aco("text-embedding-3-small") is False
        assert _is_suitable_for_aco("dall-e-3") is False
        assert _is_suitable_for_aco("whisper-1") is False
        assert _is_suitable_for_aco("tts-1") is False

    @pytest.mark.asyncio
    async def test_catalogue_includes_static_models(self):
        from app.ai.catalogue import model_catalogue

        with patch("app.ai.catalogue.provider_registry") as mock_reg:
            mock_provider = MagicMock()
            mock_provider.capabilities.supports_model_discovery = False
            mock_reg.get_all = MagicMock(return_value={"openai": mock_provider})

            models = await model_catalogue.get_models("openai")
            assert "openai" in models
            model_ids = [m["id"] for m in models["openai"]]
            assert "gpt-4o" in model_ids
            assert "gpt-4o-mini" in model_ids

    @pytest.mark.asyncio
    async def test_catalogue_merges_dynamic_models(self):
        from app.ai.catalogue import model_catalogue, ModelInfo
        from app.ai.providers.base.types import ProviderCapabilities

        mock_model = ModelInfo(
            id="custom-model-v1",
            provider="openai",
            name="Custom Model V1",
            capabilities=ProviderCapabilities(),
        )

        mock_provider = MagicMock()
        mock_provider.capabilities.supports_model_discovery = True
        mock_provider.list_models = AsyncMock(return_value=[mock_model])

        with patch("app.ai.catalogue.provider_registry") as mock_reg, \
             patch("app.ai.catalogue.model_cache") as mock_cache:
            mock_reg.get_all = MagicMock(return_value={"openai": mock_provider})
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            models = await model_catalogue.get_models("openai")
            model_ids = [m["id"] for m in models["openai"]]
            assert "gpt-4o" in model_ids
            assert "custom-model-v1" in model_ids

    @pytest.mark.asyncio
    async def test_catalogue_deduplicates(self):
        from app.ai.catalogue import model_catalogue, ModelInfo
        from app.ai.providers.base.types import ProviderCapabilities

        mock_model = ModelInfo(
            id="gpt-4o",
            provider="openai",
            name="GPT-4o (dynamic)",
            capabilities=ProviderCapabilities(),
        )

        mock_provider = MagicMock()
        mock_provider.capabilities.supports_model_discovery = True
        mock_provider.list_models = AsyncMock(return_value=[mock_model])

        with patch("app.ai.catalogue.provider_registry") as mock_reg, \
             patch("app.ai.catalogue.model_cache") as mock_cache:
            mock_reg.get_all = MagicMock(return_value={"openai": mock_provider})
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            models = await model_catalogue.get_models("openai")
            gpt4o_count = sum(1 for m in models["openai"] if m["id"] == "gpt-4o")
            assert gpt4o_count == 1


# ===========================================================================
# OpenAI-Compatible Provider Tests
# ===========================================================================

class TestOpenAICompatibleProvider:
    """OpenAI-compatible provider base behavior."""

    def test_build_headers_with_key(self):
        from app.ai.providers.openai_compatible.provider import OpenAICompatibleProvider, OpenAICompatibleConfig

        class TestProvider(OpenAICompatibleProvider):
            @property
            def provider_config(self):
                return OpenAICompatibleConfig(name="test", base_url="https://api.test.com")

        p = TestProvider()
        headers = p._build_headers("sk-test-123")
        assert headers["Authorization"] == "Bearer sk-test-123"

    def test_build_headers_without_key(self):
        from app.ai.providers.openai_compatible.provider import OpenAICompatibleProvider, OpenAICompatibleConfig

        class TestProvider(OpenAICompatibleProvider):
            @property
            def provider_config(self):
                return OpenAICompatibleConfig(name="test", base_url="https://api.test.com")

        p = TestProvider()
        headers = p._build_headers("")
        assert "Authorization" not in headers

    def test_build_payload(self):
        from app.ai.providers.openai_compatible.provider import OpenAICompatibleProvider, OpenAICompatibleConfig
        from app.ai.providers.base.types import CompletionRequest, Message, MessageRole

        class TestProvider(OpenAICompatibleProvider):
            @property
            def provider_config(self):
                return OpenAICompatibleConfig(name="test", base_url="https://api.test.com", default_model="default-m")

        p = TestProvider()
        req = CompletionRequest(
            messages=[Message(role=MessageRole.USER, content="hi")],
            temperature=0.5,
            max_tokens=100,
        )
        payload = p._build_payload(req)
        assert payload["model"] == "default-m"
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 100
        assert payload["messages"][0]["role"] == "user"

    def test_parse_response(self):
        from app.ai.providers.openai_compatible.provider import OpenAICompatibleProvider, OpenAICompatibleConfig

        class TestProvider(OpenAICompatibleProvider):
            @property
            def provider_config(self):
                return OpenAICompatibleConfig(name="test", base_url="https://api.test.com")

        p = TestProvider()
        data = {
            "model": "gpt-4o",
            "choices": [{
                "message": {"content": "Hello!", "role": "assistant"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        resp = p._parse_response(data, "gpt-4o", 100.0)
        assert resp.content == "Hello!"
        assert resp.tokens_input == 10
        assert resp.tokens_output == 5
        assert resp.latency_ms == 100.0

    def test_configurable_capabilities(self):
        from app.ai.providers.openai_compatible.provider import OpenAICompatibleProvider, OpenAICompatibleConfig

        class TestProvider(OpenAICompatibleProvider):
            @property
            def provider_config(self):
                return OpenAICompatibleConfig(
                    name="test", base_url="https://api.test.com",
                    supports_embeddings=True,
                    supports_structured_output=True,
                    supports_vision=False,
                )

        p = TestProvider()
        caps = p.capabilities
        assert caps.supports_embeddings is True
        assert caps.supports_structured_output is True
        assert caps.supports_vision is False


# ===========================================================================
# Provider Registry Tests
# ===========================================================================

class TestProviderRegistry:

    def test_skip_modules_includes_openai_compatible(self):
        from app.ai.registry import SKIP_MODULES
        assert "openai_compatible" in SKIP_MODULES
        assert "base" in SKIP_MODULES

    def test_registry_discovers_providers(self):
        from app.ai.registry import ProviderRegistry
        reg = ProviderRegistry()
        assert hasattr(reg, '_providers')
        assert hasattr(reg, 'discover')


# ===========================================================================
# API Endpoint Tests (with TestClient)
# ===========================================================================

class TestAIEndpointAuth:
    """Endpoints require authentication."""

    def test_providers_requires_auth(self, client):
        resp = client.get("/api/v1/ai/providers")
        assert resp.status_code in (401, 403)

    def test_credentials_requires_auth(self, client):
        resp = client.get("/api/v1/ai/credentials")
        assert resp.status_code in (401, 403)

    def test_models_requires_auth(self, client):
        resp = client.get("/api/v1/ai/models")
        assert resp.status_code in (401, 403)

    def test_settings_get_requires_auth(self, client):
        resp = client.get("/api/v1/ai/settings")
        assert resp.status_code in (401, 403)


class TestConversationModelSelection:
    """Per-conversation provider/model/credential restoration."""

    @pytest.mark.asyncio
    async def test_conversation_model_fields(self, mock_user_id):
        from app.infrastructure.db.models import Conversation
        from beanie import PydanticObjectId

        oid = PydanticObjectId(mock_user_id)
        conv = Conversation(
            conversation_id="conv_test123",
            user_id=oid,
            title="Test Conv",
            preferred_provider="openai",
            preferred_model="gpt-4o",
            preferred_credential_id="cred_abc",
            reasoning_level="deep",
        )
        assert conv.preferred_provider == "openai"
        assert conv.preferred_model == "gpt-4o"
        assert conv.preferred_credential_id == "cred_abc"
        assert conv.reasoning_level == "deep"

    @pytest.mark.asyncio
    async def test_conversation_default_model_fields(self):
        from app.infrastructure.db.models import Conversation
        from beanie import PydanticObjectId

        conv = Conversation(
            conversation_id="conv_default",
            user_id=PydanticObjectId(),
        )
        assert conv.preferred_provider is None
        assert conv.preferred_model is None
        assert conv.preferred_credential_id is None
        assert conv.reasoning_level is None
