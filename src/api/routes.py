"""API Routes"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_session
from src.api.webhooks import whatsapp_webhook
from src.api.admin import admin_router
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(whatsapp_webhook.router, prefix="/webhook", tags=["webhook"])
router.include_router(admin_router, prefix="/admin", tags=["admin"])


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "UWS WhatsApp AI Chatbot API",
        "version": "1.0.0",
        "status": "operational"
    }


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db_session)):
    """Detailed status endpoint"""
    try:
        # Test database connection
        await db.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "components": {
                "database": "operational",
                "vector_store": "operational",
                "mcp_manager": "operational"
            },
            "timestamp": "2025-08-12T06:00:00Z"
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")