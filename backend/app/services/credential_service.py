"""Centralized credential service.

Providers NEVER access the database. This service loads, decrypts, and passes
API keys temporarily into provider requests. It enforces per-user ownership
and supports multiple keys per provider via credential_id.
"""
import logging
from typing import Optional, Tuple, List
from datetime import datetime, timezone

from app.infrastructure.db.models import UserApiKey
from app.services.credential_store import encrypt_api_key, decrypt_api_key, mask_api_key

logger = logging.getLogger(__name__)


class CredentialError(Exception):
    def __init__(self, message: str, status_code: int = 404):
        self.status_code = status_code
        super().__init__(message)


class CredentialService:
    """Load, decrypt, and manage API credentials without exposing them to providers."""

    async def save_key(
        self,
        user_id: str,
        provider: str,
        api_key: str,
        label: str = "",
        is_default: bool = False,
        credential_id: Optional[str] = None,
    ) -> UserApiKey:
        """Save or update an API key. Returns the credential document (key never returned)."""
        encrypted = encrypt_api_key(api_key)
        hint = mask_api_key(api_key)

        existing = None
        if credential_id:
            existing = await UserApiKey.find_one(
                UserApiKey.id == credential_id,
                UserApiKey.user_id == user_id,
            )
        if not existing:
            existing = await UserApiKey.find_one(
                UserApiKey.user_id == user_id,
                UserApiKey.provider == provider,
            )

        now = datetime.now(timezone.utc)
        if existing:
            existing.encrypted_key = encrypted
            existing.key_hint = hint
            existing.label = label or existing.label
            existing.updated_at = now
            if is_default:
                await self._clear_default(user_id, provider)
                existing.is_default = True
            await existing.save()
            return existing

        if is_default:
            await self._clear_default(user_id, provider)

        doc = UserApiKey(
            user_id=user_id,
            provider=provider,
            encrypted_key=encrypted,
            key_hint=hint,
            label=label,
            is_active=True,
            is_default=is_default,
        )
        await doc.insert()
        return doc

    async def get_key(self, user_id: str, credential_id: str) -> Tuple[str, UserApiKey]:
        """Load and decrypt a key by credential_id. Enforces ownership.

        Returns (decrypted_key, credential_doc).
        Raises CredentialError if not found or ownership mismatch.
        """
        doc = await UserApiKey.find_one(
            UserApiKey.id == credential_id,
            UserApiKey.user_id == user_id,
        )
        if not doc:
            raise CredentialError("Credential not found", 404)
        if not doc.is_active:
            raise CredentialError("Credential is deactivated", 403)
        try:
            decrypted = decrypt_api_key(doc.encrypted_key)
        except Exception as e:
            raise CredentialError(f"Failed to decrypt credential: {e}", 500)
        return decrypted, doc

    async def get_key_for_provider(
        self,
        user_id: str,
        provider: str,
        credential_id: Optional[str] = None,
    ) -> Tuple[str, UserApiKey]:
        """Load and decrypt a key for a provider. Uses credential_id if given, else default.

        Returns (decrypted_key, credential_doc).
        Raises CredentialError if not found.
        """
        if credential_id:
            return await self.get_key(user_id, credential_id)

        doc = await UserApiKey.find_one(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == provider,
            UserApiKey.is_active == True,
            UserApiKey.is_default == True,
        )
        if doc:
            try:
                decrypted = decrypt_api_key(doc.encrypted_key)
                return decrypted, doc
            except Exception as e:
                raise CredentialError(f"Failed to decrypt credential: {e}", 500)

        doc = await UserApiKey.find_one(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == provider,
            UserApiKey.is_active == True,
        )
        if not doc:
            raise CredentialError(f"No active credential for provider '{provider}'", 404)
        try:
            decrypted = decrypt_api_key(doc.encrypted_key)
            return decrypted, doc
        except Exception as e:
            raise CredentialError(f"Failed to decrypt credential: {e}", 500)

    async def delete_key(self, user_id: str, credential_id: str) -> bool:
        """Delete a credential by ID. Enforces ownership."""
        doc = await UserApiKey.find_one(
            UserApiKey.id == credential_id,
            UserApiKey.user_id == user_id,
        )
        if not doc:
            return False
        await doc.delete()
        return True

    async def list_credentials(self, user_id: str) -> List[dict]:
        """List all credentials for a user. Returns masked data only — never the key."""
        docs = await UserApiKey.find(UserApiKey.user_id == user_id).sort(
            UserApiKey.created_at, -1
        )
        return [
            {
                "id": str(doc.id),
                "provider": doc.provider,
                "label": doc.label,
                "key_hint": doc.key_hint,
                "is_active": doc.is_active,
                "is_default": doc.is_default,
                "validated_at": doc.validated_at.isoformat() if doc.validated_at else None,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in docs
        ]

    async def set_default(self, user_id: str, credential_id: str) -> bool:
        """Set a credential as the default for its provider."""
        doc = await UserApiKey.find_one(
            UserApiKey.id == credential_id,
            UserApiKey.user_id == user_id,
        )
        if not doc:
            return False
        await self._clear_default(user_id, doc.provider)
        doc.is_default = True
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()
        return True

    async def deactivate_key(self, user_id: str, credential_id: str) -> bool:
        """Deactivate a credential without deleting it."""
        doc = await UserApiKey.find_one(
            UserApiKey.id == credential_id,
            UserApiKey.user_id == user_id,
        )
        if not doc:
            return False
        doc.is_active = False
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()
        return True

    async def validate_key(self, user_id: str, credential_id: str) -> dict:
        """Validate a credential by calling provider health check with the key.

        Returns validation result dict.
        """
        from app.ai.registry import provider_registry

        try:
            decrypted, doc = await self.get_key(user_id, credential_id)
        except CredentialError as e:
            return {"valid": False, "error": str(e)}

        provider = provider_registry.get(doc.provider)
        if not provider:
            return {"valid": False, "error": f"Provider '{doc.provider}' not registered"}

        try:
            from app.ai.providers.base.types import CompletionRequest, Message, MessageRole
            test_request = CompletionRequest(
                messages=[Message(role=MessageRole.USER, content="ping")],
                model=None,
                max_tokens=1,
                api_key=decrypted,
            )
            await provider.generate(test_request)
            doc.validated_at = datetime.now(timezone.utc)
            await doc.save()
            return {"valid": True, "provider": doc.provider}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def _clear_default(self, user_id: str, provider: str) -> None:
        """Remove default flag from all credentials of a provider for a user."""
        docs = await UserApiKey.find(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == provider,
            UserApiKey.is_default == True,
        )
        for doc in docs:
            doc.is_default = False
            doc.updated_at = datetime.now(timezone.utc)
            await doc.save()


credential_service = CredentialService()
