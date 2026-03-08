from handlers.admin import router as admin_router
from handlers.cleaner import router as cleaner_router
from handlers.common import router as common_router
from handlers.manager import router as manager_router

__all__ = ["common_router", "admin_router", "manager_router", "cleaner_router"]
