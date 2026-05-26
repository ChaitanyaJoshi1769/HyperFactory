"""
HyperFactory API - Phase 2 Backend
Main FastAPI application for manufacturing orchestration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

load_dotenv()

# Import routers
from app.routers import hardware_router, supplier_router, factory_router, cad_router, auth_router, admin_router, websocket_router, files_router, search_router, webhooks_router
from app.exceptions import register_exception_handlers
from app.tasks.webhook_processor import WebhookProcessor

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()

def process_webhook_deliveries():
    """Background task to process pending webhook deliveries"""
    try:
        WebhookProcessor.process_pending_deliveries()
    except Exception as e:
        logger.error(f"Error processing webhook deliveries: {e}")

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 HyperFactory API starting up...")

    # Start webhook scheduler
    try:
        scheduler.add_job(
            process_webhook_deliveries,
            IntervalTrigger(seconds=60),
            id='webhook_processor',
            name='Process pending webhook deliveries',
            replace_existing=True,
            max_instances=1
        )
        scheduler.start()
        logger.info("✅ Webhook delivery processor scheduled (every 60 seconds)")
    except Exception as e:
        logger.error(f"Failed to start webhook scheduler: {e}")

    yield

    # Shutdown
    print("🛑 HyperFactory API shutting down...")
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✅ Webhook scheduler shut down")

# Initialize FastAPI app
app = FastAPI(
    title="HyperFactory API",
    description="Autonomous Hardware Iteration Operating System",
    version="0.2.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "HyperFactory API",
        "version": "0.2.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to HyperFactory API",
        "version": "0.2.0",
        "docs_url": "/docs",
        "status": "operational"
    }

# Include routers
app.include_router(hardware_router)
app.include_router(supplier_router)
app.include_router(factory_router)
app.include_router(cad_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(websocket_router)
app.include_router(files_router)
app.include_router(search_router)
app.include_router(webhooks_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
