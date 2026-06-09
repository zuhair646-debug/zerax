"""Zerax Marketing Suite — owner-only AI marketing auto-pilot.

Generates daily content (text + image) targeting 5 audience personas,
publishes to connected channels (Telegram/Discord/Email/Twitter/WhatsApp/Instagram),
auto-replies to incoming messages, and tracks engagement.

All access restricted to is_owner=True users.
"""
from .routes import create_marketing_router

__all__ = ["create_marketing_router"]
