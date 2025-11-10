"""
Legal AI Vault - Main FastAPI Application
On-premises AI inference for legal/financial workflows
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
import sys

from config import settings
from database import engine, Base, check_db_connection
from routers import auth
from services.audit import AuditService

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/api.log') if not settings.DEBUG else logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Legal AI Vault API",
    description="On-premises AI inference for legal workflows",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    logger.info("Starting Legal AI Vault API...")

    # Check database connection
    if not check_db_connection():
        logger.error("Database connection failed!")
        raise Exception("Database connection failed")

    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

    # Initialize audit service
    AuditService.initialize()
    logger.info("Audit service initialized")

    logger.info(f"Legal AI Vault API started successfully (v{settings.VERSION})")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Legal AI Vault API...")


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests for audit purposes"""
    start_time = datetime.utcnow()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()

    # Log request
    logger.info(
        f"{request.method} {request.url.path} "
        f"Status: {response.status_code} "
        f"Duration: {duration:.3f}s "
        f"Client: {request.client.host}"
    )

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please contact support.",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
# app.include_router(agents.router, prefix="/api/agents", tags=["AI Agents"])
# app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])


# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    db_healthy = check_db_connection()

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "database": "connected" if db_healthy else "disconnected"
    }


# Root endpoint
@app.get("/")
async def root():
    """API root information"""
    return {
        "name": "Legal AI Vault API",
        "version": settings.VERSION,
        "docs": "/api/docs",
        "deployment": "on-premises",
        "environment": settings.ENVIRONMENT
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=settings.DEBUG
    )
