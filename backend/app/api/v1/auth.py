from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.core.rate_limit import limiter
from app.core.config import settings
from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token
)
from app.infrastructure.db.models import User
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
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "role": user.role,
    }

def _token_response(user) -> dict:
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": _user_dict(user),
    }

@router.post("/register", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(request: Request, req: RegisterRequest):
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
    user = await User.find_one(User.email == req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return _token_response(user)

@router.post("/login/form", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login_form(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
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
