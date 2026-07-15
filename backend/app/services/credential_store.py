import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = settings.CREDENTIAL_ENCRYPTION_KEY
    if not key:
        key_bytes = Fernet.generate_key()
        logger.warning("No CREDENTIAL_ENCRYPTION_KEY set — using ephemeral key (keys will not persist across restarts)")
        return Fernet(key_bytes)
    if isinstance(key, str):
        key = key.encode()
    try:
        Fernet(key)
        return Fernet(key)
    except Exception:
        key_bytes = Fernet.generate_key()
        logger.warning("Invalid CREDENTIAL_ENCRYPTION_KEY — using ephemeral key")
        return Fernet(key_bytes)


def encrypt_api_key(api_key: str) -> str:
    f = _get_fernet()
    encrypted = f.encrypt(api_key.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_api_key(encrypted_b64: str) -> str:
    f = _get_fernet()
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_b64.encode())
    decrypted = f.decrypt(encrypted_bytes)
    return decrypted.decode()


def mask_api_key(api_key: str) -> str:
    if not api_key:
        return "••••••••"
    if len(api_key) <= 8:
        return "••••••••"
    return f"••••••••{api_key[-4:]}"


async def save_api_key(user_id: str, provider: str, api_key: str) -> dict:
    from app.core.database import db_manager

    encrypted = encrypt_api_key(api_key)
    hint = mask_api_key(api_key)

    if db_manager.use_memory:
        from app.infrastructure.memory_db import memory_db
        existing = await memory_db.find_one("user_api_keys", {"user_id": str(user_id), "provider": provider})
        if existing:
            await memory_db.update("user_api_keys",
                                   {"user_id": str(user_id), "provider": provider},
                                   {"encrypted_key": encrypted, "key_hint": hint})
        else:
            await memory_db.insert("user_api_keys", {
                "user_id": str(user_id),
                "provider": provider,
                "encrypted_key": encrypted,
                "key_hint": hint,
            })
        return {"provider": provider, "key_hint": hint}

    db = db_manager.db
    existing = await db.user_api_keys.find_one({"user_id": str(user_id), "provider": provider})
    if existing:
        await db.user_api_keys.update_one(
            {"_id": existing["_id"]},
            {"$set": {"encrypted_key": encrypted, "key_hint": hint}},
        )
    else:
        doc = {
            "user_id": str(user_id),
            "provider": provider,
            "encrypted_key": encrypted,
            "key_hint": hint,
        }
        await db.user_api_keys.insert_one(doc)

    return {"provider": provider, "key_hint": hint}


async def get_api_key(user_id: str, provider: str) -> Optional[str]:
    from app.core.database import db_manager

    if db_manager.use_memory:
        from app.infrastructure.memory_db import memory_db
        doc = await memory_db.find_one("user_api_keys", {"user_id": str(user_id), "provider": provider})
        if not doc:
            return None
        try:
            return decrypt_api_key(doc["encrypted_key"])
        except Exception as e:
            logger.error(f"Failed to decrypt API key for provider {provider}: {e}")
            return None

    db = db_manager.db
    doc = await db.user_api_keys.find_one({"user_id": str(user_id), "provider": provider})
    if not doc:
        return None
    try:
        return decrypt_api_key(doc["encrypted_key"])
    except Exception as e:
        logger.error(f"Failed to decrypt API key for provider {provider}: {e}")
        return None


async def get_api_key_hint(user_id: str, provider: str) -> Optional[str]:
    from app.core.database import db_manager

    if db_manager.use_memory:
        from app.infrastructure.memory_db import memory_db
        doc = await memory_db.find_one("user_api_keys", {"user_id": str(user_id), "provider": provider})
        if not doc:
            return None
        return doc.get("key_hint", "")

    db = db_manager.db
    doc = await db.user_api_keys.find_one({"user_id": str(user_id), "provider": provider})
    if not doc:
        return None
    return doc.get("key_hint", "")


async def delete_api_key(user_id: str, provider: str) -> bool:
    from app.core.database import db_manager

    if db_manager.use_memory:
        from app.infrastructure.memory_db import memory_db
        return await memory_db.delete("user_api_keys", {"user_id": str(user_id), "provider": provider})

    db = db_manager.db
    result = await db.user_api_keys.delete_one({"user_id": str(user_id), "provider": provider})
    return result.deleted_count > 0


async def list_api_keys(user_id: str) -> list:
    from app.core.database import db_manager

    if db_manager.use_memory:
        from app.infrastructure.memory_db import memory_db
        docs = await memory_db.find("user_api_keys", {"user_id": str(user_id)})
        return [{"provider": d["provider"], "key_hint": d.get("key_hint", "")} for d in docs]

    db = db_manager.db
    cursor = db.user_api_keys.find({"user_id": str(user_id)}, {"encrypted_key": 0})
    results = []
    async for doc in cursor:
        results.append({"provider": doc["provider"], "key_hint": doc.get("key_hint", "")})
    return results
