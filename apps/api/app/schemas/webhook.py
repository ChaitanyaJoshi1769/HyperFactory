"""Webhook schemas for request/response validation"""

from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import List, Optional
from uuid import UUID


class WebhookCreate(BaseModel):
    """Create a new webhook"""
    url: str = Field(..., description="Webhook URL to receive events")
    events: List[str] = Field(..., description="List of event types to subscribe to")
    description: Optional[str] = Field(None, description="Webhook description")
    max_retries: int = Field(5, ge=0, le=10, description="Maximum number of retries")
    retry_delay_seconds: int = Field(60, ge=10, le=3600, description="Delay between retries in seconds")
    timeout_seconds: int = Field(30, ge=5, le=120, description="Request timeout in seconds")


class WebhookUpdate(BaseModel):
    """Update webhook configuration"""
    url: Optional[str] = None
    events: Optional[List[str]] = None
    description: Optional[str] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_delay_seconds: Optional[int] = Field(None, ge=10, le=3600)
    timeout_seconds: Optional[int] = Field(None, ge=5, le=120)
    status: Optional[str] = Field(None, description="Webhook status (active/disabled)")


class WebhookRead(BaseModel):
    """Webhook response model"""
    id: UUID
    url: str
    status: str
    description: Optional[str]
    events: List[str]
    max_retries: int
    retry_delay_seconds: int
    timeout_seconds: int
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    last_delivery_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    last_failure_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryRead(BaseModel):
    """Webhook delivery response model"""
    id: UUID
    webhook_id: UUID
    event_type: str
    delivery_id: str
    status: str
    http_status_code: Optional[int]
    response_time_ms: Optional[int]
    error_message: Optional[str]
    attempt_number: int
    created_at: datetime
    last_attempted_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class WebhookDeliveryListRead(BaseModel):
    """List of webhook deliveries"""
    deliveries: List[WebhookDeliveryRead]
    total: int
    successful: int
    failed: int
    pending: int


class WebhookTestRequest(BaseModel):
    """Test webhook delivery request"""
    event_type: str = Field("test.event", description="Event type for test payload")
    payload: Optional[dict] = Field(None, description="Custom test payload")


class WebhookTestResponse(BaseModel):
    """Test webhook delivery response"""
    delivery_id: str
    status: str
    http_status_code: Optional[int]
    response_time_ms: int
    success: bool
    message: str


class WebhookSecret(BaseModel):
    """Webhook secret response (only on creation)"""
    webhook_id: UUID
    secret: str = Field(..., description="Secret key for HMAC signature verification")
    message: str = Field("Save this secret securely. You won't be able to retrieve it again.")


class WebhookPayload(BaseModel):
    """Standard webhook payload format"""
    event: str
    created_at: str
    data: dict
    version: str = "1.0"
