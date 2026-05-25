"""API routers"""

from .hardware import router as hardware_router
from .supplier import router as supplier_router
from .factory import router as factory_router
from .cad import router as cad_router
from .auth import router as auth_router

__all__ = [
    "hardware_router",
    "supplier_router",
    "factory_router",
    "cad_router",
    "auth_router",
]
