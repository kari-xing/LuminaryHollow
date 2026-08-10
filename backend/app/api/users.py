"""用户接口：个人资料 / 画像 / 隐私模式。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.redis_client import set_privacy_mode
from app.models.user import User, UserProfile
from app.schemas.profile import ProfileIn, ProfileOut
from app.schemas.auth import UserOut
from app.services.memory_service import get_profile

router = APIRouter()


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/me/profile", response_model=ProfileOut)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    profile = await get_profile(db, user.id)
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


@router.put("/me/profile", response_model=ProfileOut)
async def update_my_profile(
    payload: ProfileIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    profile = await get_profile(db, user.id)
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    if payload.privacy_mode is not None:
        await set_privacy_mode(str(user.id), payload.privacy_mode)
    await db.commit()
    await db.refresh(profile)
    return profile
