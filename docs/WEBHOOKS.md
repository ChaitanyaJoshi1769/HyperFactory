# HyperFactory Webhooks API

## Overview

The HyperFactory Webhooks API enables event-driven integrations by allowing you to subscribe to events and receive HTTP callbacks when they occur. This is essential for building real-time integrations, monitoring systems, and automated workflows.

## Key Features

✅ **Event Subscriptions** - Subscribe to specific events or all events  
✅ **Reliable Delivery** - Automatic retries with exponential backoff  
✅ **Security** - HMAC-SHA256 signatures for webhook verification  
✅ **Delivery History** - Complete audit trail of all deliveries  
✅ **Testing** - Test webhooks before production use  
✅ **Management** - Full CRUD operations and secret rotation  

## Event Types

### Factory Events
- `factory.created` - New factory created
- `factory.updated` - Factory configuration updated
- `factory.deleted` - Factory deleted

### Machine Events
- `machine.created` - New machine added
- `machine.updated` - Machine configuration changed
- `machine.deleted` - Machine removed

### Job Events
- `job.created` - Production job created
- `job.started` - Job execution started
- `job.completed` - Job completed successfully
- `job.failed` - Job execution failed

### CAD Events
- `cad.analysis_completed` - CAD analysis finished
- `cad.analysis_failed` - CAD analysis failed

### Hardware Events
- `part.created` - New hardware part created
- `part.updated` - Part specification updated
- `part.deleted` - Part removed

### User/Account Events
- `user.created` - New user registered
- `user.updated` - User profile updated
- `api_key.created` - New API key generated
- `api_key.revoked` - API key revoked

## Getting Started

### 1. Create a Webhook

```bash
curl -X POST https://api.hyperfactory.com/api/webhooks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{
    "url": "https://yourserver.com/webhooks/factory",
    "events": ["factory.created", "factory.updated"],
    "description": "Monitor factory events",
    "max_retries": 5,
    "retry_delay_seconds": 60,
    "timeout_seconds": 30
  }'
```

**Response:**
```json
{
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "secret": "whsec_1234567890abcdef",
  "message": "Save this secret securely. You won't be able to retrieve it again."
}
```

⚠️ **Important:** Save the secret immediately. You cannot retrieve it again, but you can rotate it at any time.

### 2. Verify Webhook Signatures

Every webhook includes a signature header for verification:

```
X-HyperFactory-Signature: sha256=abc123...
X-HyperFactory-Timestamp: 1234567890
X-HyperFactory-Delivery-ID: delivery_123...
```

**Verification Example (Node.js):**

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(req, secret) {
  const signature = req.headers['x-hyperfactory-signature'];
  const timestamp = req.headers['x-hyperfactory-timestamp'];
  const deliveryId = req.headers['x-hyperfactory-delivery-id'];
  
  const body = JSON.stringify(req.body);
  const message = `${deliveryId}.${timestamp}.${body}`;
  
  const expectedSignature = 'sha256=' + crypto
    .createHmac('sha256', secret)
    .update(message)
    .digest('hex');
  
  return crypto.timingSafeEqual(signature, expectedSignature);
}

app.post('/webhooks/factory', (req, res) => {
  if (!verifyWebhookSignature(req, process.env.WEBHOOK_SECRET)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }
  
  const event = req.body;
  console.log(`Received event: ${event.event}`);
  res.json({ received: true });
});
```

**Verification Example (Python):**

```python
import hmac
import hashlib
import json

def verify_signature(signature, delivery_id, timestamp, body, secret):
    message = f"{delivery_id}.{timestamp}.{body}".encode()
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

@app.post('/webhooks/factory')
async def handle_webhook(request: Request):
    signature = request.headers.get('X-HyperFactory-Signature')
    timestamp = request.headers.get('X-HyperFactory-Timestamp')
    delivery_id = request.headers.get('X-HyperFactory-Delivery-ID')
    
    body = await request.body()
    
    if not verify_signature(signature, delivery_id, timestamp, body, os.getenv('WEBHOOK_SECRET')):
        return JSONResponse({'error': 'Invalid signature'}, status_code=401)
    
    event = json.loads(body)
    print(f"Received event: {event['event']}")
    return {'received': True}
```

### 3. Handle Webhook Payloads

All webhooks are sent as `POST` requests with this standard structure:

```json
{
  "event": "factory.created",
  "created_at": "2026-05-26T14:30:00Z",
  "version": "1.0",
  "data": {
    "factory_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Detroit Manufacturing Plant",
    "location": "Michigan, USA",
    "status": "operational"
  }
}
```

**Response Requirements:**
- Your endpoint must respond with HTTP 200-299 within 30 seconds (configurable)
- Any other response will be retried
- Return `{"received": true}` or similar to acknowledge receipt

## Webhook Management

### List Your Webhooks

```bash
curl -X GET https://api.hyperfactory.com/api/webhooks \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

### Get Webhook Details

```bash
curl -X GET https://api.hyperfactory.com/api/webhooks/{webhook_id} \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

### Update Webhook Configuration

```bash
curl -X PATCH https://api.hyperfactory.com/api/webhooks/{webhook_id} \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{
    "url": "https://newserver.com/webhooks",
    "events": ["factory.created"],
    "max_retries": 10
  }'
```

### Rotate Secret

```bash
curl -X POST https://api.hyperfactory.com/api/webhooks/{webhook_id}/rotate-secret \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

⚠️ **Warning:** The old secret will immediately stop working. Update your verification logic before rotating.

### Delete Webhook

```bash
curl -X DELETE https://api.hyperfactory.com/api/webhooks/{webhook_id} \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

## Testing Webhooks

### Send Test Event

```bash
curl -X POST https://api.hyperfactory.com/api/webhooks/{webhook_id}/test \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{
    "event_type": "factory.created",
    "payload": {
      "factory_id": "test-123",
      "name": "Test Factory"
    }
  }'
```

**Response:**
```json
{
  "delivery_id": "delivery_abc123...",
  "status": "success",
  "http_status_code": 200,
  "response_time_ms": 245,
  "success": true,
  "message": "Test webhook sent"
}
```

## Delivery History

### Get Delivery History

```bash
curl -X GET "https://api.hyperfactory.com/api/webhooks/{webhook_id}/deliveries?skip=0&limit=50" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

### Get Specific Delivery

```bash
curl -X GET https://api.hyperfactory.com/api/webhooks/{webhook_id}/deliveries/{delivery_id} \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

**Response:**
```json
{
  "id": "delivery_123...",
  "webhook_id": "webhook_456...",
  "event_type": "factory.created",
  "delivery_id": "delivery_abc123...",
  "status": "success",
  "http_status_code": 200,
  "response_time_ms": 150,
  "error_message": null,
  "attempt_number": 1,
  "created_at": "2026-05-26T14:30:00Z",
  "last_attempted_at": "2026-05-26T14:30:00Z",
  "completed_at": "2026-05-26T14:30:00Z"
}
```

### Filter by Status

```bash
# Only failed deliveries
curl -X GET "https://api.hyperfactory.com/api/webhooks/{webhook_id}/deliveries?status=failed" \
  -H "Authorization: Bearer YOUR_API_TOKEN"

# Statuses: pending, success, failed, timeout
```

### Retry Failed Delivery

```bash
curl -X POST https://api.hyperfactory.com/api/webhooks/{webhook_id}/deliveries/{delivery_id}/retry \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

## Best Practices

### ✅ Do's

1. **Verify signatures** - Always validate HMAC signatures to ensure authenticity
2. **Handle retries** - Implement idempotency using `X-HyperFactory-Delivery-ID`
3. **Respond quickly** - Return HTTP 200 as fast as possible, do heavy processing asynchronously
4. **Log events** - Keep audit trail of received webhooks
5. **Monitor health** - Check delivery history regularly
6. **Rotate secrets** - Rotate secrets periodically (quarterly recommended)
7. **Use HTTPS** - Always use HTTPS for webhook URLs in production

### ❌ Don'ts

1. **Don't ignore failures** - Monitor webhook delivery status
2. **Don't process without verification** - Always verify signatures
3. **Don't block on responses** - Process webhooks asynchronously
4. **Don't expose secrets** - Never commit secrets to version control
5. **Don't trust event order** - Events may not arrive in perfect order
6. **Don't hardcode webhook URLs** - Use configuration management
7. **Don't forget timeouts** - Set appropriate response timeouts

## Retry Logic

Webhooks use exponential backoff with the following defaults:

- **Initial delay**: 60 seconds
- **Backoff multiplier**: 2x
- **Max retries**: 5 (configurable)
- **Max delay**: 1 hour

Retry schedule with defaults:
1. Attempt 1: Immediate
2. Attempt 2: 60 seconds later
3. Attempt 3: 120 seconds later (2 min)
4. Attempt 4: 240 seconds later (4 min)
5. Attempt 5: 480 seconds later (8 min)
6. Attempt 6: 960 seconds later (16 min)

After max retries, the webhook is disabled automatically.

## Webhook Statuses

| Status | Meaning |
|--------|---------|
| `active` | Webhook is enabled and receiving events |
| `disabled` | Webhook exceeded max retries and was disabled |
| `failed` | Last delivery attempt failed |

## Webhook Delivery Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Waiting to be delivered |
| `success` | Successfully delivered (HTTP 200-299) |
| `failed` | Failed after all retries |
| `timeout` | Request timed out |

## Error Handling

### Common Issues

**Signature Verification Fails**
- Ensure secret is base64-decoded if stored encoded
- Check timestamp isn't too old (>5 minutes)
- Verify you're using the correct delivery ID
- Confirm the body JSON is not reformatted

**Webhook Disabled**
- Check delivery history for error reasons
- Rotate secret if it may be compromised
- Update URL and re-enable
- Monitor logs for application errors

**Deliveries Timing Out**
- Increase timeout configuration (up to 120 seconds)
- Optimize your endpoint response time
- Check for network connectivity issues
- Review application logs

## Rate Limits

Webhooks count against your API rate limits:
- Each webhook delivery = 1 API request equivalent
- Failed retries also count
- No additional cost for signature verification

## Monitoring

### Webhook Health Dashboard

Track webhook health metrics:
- Total deliveries
- Success rate
- Average response time
- Last failure timestamp
- Failed delivery count

```bash
curl -X GET https://api.hyperfactory.com/api/webhooks/{webhook_id}/stats \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

## Examples

### Example 1: Log All Factory Events

```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();
app.use(express.json());

const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;

function verifySignature(req) {
  const signature = req.headers['x-hyperfactory-signature'];
  const timestamp = req.headers['x-hyperfactory-timestamp'];
  const deliveryId = req.headers['x-hyperfactory-delivery-id'];
  
  const message = `${deliveryId}.${timestamp}.${JSON.stringify(req.body)}`;
  const expected = 'sha256=' + crypto
    .createHmac('sha256', WEBHOOK_SECRET)
    .update(message)
    .digest('hex');
  
  return crypto.timingSafeEqual(signature, expected);
}

app.post('/webhooks/factory', (req, res) => {
  try {
    if (!verifySignature(req)) {
      return res.status(401).json({ error: 'Invalid signature' });
    }
    
    const event = req.body;
    console.log(`[${event.created_at}] ${event.event}:`, event.data);
    
    res.json({ received: true });
  } catch (error) {
    console.error('Webhook error:', error);
    res.status(500).json({ error: 'Processing failed' });
  }
});

app.listen(3000, () => console.log('Webhook receiver listening on port 3000'));
```

### Example 2: Update Database on Job Completion

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json
import asyncio
from datetime import datetime

app = FastAPI()
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

def verify_signature(signature: str, delivery_id: str, timestamp: str, body: bytes):
    message = f"{delivery_id}.{timestamp}.".encode() + body
    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

@app.post('/webhooks/jobs')
async def handle_job_webhook(request: Request):
    signature = request.headers.get('X-HyperFactory-Signature')
    timestamp = request.headers.get('X-HyperFactory-Timestamp')
    delivery_id = request.headers.get('X-HyperFactory-Delivery-ID')
    
    body = await request.body()
    
    if not verify_signature(signature, delivery_id, timestamp, body):
        raise HTTPException(status_code=401, detail='Invalid signature')
    
    event = json.loads(body)
    
    if event['event'] == 'job.completed':
        job_id = event['data']['job_id']
        duration = event['data']['actual_duration_minutes']
        cost = event['data']['actual_cost']
        
        # Update database
        await update_job_record(job_id, {
            'completed_at': datetime.utcnow(),
            'duration_minutes': duration,
            'cost': cost
        })
        
        # Send notification
        await notify_team(f"Job {job_id} completed in {duration}min, cost: ${cost}")
    
    return {'received': True}
```

## API Reference

See `/api/webhooks` documentation at `https://api.hyperfactory.com/docs` for complete OpenAPI specification.

## Support

For issues or questions:
- Check delivery history for error details
- Review webhook logs in dashboard
- Contact: api-support@hyperfactory.com
