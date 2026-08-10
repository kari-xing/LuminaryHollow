"""认证接口基础测试（需本地 PostgreSQL/Redis 可用时运行）。

运行：cd backend && python -m pytest tests -v
"""
import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_register_validation(client):
    resp = await client.post(
        "/api/auth/register",
        json={"username": "x", "password": "short"},  # 密码过短
    )
    assert resp.status_code == 422
