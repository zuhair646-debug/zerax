"""
Zenrex AI Router — exposes claude_core to the frontend
======================================================
Thin HTTP layer over claude_core orchestrator.
All endpoints prefixed with /api/ai.

Owner: Zenrex Platform (Feb 2026)
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import claude_core
from routers.store_router import merchant_user, customer_user

log = logging.getLogger("ai_router")
router = APIRouter(prefix="/api/ai", tags=["ai"])


class ProductChatIn(BaseModel):
    prompt: str = Field(min_length=2, max_length=2000)
    user_spec: Optional[Dict[str, Any]] = None
    image_base64: Optional[str] = None
    session_id: Optional[str] = None


@router.post("/product-chat")
async def product_chat(body: ProductChatIn, u: dict = Depends(merchant_user)):
    """Main entry point — used by admin.html's AI chat tab."""
    res = await claude_core.product_research_chat(
        merchant_id=u["user_id"],
        user_prompt=body.prompt,
        user_spec=body.user_spec,
        image_base64=body.image_base64,
        session_id=body.session_id,
    )
    return res


class OnboardingIn(BaseModel):
    description: str = Field(min_length=10, max_length=4000)


@router.post("/onboarding/extract")
async def onboarding_extract(body: OnboardingIn, u: dict = Depends(merchant_user)):
    """Used at store handover — converts merchant's description into the AI profile."""
    profile = await claude_core.onboarding_extract(body.description)
    if "error" not in profile:
        # Auto-save to merchant_ai_profiles collection
        profile["merchant_id"] = u["user_id"]
        await claude_core.db.merchant_ai_profiles.update_one(
            {"merchant_id": u["user_id"]},
            {"$set": profile},
            upsert=True,
        )
    return profile


@router.get("/rules")
async def get_ai_rules():
    """Public — returns the core rules so frontend can display them transparently."""
    return claude_core.ZENREX_AI_CORE_RULES


@router.get("/health")
async def ai_health():
    import os
    return {
        "ok": True,
        "has_key": bool(os.environ.get("EMERGENT_LLM_KEY")),
        "rules_loaded": bool(claude_core.ZENREX_AI_CORE_RULES),
    }
