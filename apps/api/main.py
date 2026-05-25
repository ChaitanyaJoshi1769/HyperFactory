"""
HyperFactory API - Phase 2 Backend
Main FastAPI application for manufacturing orchestration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

# Import routers
from app.routers import hardware_router, supplier_router, factory_router, cad_router

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 HyperFactory API starting up...")
    yield
    # Shutdown
    print("🛑 HyperFactory API shutting down...")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
