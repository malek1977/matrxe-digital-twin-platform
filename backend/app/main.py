"""
MATRXe - Digital Twin Platform
Backend Main Application
"""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict, Any

from app.config.settings import Settings, get_settings
from app.database.database import engine, Base, get_db
from app.middleware.auth import AuthMiddleware
from app.middleware.i18n import I18nMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.api.v1.api import api_router
from app.core.events import create_start_app_handler, create_stop_app_handler
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for the application
    """
    # Startup
    logger.info("🚀 Starting MATRXe Digital Twin Platform...")
    
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
    
    # Load AI models
    from app.ai_engine.loader import load_ai_models
    await load_ai_models()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down MATRXe...")
    await engine.dispose()

def create_application() -> FastAPI:
    """
    Create and configure FastAPI application
    """
    settings = get_settings()
    
    # Create app
    app = FastAPI(
        title="MATRXe Digital Twin Platform",
        description="Advanced AI-powered digital twin creation platform",
        version="1.0.0",
        docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
        redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
        openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Add trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )
    
    # Add custom middlewares
    app.add_middleware(AuthMiddleware)
    app.add_middleware(I18nMiddleware)
    app.add_middleware(RateLimiterMiddleware)
    
    # Add startup and shutdown events
    app.add_event_handler("startup", create_start_app_handler(app))
    app.add_event_handler("shutdown", create_stop_app_handler(app))
    
    # Include routers
    app.include_router(api_router, prefix="/api/v1")
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "service": "matrxe-backend",
            "version": "1.0.0",
            "timestamp": time.time(),
        }
    
    # Custom docs for production
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html(req: Request):
        root_path = req.scope.get("root_path", "").rstrip("/")
        openapi_url = root_path + app.openapi_url
        return get_swagger_ui_html(
            openapi_url=openapi_url,
            title="MATRXe API Documentation",
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )
    
    # Custom exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "details": getattr(exc, "details", None),
                },
                "timestamp": time.time(),
            },
        )
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": 500,
                    "message": "Internal server error",
                    "details": str(exc) if settings.DEBUG else None,
                },
                "timestamp": time.time(),
            },
        )
    
    return app

# Create application instance
app = create_application()

# Root endpoint
@app.get("/", tags=["Root"])
async def root(request: Request):
    """
    Root endpoint - Welcome to MATRXe
    """
    accept_language = request.headers.get("accept-language", "en")
    lang = accept_language.split(",")[0].split("-")[0] if accept_language else "en"
    
    welcome_messages = {
        "ar": "مرحباً بكم في منصة ماتركس إي للنسخ الرقمية الذكية",
        "en": "Welcome to MATRXe Digital Twin Platform",
        "fr": "Bienvenue sur la plateforme MATRXe de jumeaux numériques",
        "es": "Bienvenido a la plataforma MATRXe de gemelos digitales",
    }
    
    return {
        "success": True,
        "message": welcome_messages.get(lang, welcome_messages["en"]),
        "service": "MATRXe Backend API",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "api": "/api/v1",
            "health": "/health",
        },
        "timestamp": time.time(),
    }

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )