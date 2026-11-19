from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from config import config


engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
Base = declarative_base()


async def get_session():
    async with async_session_maker() as session:
        yield session


async def init_db():
    from app import models

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db():
    await engine.dispose()
