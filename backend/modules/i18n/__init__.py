"""i18n package — on-demand translation backed by Claude."""
from .translate_endpoint import router as translate_router

__all__ = ["translate_router"]
