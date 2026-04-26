from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# 这是连接程序和数据库的引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_recycle=3600,
)


# 这是会话工厂，用于创建数据库会话
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 这是数据库会话生成器，用于获取数据库会话
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# 这是数据库初始化函数，用于初始化数据库
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_lightweight_schema_upgrades(conn)


async def _ensure_lightweight_schema_upgrades(conn) -> None:
    """
    中文说明：create_all 不会给已有表自动加新列。
    这里只补当前版本新增且可安全为空/有默认值的列，避免用户手动改数据库。
    """
    columns = await conn.run_sync(
        lambda sync_conn: {
            column["name"]
            for column in inspect(sync_conn).get_columns("chat_sessions")
        }
    )

    if "document_id" not in columns:
        await conn.execute(
            text("ALTER TABLE chat_sessions ADD COLUMN document_id INT NULL")
        )

    if "web_search_enabled" not in columns:
        await conn.execute(
            text(
                "ALTER TABLE chat_sessions "
                "ADD COLUMN web_search_enabled BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
