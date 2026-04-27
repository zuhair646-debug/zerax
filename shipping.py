"""Pydantic models for the Websites module."""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class WebsiteSection(BaseModel):
    id: str = Field(default_factory=lambda: f"sec-{uuid.uuid4().hex[:8]}")
    type: str                     # hero, about, services, gallery, pricing, contact, cta, footer, testimonials, team, faq, features
    order: int = 0
    visible: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    style: Dict[str, Any] = Field(default_factory=dict)


class WebsiteProject(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    name: str = "موقعي الجديد"
    business_type: str = "company"   # store, restaurant, company, portfolio, real_estate, saas, blog
    template: str = "blank"
    lang: str = "ar"
    direction: str = "rtl"
    theme: Dict[str, Any] = Field(default_factory=lambda: {
        "primary": "#FFD700",
        "secondary": "#1a1f3a",
        "accent": "#FF6B35",
        "background": "#0b0f1f",
        "text": "#ffffff",
        "font": "Tajawal",
        "radius": "medium",
    })
    sections: List[WebsiteSection] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)   # site title, description, og image
    chat: List[Dict[str, Any]] = Field(default_factory=list)   # conversational history
    wizard: Optional[Dict[str, Any]] = None   # consultative wizard state
    status: Optional[str] = None   # draft | approved
    approved_at: Optional[str] = None
    slug: Optional[str] = None   # public URL slug for approved sites
    visits: Optional[int] = 0   # view counter for live link
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChatMessageIn(BaseModel):
    message: str
    business_type: Optional[str] = None


class AIGenerateIn(BaseModel):
    brief: str
    business_type: str = "company"
    name: Optional[str] = None
