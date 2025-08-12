"""Database connection and initialization"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create declarative base
Base = declarative_base()


async def get_db_session() -> AsyncSession:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_database():
    """Initialize database and create tables"""
    try:
        logger.info("Initializing database...")
        
        # Test connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        
        logger.info("Database initialization complete")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_database():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")