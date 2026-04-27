# Routers package
from .chat_router import router as chat_router, set_ai_assistant
from .deployment_router import router as deployment_router, set_deployment_service

__all__ = ['chat_router', 'set_ai_assistant', 'deployment_router', 'set_deployment_service']
