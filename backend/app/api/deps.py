from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from bson import ObjectId

from app.core.config import settings, normalize_email
from app.core.database import db_manager
from app.core.security import ALGORITHM
from app.infrastructure.db.models import User
from app.infrastructure.memory_db import memory_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def _find_user_by_email(email: str):
    """Find a user by email, handling both memory and MongoDB modes."""
    email = normalize_email(email)
    if db_manager.use_memory:
        user_doc = await memory_db.find_one("users", {"email": email})
        if not user_doc:
            return None
        return user_doc
    return await User.find_one(User.email == email)


def _user_from_doc(doc) -> User:
    """Create a minimal User-like object from a memory_db document or Beanie User."""
    if isinstance(doc, dict):
        user = User.model_construct(
            id=doc["_id"] if isinstance(doc["_id"], ObjectId) else ObjectId(doc["_id"]),
            email=doc.get("email", ""),
            name=doc.get("name", ""),
            avatar_url=doc.get("avatar_url"),
            role=doc.get("role", "user"),
            hashed_password=doc.get("hashed_password"),
            google_id=doc.get("google_id"),
        )
        return user
    return doc


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Dependency to retrieve and validate the authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await _find_user_by_email(email)
    if user is None:
        raise credentials_exception
    return _user_from_doc(user)


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role == "guest":
        raise HTTPException(status_code=400, detail="Inactive or Guest permissions.")
    return current_user


def get_user_id(user: User) -> str:
    """Returns the string user_id from an authenticated User. Single source of truth."""
    return str(user.id)


async def get_user_from_token(token: str) -> User:
    """Resolve a JWT token string to a User. For use in WebSocket handlers where
    Depends() injection is not available."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await _find_user_by_email(email)
    if user is None:
        raise credentials_exception
    return _user_from_doc(user)
