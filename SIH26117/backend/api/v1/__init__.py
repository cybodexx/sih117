from backend.api.v1.attachments import router as attachments_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.documents import router as documents_router
from backend.api.v1.chat import router as chat_router
from backend.api.v1.chat_stream import router as chat_stream_router
from backend.api.v1.audit_sovereignty import router as audit_router
from backend.api.v1.health import router as health_router
from backend.api.v1.deliverables import router as deliverables_router
from backend.api.v1.layouts import router as layouts_router
from backend.api.v1.insights import router as insights_router

__all__ = [
    "attachments_router",
    "auth_router",
    "documents_router",
    "chat_router",
    "chat_stream_router",
    "audit_router",
    "health_router",
    "deliverables_router",
    "layouts_router",
    "insights_router",
]
