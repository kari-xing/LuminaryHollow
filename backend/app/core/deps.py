"""FastAPI 公共依赖：鉴权 / 分页 / 业务异常。"""
import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User


class BizError(Exception):
    """业务错误：code 见需求文档 §10.7。"""

    def __init__(self, code: int, message: str, http_status: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        self.http_status = http_status


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Bearer token 解析当前用户；失败抛 4010。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"code": 4010, "message": "未登录 / token 缺失"})
    token = authorization.split(" ", 1)[1].strip()
    user_id = decode_token(token, expected_type="access")
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": 4010, "message": "token 失效，请重新登录"})
    user = await db.get(User, uuid.UUID(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail={"code": 4010, "message": "用户不存在"})
    return user
