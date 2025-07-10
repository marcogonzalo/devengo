from src.api.integrations.endpoints.holded import router as holded_router
from src.api.integrations.endpoints.fourgeeks import router as fourgeeks_router
from src.api.integrations.endpoints.notion import router as notion_router

TRACKED_SYSTEMS = ["holded", "fourgeeks", "notion"]
__all__ = ["holded_router", "fourgeeks_router", "notion_router"]
