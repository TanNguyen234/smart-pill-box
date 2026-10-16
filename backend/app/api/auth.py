from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, password_hasher, require_user
from app.models import User
from app.schemas import LoginInput, UserOutput

router = APIRouter(tags=["1. Xác thực & Tài khoản (Vai trò 1)"])


@router.get("/api/health", summary="Kiểm tra trạng thái máy chủ")
def health():
    return {"status": "ok", "service": "smart-pill-box-api"}


@router.post("/api/auth/login", summary="Đăng nhập và cấp JWT Token")
def login(payload: LoginInput, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None or not user.active or not password_hasher.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    expires_at = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode(
        {"sub": str(user.id), "exp": expires_at, "iat": datetime.now(timezone.utc)},
        request.app.state.jwt_secret,
        algorithm="HS256",
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 28800,
        "user": UserOutput.model_validate(user),
    }


@router.get("/api/me", response_model=UserOutput, summary="Lấy thông tin tài khoản hiện tại")
def me(user: User = Depends(require_user)):
    return user
