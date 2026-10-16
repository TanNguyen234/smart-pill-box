import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.models import User

password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    with request.app.state.session_factory() as db:
        yield db


def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Cần đăng nhập")
    try:
        claims = jwt.decode(
            credentials.credentials,
            request.app.state.jwt_secret,
            algorithms=["HS256"],
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Mã truy cập không hợp lệ hoặc đã hết hạn",
        )
    user = db.get(User, user_id)
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="Tài khoản không hoạt động")
    return user


def require_role(role: str):
    def dependency(user: User = Depends(require_user)) -> User:
        if user.role != role:
            raise HTTPException(
                status_code=403,
                detail="Không có quyền thực hiện thao tác này",
            )
        return user

    return dependency


caregiver_only = require_role("caregiver")
operator_only = require_role("operator")
