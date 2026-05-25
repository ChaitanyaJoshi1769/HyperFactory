# HyperFactory WebSocket Real-Time Updates - Phase 3

Real-time event streaming for manufacturing, supply chain, and design operations.

## Overview

WebSocket support provides real-time updates for:
- Manufacturing events (job creation, status changes, completion)
- Supply chain updates (quotes, supplier changes)
- Design/CAD updates (model uploads, analysis completion)
- System events (user management, system alerts)

## Architecture

### Connection Manager (`app/websockets.py`)

Manages WebSocket connections and broadcasts.

```python
manager = ConnectionManager()

# Connect user to channel
connection_id = await manager.connect(websocket, user_id, channel)

# Broadcast to all in channel
await manager.broadcast(channel, message)

# Broadcast to specific user
await manager.broadcast_to_user(user_id, message)

# Send to single connection
await manager.unicast(websocket, message)
```

### Event Types

**Manufacturing Events**:
- `job_created`: Production job created
- `job_started`: Production job started
- `job_completed`: Production job completed
- `job_cancelled`: Production job cancelled
- `job_queued`: Production job queued
- `factory_update`: Factory metrics updated
- `machine_status`: Machine status changed

**System Events**:
- `user_created`: User account created
- `user_updated`: User profile updated
- `user_deleted`: User account deleted
- `system_alert`: System alert
- `system_status`: System status changed

**Supply Chain Events**:
- `supplier_created`: Supplier added
- `supplier_updated`: Supplier updated
- `quote_received`: New quote received
- `quote_expired`: Quote expired

**Design Events**:
- `model_uploaded`: CAD model uploaded
- `model_analyzed`: CAD model analyzed
- `analysis_complete`: DFM analysis complete

## Endpoints

### Manufacturing Updates

**URL**: `ws://localhost:8000/ws/manufacturing?token={jwt_token}`

Channels:
- `manufacturing`: All manufacturing events
- `manufacturing:{factory_id}`: Factory-specific events
- `production:{job_id}`: Specific job events

**Example - Subscribe to factory events**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/manufacturing?token=eyJ...');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Manufacturing event:', message);
};

// Subscribe to factory
ws.send(JSON.stringify({
  type: 'subscribe',
  data: {
    channel: 'manufacturing:factory_id_here'
  }
}));
```

### Supply Chain Updates

**URL**: `ws://localhost:8000/ws/supply-chain?token={jwt_token}`

Channels:
- `supply_chain`: All supply chain events
- `supplier:{supplier_id}`: Supplier-specific events

### Design Updates

**URL**: `ws://localhost:8000/ws/design?token={jwt_token}`

Channels:
- `design`: All design events
- `model:{model_id}`: Model-specific events

### System Updates

**URL**: `ws://localhost:8000/ws/system?token={jwt_token}`

Channels:
- `global`: System-wide events

### Unified Stream (Multi-Channel)

**URL**: `ws://localhost:8000/ws/stream?token={jwt_token}`

Subscribe to multiple channels in single connection.

## Message Format

### Incoming Messages

**Subscribe**:
```json
{
  "type": "subscribe",
  "data": {
    "channel": "manufacturing"
  }
}
```

**Ping** (keep-alive):
```json
{
  "type": "ping"
}
```

### Outgoing Messages

**Event**:
```json
{
  "type": "job_completed",
  "data": {
    "entity_type": "job",
    "entity_id": "job_uuid",
    "factory_id": "factory_uuid",
    "status": "completed",
    "duration_minutes": 45
  },
  "timestamp": "2026-05-25T12:30:45.123456"
}
```

**Pong** (response to ping):
```json
{
  "type": "pong",
  "timestamp": "2026-05-25T12:30:45.123456"
}
```

**Subscribed** (confirmation):
```json
{
  "type": "subscribed",
  "channel": "manufacturing",
  "timestamp": "2026-05-25T12:30:45.123456"
}
```

**Welcome** (initial connection):
```json
{
  "type": "welcome",
  "message": "Connected to HyperFactory real-time stream",
  "user_id": "user_uuid",
  "username": "john_doe"
}
```

**Error**:
```json
{
  "type": "error",
  "message": "Invalid channel"
}
```

## Usage Examples

### JavaScript/Browser

```javascript
// Establish connection
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
const ws = new WebSocket(`ws://localhost:8000/ws/stream?token=${token}`);

// Handle connection
ws.onopen = () => {
  console.log("Connected");
  
  // Subscribe to manufacturing events
  ws.send(JSON.stringify({
    type: 'subscribe',
    data: { channel: 'manufacturing' }
  }));
};

// Handle messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'job_completed') {
    console.log('Job completed:', message.data);
    updateUI(message);
  }
  
  // Keep connection alive
  if (message.type === 'pong') {
    console.log('Pong received');
  }
};

// Handle errors
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

// Handle disconnection
ws.onclose = () => {
  console.log("Disconnected");
  // Implement reconnection logic
};

// Send ping every 30 seconds
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  }
}, 30000);
```

### Python

```python
import asyncio
import json
import websockets
from datetime import datetime

async def listen_manufacturing(token: str):
    """Listen to manufacturing events"""
    uri = f"ws://localhost:8000/ws/manufacturing?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to factory events
        await websocket.send(json.dumps({
            "type": "subscribe",
            "data": {"channel": "manufacturing:factory_id"}
        }))
        
        # Listen for events
        async for message in websocket:
            event = json.loads(message)
            
            if event['type'] == 'job_completed':
                print(f"Job {event['data']['entity_id']} completed")
                process_event(event)
            
            # Keep alive with ping
            elif event['type'] == 'pong':
                print(f"Connection alive at {event['timestamp']}")

async def main():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    await listen_manufacturing(token)

if __name__ == "__main__":
    asyncio.run(main())
```

### React Hook

```javascript
import { useEffect, useRef, useState } from 'react';

export function useWebSocket(token, channel) {
  const ws = useRef(null);
  const [data, setData] = useState(null);
  const [status, setStatus] = useState('disconnected');

  useEffect(() => {
    if (!token) return;

    ws.current = new WebSocket(`ws://localhost:8000/ws/stream?token=${token}`);

    ws.current.onopen = () => {
      setStatus('connected');
      ws.current.send(JSON.stringify({
        type: 'subscribe',
        data: { channel }
      }));
    };

    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setData(message);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setStatus('error');
    };

    ws.current.onclose = () => {
      setStatus('disconnected');
    };

    return () => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.close();
      }
    };
  }, [token, channel]);

  const send = (message) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  };

  return { data, status, send };
}

// Usage
function ManufacturingDashboard() {
  const { data, status } = useWebSocket(token, 'manufacturing');

  return (
    <div>
      <p>Status: {status}</p>
      {data && <div>Latest event: {data.type}</div>}
    </div>
  );
}
```

## Broadcasting Events

### From Backend (in route handlers)

```python
from app.websockets import broadcast_manufacturing_event

# When job completes
await broadcast_manufacturing_event(
    event_type="job_completed",
    entity_id=str(job.id),
    entity_type="job",
    factory_id=str(factory.id),
    data={
        "status": "completed",
        "duration_minutes": 45,
        "completed_parts": 1000,
    }
)
```

### Manufacturing Events

```python
from app.websockets import broadcast_manufacturing_event

# Job created
await broadcast_manufacturing_event(
    event_type="job_created",
    entity_id=str(job.id),
    entity_type="job",
    factory_id=str(factory.id),
    data={"part_number": "PN-12345", "quantity": 100}
)

# Job started
await broadcast_manufacturing_event(
    event_type="job_started",
    entity_id=str(job.id),
    entity_type="job",
    factory_id=str(factory.id),
)

# Machine status
await broadcast_manufacturing_event(
    event_type="machine_status",
    entity_id=str(machine.id),
    entity_type="machine",
    factory_id=str(factory.id),
    data={"status": "idle", "utilization": 0.75}
)
```

### Supply Chain Events

```python
from app.websockets import broadcast_supply_chain_event

# Quote received
await broadcast_supply_chain_event(
    event_type="quote_received",
    entity_id=str(supplier.id),
    data={
        "supplier_name": "ACME Corp",
        "unit_price": 12.50,
        "lead_days": 14,
    }
)

# Supplier updated
await broadcast_supply_chain_event(
    event_type="supplier_updated",
    entity_id=str(supplier.id),
    data={"quality_score": 0.95}
)
```

### Design Events

```python
from app.websockets import broadcast_design_event

# Model uploaded
await broadcast_design_event(
    event_type="model_uploaded",
    model_id=str(model.id),
    data={"file_name": "bracket_v2.step", "file_size": 2048}
)

# Analysis complete
await broadcast_design_event(
    event_type="analysis_complete",
    model_id=str(model.id),
    data={"dfm_score": 0.89, "manufacturability": "excellent"}
)
```

### System Events

```python
from app.websockets import broadcast_system_event

# User created
await broadcast_system_event(
    event_type="user_created",
    data={"user_id": str(user.id), "username": "john_doe"}
)

# System alert
await broadcast_system_event(
    event_type="system_alert",
    data={"level": "warning", "message": "High factory utilization"}
)
```

## Best Practices

### Connection Management

1. **Validate tokens**: Always validate JWT before accepting WebSocket
2. **Clean disconnects**: Properly clean up on disconnect
3. **Connection pooling**: Reuse connections when possible
4. **Heartbeat/ping**: Send ping every 30-60 seconds to maintain connection

### Event Broadcasting

1. **Rate limiting**: Don't broadcast too frequently (batch updates)
2. **Filtering**: Only broadcast relevant events to subscribers
3. **Error handling**: Handle broadcast failures gracefully
4. **Logging**: Log all connections, disconnections, and errors

### Client-Side

1. **Reconnection**: Implement exponential backoff for reconnects
2. **Message buffering**: Buffer messages during disconnection
3. **Channel management**: Subscribe/unsubscribe cleanly
4. **Type safety**: Validate incoming messages

## Troubleshooting

### Connection fails with 401

- Verify JWT token is valid: `GET /api/auth/me`
- Check token hasn't expired
- Ensure `?token={token}` in URL

### No events received

- Verify subscription message was sent
- Check correct channel name
- Monitor browser console for errors

### Connection drops frequently

- Implement exponential backoff reconnection
- Send ping every 30 seconds
- Check server logs for errors

### High memory usage

- Limit number of concurrent connections
- Implement connection rate limiting
- Clean up old event buffers

## Performance Considerations

- Each connection uses minimal memory (~5KB)
- Broadcasting is O(n) where n = connected clients
- Consider load balancing with multiple servers
- Use pub/sub system (Redis) for distributed WebSocket servers

## Future Enhancements

1. **Selective Broadcasting**: Only send events to relevant subscribers
2. **Message Compression**: Gzip compress large payloads
3. **Authentication Refresh**: Support token refresh over WebSocket
4. **Presence**: Track who's currently viewing which resource
5. **History**: Replay recent events on connect
6. **Subscriptions**: Persist subscription preferences
7. **Metrics**: Dashboard for WebSocket metrics
8. **Load Balancing**: Distribute across multiple servers with sticky sessions

## See Also

- [Authentication Documentation](./AUTH.md)
- [API Documentation](./API.md)
- [Admin Documentation](./app/routers/admin.py)
