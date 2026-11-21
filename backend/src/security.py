import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .db import db, one

bearer = HTTPBearer(auto_error=False)


def make_token(user):
    payload = {"sub": str(user["id"]), "email": user["email"], "name": user["name"], "role": user["role"], "exp": datetime.now(timezone.utc) + timedelta(hours=8)}
    return jwt.encode(payload, os.getenv("JWT_SECRET", "dealer-renewal-demo-secret"), algorithm="HS256")


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(401, "需要登录")
    try:
        payload = jwt.decode(credentials.credentials, os.getenv("JWT_SECRET", "dealer-renewal-demo-secret"), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "登录已过期")
    with db() as conn:
        with conn.cursor() as cur:
            user = one(cur, "SELECT id,email,name,role,active FROM users WHERE id=%s", (payload["sub"],))
    if not user or not user["active"]:
        raise HTTPException(401, "账号不可用")
    return user


def require_roles(*roles):
    def dependency(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "当前岗位没有该操作权限")
        return user
    return dependency
