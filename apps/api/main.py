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

# Import routers (will create these)
# from app.routers import hardware, suppliers, factory, dfm, cad

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

# Include routers (when created)
# app.include_router(hardware.router, prefix="/api/hardware", tags=["Hardware"])
# app.include_router(suppliers.router, prefix="/api/suppliers", tags=["Suppliers"])
# app.include_router(factory.router, prefix="/api/factory", tags=["Factory"])
# app.include_router(dfm.router, prefix="/api/dfm", tags=["DFM Analysis"])
# app.include_router(cad.router, prefix="/api/cad", tags=["CAD Processing"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
