import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import bcrypt
from uuid import uuid4
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.event_bus import event_bus, SystemEvent
from app.infrastructure.db.models import PermissionPolicy, Rule

logger = logging.getLogger(__name__)

# JWT configuration
ALGORITHM = "HS256"

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "refresh": True})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionGuard:
    def __init__(self):
        # Maps request_id -> asyncio.Future for waiting responses
        self._pending_requests: Dict[str, asyncio.Future] = {}
        # Subscribe to permission.response event to resolve user overrides
        event_bus.subscribe("permission.response", self._handle_permission_response)

    async def authorize_action(self, agent_name: str, action: str, details: Dict[str, Any]) -> bool:
        """
        Validates if an action by an agent is permitted.
        Checks policy databases, and if policy is 'ask', prompts the user via the Event Bus and waits.
        """
        policy = await self._get_policy_for(agent_name, action)
        logger.info(f"PERM_CHECK: agent={agent_name}, action={action}, policy={policy}, details={details}")
        
        if policy == "allow":
            logger.info(f"Permission GRANTED for agent={agent_name}, action={action}")
            return True
        if policy == "block":
            logger.warning(f"Permission BLOCKED for agent={agent_name}, action={action}")
            return False

        # If policy is 'ask', request user confirmation
        request_id = str(uuid4())
        logger.info(f"Permission prompting user for agent={agent_name}, action={action}, req_id={request_id}")
        
        future = asyncio.get_running_loop().create_future()
        self._pending_requests[request_id] = future

        # Publish authorization request to the frontend (WebSockets / Client)
        await event_bus.publish(
            topic="permission.request",
            sender="PermissionGuard",
            payload={
                "request_id": request_id,
                "agent_name": agent_name,
                "action": action,
                "details": details
            }
        )

        try:
            # Wait for user input with a 60-second timeout
            approved = await asyncio.wait_for(future, timeout=60.0)
            return approved
        except asyncio.TimeoutError:
            logger.warning(f"Permission request {request_id} timed out. Defaulting to BLOCK.")
            return False
        finally:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]

    async def _get_policy_for(self, agent_name: str, action: str) -> str:
        """Fetches the permission level from permission_policies database collection."""
        # Built-in default rules (config-driven, always checked first)
        if agent_name == "browser":
            default = settings.DEFAULT_PERM_BROWSER
        elif agent_name == "desktop":
            default = settings.DEFAULT_PERM_DESKTOP
        elif agent_name == "terminal":
            default = settings.DEFAULT_PERM_TERMINAL
        elif agent_name == "file" and action == "delete":
            default = settings.DEFAULT_PERM_FILE_DELETE
        elif agent_name == "file" and action == "write":
            default = settings.DEFAULT_PERM_FILE_WRITE
        elif agent_name == "file" and action == "registry":
            default = settings.DEFAULT_PERM_REGISTRY
        elif agent_name == "file":
            default = "allow"
        else:
            default = "ask"

        # If config default is "allow" or "block", skip DB lookup — use it directly
        if default in ("allow", "block"):
            return default

        # Only query DB if config says "ask" (to allow DB-level overrides)
        try:
            policy_doc = await PermissionPolicy.find_one({"role": "user"})
            if policy_doc:
                for rule in policy_doc.rules:
                    if rule.agent == agent_name and rule.action == action:
                        return rule.policy
        except Exception:
            pass

        return default

    async def _handle_permission_response(self, event: SystemEvent) -> None:
        """Callback when user approves or blocks an action via permission.response event."""
        payload = event.payload
        request_id = payload.get("request_id")
        approved = payload.get("approved", False)

        logger.info(f"PERM_RESPONSE_HANDLER: received response for request_id={request_id}, approved={approved}, pending_keys={list(self._pending_requests.keys())}")

        if request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            if not future.done():
                future.set_result(approved)
                logger.info(f"PERM_RESPONSE_HANDLER: resolved future for request_id={request_id}: approved={approved}")
            else:
                logger.warning(f"PERM_RESPONSE_HANDLER: future already done for request_id={request_id}")
        else:
            logger.warning(f"PERM_RESPONSE_HANDLER: request_id={request_id} NOT FOUND in pending requests")

permission_guard = PermissionGuard()
