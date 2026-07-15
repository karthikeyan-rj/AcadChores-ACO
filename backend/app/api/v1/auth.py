from datetime import timedelta, datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.core.database import db_manager
from app.core.rate_limit import limiter
from app.core.config import settings
from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token
)
from app.infrastructure.db.models import User
from app.infrastructure.memory_db import memory_db
from app.api.deps import get_current_user

router = APIRouter()

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str

class GoogleAuthRequest(BaseModel):
    credential: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

def _user_dict(user) -> dict:
    if isinstance(user, dict):
        return {
            "id": str(user["_id"]),
            "email": user.get("email", ""),
            "name": user.get("name", ""),
            "avatar_url": user.get("avatar_url"),
            "role": user.get("role", "user"),
        }
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "role": user.role,
    }

def _token_response(user) -> dict:
    email = user.get("email", "") if isinstance(user, dict) else user.email
    access_token = create_access_token(data={"sub": email})
    refresh_token = create_refresh_token(data={"sub": email})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": _user_dict(user),
    }

@router.post("/register", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(request: Request, req: RegisterRequest):
    if db_manager.use_memory:
        existing = await memory_db.find_one("users", {"email": req.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered.")

        hashed_pw = get_password_hash(req.password)
        user_doc = {
            "email": req.email,
            "name": req.name,
            "hashed_password": hashed_pw,
            "avatar_url": None,
            "google_id": None,
            "role": "user",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        oid = await memory_db.insert("users", user_doc)
        user_doc["_id"] = oid
        return _token_response(user_doc)

    existing_user = await User.find_one(User.email == req.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed_pw = get_password_hash(req.password)
    user = User(
        email=req.email,
        name=req.name,
        hashed_password=hashed_pw,
        role="user"
    )
    await user.insert()
    return _token_response(user)

@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(request: Request, req: LoginRequest):
    if db_manager.use_memory:
        user_doc = await memory_db.find_one("users", {"email": req.email})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        if not verify_password(req.password, user_doc.get("hashed_password", "")):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        return _token_response(user_doc)

    user = await User.find_one(User.email == req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return _token_response(user)

@router.post("/login/form", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login_form(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    if db_manager.use_memory:
        user_doc = await memory_db.find_one("users", {"email": form_data.username})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        if not verify_password(form_data.password, user_doc.get("hashed_password", "")):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        return _token_response(user_doc)

    user = await User.find_one(User.email == form_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return _token_response(user)

@router.post("/google", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def google_auth(request: Request, req: GoogleAuthRequest):
    """Authenticate via Google Identity Services ID token."""
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        payload = google_id_token.verify_oauth2_token(
            req.credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Google auth library not installed. Run: pip install google-auth")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    google_email = payload.get("email")
    google_name = payload.get("name", "")
    google_picture = payload.get("picture", "")
    google_sub = payload.get("sub", "")

    if not google_email:
        raise HTTPException(status_code=401, detail="Google token missing email")

    if db_manager.use_memory:
        user_doc = await memory_db.find_one("users", {"email": google_email})
        if not user_doc:
            user_doc = {
                "email": google_email,
                "name": google_name,
                "avatar_url": google_picture,
                "google_id": google_sub,
                "role": "user",
                "hashed_password": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            oid = await memory_db.insert("users", user_doc)
            user_doc["_id"] = oid
        else:
            user_doc["google_id"] = google_sub
            if google_picture:
                user_doc["avatar_url"] = google_picture
            if google_name:
                user_doc["name"] = google_name
            await memory_db.update("users", {"_id": user_doc["_id"]}, user_doc)
        return _token_response(user_doc)

    user = await User.find_one(User.email == google_email)
    if not user:
        user = User(
            email=google_email,
            name=google_name,
            avatar_url=google_picture,
            google_id=google_sub,
            role="user",
        )
        await user.insert()
    else:
        user.google_id = google_sub
        if google_picture:
            user.avatar_url = google_picture
        if google_name:
            user.name = google_name
        await user.save()

    return _token_response(user)

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return _user_dict(user)
