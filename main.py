#!/usr/bin/env python3
"""
UWS WhatsApp AI Chatbot
Main application entry point
"""

import uvicorn
from src.app import create_app
from src.config import settings
from src.utils.logger import setup_logger


def main():
    """Main application entry point"""
    # Setup logging
    logger = setup_logger()
    
    # Create FastAPI application
    app = create_app()
    
    logger.info(f"Starting UWS WhatsApp Chatbot on {settings.APP_HOST}:{settings.APP_PORT}")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Run the application
    uvicorn.run(
        app,
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG,
        access_log=True
    )


if __name__ == "__main__":
    main()