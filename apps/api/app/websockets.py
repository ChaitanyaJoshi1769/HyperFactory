"""WebSocket connection management for real-time updates"""

from fastapi import WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Set, Dict, List
from datetime import datetime
import json
from uuid import UUID

from app.db import get_db
from app.services.auth_service import AuthService
from app.models.user import User


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, str] = {}  # Maps connection id to user_id

    async def connect(self, websocket: WebSocket, user_id: str, channel: str):
        """
        Connect user to a channel.

        Channels:
        - global: All system events
        - manufacturing: All manufacturing events
        - manufacturing:{factory_id}: Factory-specific events
        - production:{job_id}: Specific job events
        """
        await websocket.accept()

        if channel not in self.active_connections:
            self.active_connections[channel] = []

        connection_id = str(UUID(int=len(self.active_connections[channel])))
        self.active_connections[channel].append(websocket)
        self.user_connections[connection_id] = user_id

        return connection_id

    async def disconnect(self, channel: str, websocket: WebSocket):
        """Disconnect user from channel"""
        if channel in self.active_connections:
            self.active_connections[channel].remove(websocket)

    async def broadcast(self, channel: str, message: dict):
        """Broadcast message to all connections in channel"""
        if channel not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(channel, connection)

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Broadcast message to all connections of a specific user"""
        user_channels = [
            (channel, ws)
            for channel, connections in self.active_connections.items()
            for ws in connections
            if self.user_connections.get(str(id(ws))) == user_id
        ]

        for channel, websocket in user_channels:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error sending to user {user_id}: {e}")

    async def unicast(self, websocket: WebSocket, message: dict):
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending unicast message: {e}")


# Global connection manager
manager = ConnectionManager()


# ============================================================================
# WebSocket Utilities
# ============================================================================

async def get_websocket_user(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate WebSocket connection and return authenticated user.

    Query parameter: token={jwt_token}
    """
    user_id = AuthService.verify_user_token(token)

    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

    user = AuthService.get_user(db, user_id)

    if not user or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid user")
        raise HTTPException(status_code=401, detail="Invalid user")

    return user


# ============================================================================
# Event Models
# ============================================================================

class Event:
    """Base event class for WebSocket messages"""

    def __init__(self, event_type: str, data: dict, timestamp: datetime = None):
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class ManufacturingEvent(Event):
    """Manufacturing-related events"""

    EVENT_TYPES = {
        "job_created": "Production job created",
        "job_started": "Production job started",
        "job_completed": "Production job completed",
        "job_cancelled": "Production job cancelled",
        "job_queued": "Production job queued",
        "factory_update": "Factory metrics updated",
        "machine_status": "Machine status changed",
    }

    def __init__(self, event_type: str, entity_id: str, entity_type: str,
                 data: dict, factory_id: str = None):
        if event_type not in self.EVENT_TYPES:
            raise ValueError(f"Unknown event type: {event_type}")

        super().__init__(event_type, {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "factory_id": factory_id,
            **data
        })


class SystemEvent(Event):
    """System-wide events"""

    EVENT_TYPES = {
        "user_created": "User account created",
        "user_updated": "User profile updated",
        "user_deleted": "User account deleted",
        "system_alert": "System alert",
        "system_status": "System status changed",
    }

    def __init__(self, event_type: str, data: dict):
        if event_type not in self.EVENT_TYPES:
            raise ValueError(f"Unknown event type: {event_type}")
        super().__init__(event_type, data)


class SupplyChainEvent(Event):
    """Supply chain related events"""

    EVENT_TYPES = {
        "supplier_created": "Supplier added",
        "supplier_updated": "Supplier updated",
        "quote_received": "New quote received",
        "quote_expired": "Quote expired",
    }

    def __init__(self, event_type: str, entity_id: str, data: dict):
        if event_type not in self.EVENT_TYPES:
            raise ValueError(f"Unknown event type: {event_type}")

        super().__init__(event_type, {
            "entity_id": entity_id,
            **data
        })


class DesignEvent(Event):
    """CAD/Design related events"""

    EVENT_TYPES = {
        "model_uploaded": "CAD model uploaded",
        "model_analyzed": "CAD model analyzed",
        "analysis_complete": "DFM analysis complete",
    }

    def __init__(self, event_type: str, model_id: str, data: dict):
        if event_type not in self.EVENT_TYPES:
            raise ValueError(f"Unknown event type: {event_type}")

        super().__init__(event_type, {
            "model_id": model_id,
            **data
        })


# ============================================================================
# Broadcast Helpers
# ============================================================================

async def broadcast_manufacturing_event(
    event_type: str,
    entity_id: str,
    entity_type: str,
    factory_id: str = None,
    data: dict = None,
):
    """
    Broadcast a manufacturing event to relevant channels.

    Channels:
    - manufacturing: All manufacturing events
    - manufacturing:{factory_id}: Factory-specific events
    - production:{entity_id}: Specific job events
    """
    event = ManufacturingEvent(
        event_type=event_type,
        entity_id=entity_id,
        entity_type=entity_type,
        factory_id=factory_id,
        data=data or {}
    )

    event_dict = event.to_dict()

    # Broadcast to manufacturing channel
    await manager.broadcast("manufacturing", event_dict)

    # Broadcast to factory-specific channel
    if factory_id:
        await manager.broadcast(f"manufacturing:{factory_id}", event_dict)

    # Broadcast to job-specific channel
    if entity_type == "job":
        await manager.broadcast(f"production:{entity_id}", event_dict)


async def broadcast_system_event(event_type: str, data: dict = None):
    """Broadcast system event to global channel"""
    event = SystemEvent(event_type, data or {})
    await manager.broadcast("global", event.to_dict())


async def broadcast_supply_chain_event(
    event_type: str,
    entity_id: str,
    data: dict = None,
):
    """Broadcast supply chain event"""
    event = SupplyChainEvent(event_type, entity_id, data or {})
    await manager.broadcast("supply_chain", event.to_dict())


async def broadcast_design_event(
    event_type: str,
    model_id: str,
    data: dict = None,
):
    """Broadcast design event"""
    event = DesignEvent(event_type, model_id, data or {})
    await manager.broadcast("design", event.to_dict())


# ============================================================================
# Connection Handlers
# ============================================================================

async def handle_ping(websocket: WebSocket, user_id: str):
    """Handle ping messages for keep-alive"""
    response = {
        "type": "pong",
        "timestamp": datetime.utcnow().isoformat(),
    }
    await manager.unicast(websocket, response)


async def handle_subscribe(websocket: WebSocket, user_id: str, data: dict):
    """
    Handle subscribe requests.

    Expected data:
    {
      "channel": "manufacturing"
    }
    """
    channel = data.get("channel")

    if not channel:
        error = {
            "type": "error",
            "message": "Channel required",
        }
        await manager.unicast(websocket, error)
        return

    # Validate channel format
    valid_channels = ["global", "manufacturing", "supply_chain", "design"]
    if not any(
        channel == c or channel.startswith(f"{c}:")
        for c in valid_channels
    ):
        error = {
            "type": "error",
            "message": "Invalid channel",
        }
        await manager.unicast(websocket, error)
        return

    response = {
        "type": "subscribed",
        "channel": channel,
        "timestamp": datetime.utcnow().isoformat(),
    }
    await manager.unicast(websocket, response)


async def handle_message(websocket: WebSocket, user_id: str, message: dict):
    """Route incoming messages to appropriate handlers"""
    msg_type = message.get("type")

    if msg_type == "ping":
        await handle_ping(websocket, user_id)
    elif msg_type == "subscribe":
        await handle_subscribe(websocket, user_id, message.get("data", {}))
    else:
        error = {
            "type": "error",
            "message": f"Unknown message type: {msg_type}",
        }
        await manager.unicast(websocket, error)
