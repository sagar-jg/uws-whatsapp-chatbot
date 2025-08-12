"""FastAPI Application Factory"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.config import settings
from src.api.routes import router
from src.middleware.rate_limiting import RateLimitMiddleware
from src.middleware.security import SecurityMiddleware
from src.database.connection import init_database
from src.services.vector_store import VectorStoreService
from src.services.mcp_manager import MCPManager
from src.utils.logger import get_logger
from src.utils.monitoring import prometheus_registry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting UWS WhatsApp Chatbot...")
    
    # Initialize database
    await init_database()
    
    # Initialize vector store
    vector_store = VectorStoreService()
    app.state.vector_store = vector_store
    
    # Initialize MCP Manager
    mcp_manager = MCPManager()
    await mcp_manager.initialize()
    app.state.mcp_manager = mcp_manager
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if hasattr(app.state, 'mcp_manager'):
        await app.state.mcp_manager.cleanup()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="UWS WhatsApp AI Chatbot",
        description="AI-powered WhatsApp chatbot for UWS student support",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Add security middleware
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.uws.ac.uk", "localhost", "127.0.0.1"]
        )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://*.uws.ac.uk"] if not settings.DEBUG else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Include routes
    app.include_router(router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "version": "1.0.0"}
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        if not settings.METRICS_ENABLED:
            return JSONResponse(
                status_code=404,
                content={"detail": "Metrics disabled"}
            )
        
        metrics_data = generate_latest(prometheus_registry)
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    return app