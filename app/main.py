from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import init_db

# 必须导入模型模块，确保 SQLAlchemy 在初始化数据库时已注册所有表结构。
import app.models 


# 使用生命周期管理器集中处理启动和关闭逻辑，替代分散的 on_event。
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 【项目启动前执行的代码放在这里】
    print("正在检查并初始化数据库表...")
    await init_db()
    print("数据库表初始化完成！")
    
    yield  # 这一步代表服务正在运行中...
    
    # 【项目关闭时执行的代码放在这里】
    print("正在关闭后端服务...")


def create_app() -> FastAPI:
    # 创建 FastAPI 应用，并挂载生命周期管理器
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # 添加中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加路由
    app.include_router(api_router, prefix=settings.API_PREFIX)

    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        return {
            "message": "Paper Agent backend is running",
            "env": settings.APP_ENV,
        }

    return app

app = create_app()
