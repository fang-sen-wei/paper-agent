from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


# 访问 /health 检查健康状态
@router.get("/health", summary="Health Check")
async def health_check() -> dict[str,str]:
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "name": settings.APP_NAME,
        "env": settings.APP_ENV,
    }
