"""API routers"""

from .hardware import router as hardware_router
from .supplier import router as supplier_router
from .factory import router as factory_router
from .cad import router as cad_router
from .auth import router as auth_router
from .admin import router as admin_router
from .websocket import router as websocket_router
from .files import router as files_router
from .search import router as search_router
from .webhooks import router as webhooks_router

__all__ = [
    "hardware_router",
    "supplier_router",
    "factory_router",
    "cad_router",
    "auth_router",
    "admin_router",
    "websocket_router",
    "files_router",
    "search_router",
    "webhooks_router",
]
