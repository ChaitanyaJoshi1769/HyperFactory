"""WebSocket endpoints for real-time updates"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.orm import Session
import json
import logging

from app.db import get_db
from app.websockets import (
    ConnectionManager,
    manager,
    get_websocket_user,
    handle_message,
)
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])


# ============================================================================
# Real-Time Manufacturing Updates
# ============================================================================

@router.websocket("/ws/manufacturing")
async def websocket_manufacturing(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time manufacturing updates.

    Connect with: ws://localhost:8000/ws/manufacturing?token={jwt_token}

    Channels:
    - manufacturing: All manufacturing events
    - manufacturing:{factory_id}: Factory-specific events
    - production:{job_id}: Specific job events

    Example subscription:
    {
      "type": "subscribe",
      "data": {
        "channel": "manufacturing"
      }
    }
    """
    user = await get_websocket_user(websocket, token, db)

    connection_id = await manager.connect(websocket, str(user.id), "manufacturing")
    logger.info(f"User {user.username} connected to manufacturing channel")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_message(websocket, str(user.id), message)

    except WebSocketDisconnect:
        await manager.disconnect("manufacturing", websocket)
        logger.info(f"User {user.username} disconnected from manufacturing channel")

    except json.JSONDecodeError:
        error = {"type": "error", "message": "Invalid JSON"}
        await websocket.send_json(error)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
        except:
            pass


# ============================================================================
# Supply Chain Updates
# ============================================================================

@router.websocket("/ws/supply-chain")
async def websocket_supply_chain(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for supply chain updates.

    Connect with: ws://localhost:8000/ws/supply-chain?token={jwt_token}

    Channels:
    - supply_chain: All supply chain events
    - supplier:{supplier_id}: Supplier-specific events
    """
    user = await get_websocket_user(websocket, token, db)

    connection_id = await manager.connect(websocket, str(user.id), "supply_chain")
    logger.info(f"User {user.username} connected to supply chain channel")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_message(websocket, str(user.id), message)

    except WebSocketDisconnect:
        await manager.disconnect("supply_chain", websocket)
        logger.info(f"User {user.username} disconnected from supply chain channel")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
        except:
            pass


# ============================================================================
# Design & Analysis Updates
# ============================================================================

@router.websocket("/ws/design")
async def websocket_design(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for CAD/design updates.

    Connect with: ws://localhost:8000/ws/design?token={jwt_token}

    Channels:
    - design: All design events
    - model:{model_id}: Model-specific events
    """
    user = await get_websocket_user(websocket, token, db)

    connection_id = await manager.connect(websocket, str(user.id), "design")
    logger.info(f"User {user.username} connected to design channel")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_message(websocket, str(user.id), message)

    except WebSocketDisconnect:
        await manager.disconnect("design", websocket)
        logger.info(f"User {user.username} disconnected from design channel")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
        except:
            pass


# ============================================================================
# System-Wide Updates
# ============================================================================

@router.websocket("/ws/system")
async def websocket_system(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for system-wide updates.

    Connect with: ws://localhost:8000/ws/system?token={jwt_token}

    Channels:
    - global: System-wide events

    Receive updates on:
    - User management events
    - System status changes
    - System alerts
    """
    user = await get_websocket_user(websocket, token, db)

    connection_id = await manager.connect(websocket, str(user.id), "global")
    logger.info(f"User {user.username} connected to system channel")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_message(websocket, str(user.id), message)

    except WebSocketDisconnect:
        await manager.disconnect("global", websocket)
        logger.info(f"User {user.username} disconnected from system channel")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
        except:
            pass


# ============================================================================
# Unified Multi-Channel WebSocket
# ============================================================================

@router.websocket("/ws/stream")
async def websocket_stream(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Unified WebSocket endpoint for subscribing to multiple channels.

    Connect with: ws://localhost:8000/ws/stream?token={jwt_token}

    Subscribe to multiple channels in one connection:
    {
      "type": "subscribe",
      "data": {
        "channel": "manufacturing"
      }
    }

    {
      "type": "subscribe",
      "data": {
        "channel": "manufacturing:factory_id"
      }
    }

    Send ping to keep connection alive:
    {
      "type": "ping"
    }
    """
    user = await get_websocket_user(websocket, token, db)

    connection_id = await manager.connect(websocket, str(user.id), "stream")
    logger.info(f"User {user.username} connected to unified stream")

    # Send welcome message
    welcome = {
        "type": "welcome",
        "message": "Connected to HyperFactory real-time stream",
        "user_id": str(user.id),
        "username": user.username,
    }
    await websocket.send_json(welcome)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_message(websocket, str(user.id), message)

    except WebSocketDisconnect:
        await manager.disconnect("stream", websocket)
        logger.info(f"User {user.username} disconnected from unified stream")

    except json.JSONDecodeError:
        error = {"type": "error", "message": "Invalid JSON"}
        try:
            await websocket.send_json(error)
        except:
            pass

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
        except:
            pass
