"""认证接口：注册 / 登录 / 刷新 / 登出。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserProfile
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair, UserOut

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    if not payload.email and not payload.phone:
        raise HTTPException(status_code=422, detail="邮箱与手机号至少填写一项")
    # 动态构建唯一性检查：仅在提供了对应字段时才比较（避免 `IS NULL` 误匹配）
    stmt = select(User)
    if payload.email:
        stmt = stmt.where(User.email == payload.email)
    if payload.phone:
        stmt = stmt.where(User.phone == payload.phone)
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"code": 4090, "message": "邮箱或手机号已注册"})

    user = User(
        username=payload.username,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    db.add(UserProfile(user_id=user.id))
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    result = await db.execute(
        select(User).where(or_(User.email == payload.account, User.phone == payload.account))
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"code": 4010, "message": "账号或密码错误"})
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: dict, db: AsyncSession = Depends(get_db)) -> TokenPair:
    refresh_token = payload.get("refresh_token", "")
    user_id = decode_token(refresh_token, expected_type="refresh")
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": 4010, "message": "refresh token 失效"})
    user = await db.get(User, uuid.UUID(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail={"code": 4010, "message": "用户不存在"})
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: dict) -> None:
    """原型实现：refresh token 加入 Redis 黑名单（TTL 7 天）。"""
    refresh_token = payload.get("refresh_token", "")
    jti_hash = refresh_token[-32:] if refresh_token else ""
    if jti_hash:
        await get_redis().set(f"rt_blacklist:{jti_hash}", "1", ex=7 * 24 * 3600)
