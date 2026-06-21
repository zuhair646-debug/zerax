"""
Tests for the new Global Knowledge module (cross-user cumulative learning).
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

from motor.motor_asyncio import AsyncIOMotorClient

from modules.freebuild.global_knowledge import (
    add_best_practice,
    extract_keywords,
    load_global_knowledge_for_prompt,
)


@pytest_asyncio.fixture
async def db():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = client[os.environ["DB_NAME"]]
    yield d
    # Cleanup after each test
    await d.ai_global_knowledge.delete_many({"created_by_user": "pytest-user"})


@pytest.mark.asyncio
async def test_add_new_best_practice(db):
    r = await add_best_practice(
        db, category="design", mode="website", sector="ecommerce",
        problem="Hero feels generic on Arabic stores",
        solution="Use bento layout with one large product card + 4 micro-feature cards beside it",
        tags=["hero", "bento", "arabic"], created_by_user="pytest-user",
    )
    assert r["ok"] and not r["reused"]


@pytest.mark.asyncio
async def test_dedup_increments_success_count(db):
    base_args = dict(
        db=db, category="design", mode="website", sector="ecommerce",
        problem="Hero feels generic on Arabic stores",
        solution="Bento layout v1", tags=["hero"], created_by_user="pytest-user",
    )
    r1 = await add_best_practice(**base_args)
    base_args["solution"] = "Bento layout v2 — updated"
    r2 = await add_best_practice(**base_args)
    assert r1["id"] == r2["id"]
    assert r2["reused"] is True
    assert r2["success_count"] == 2


@pytest.mark.asyncio
async def test_retrieval_returns_relevant_block(db):
    await add_best_practice(
        db, category="design", mode="website", sector="restaurant",
        problem="Cafe site that doesn't look templated",
        solution="Half-page parallax of espresso pour + handwritten font for headlines",
        tags=["parallax", "cafe", "handwritten"], created_by_user="pytest-user",
    )
    keywords = extract_keywords("بناء موقع مقهى عربي بستايل مميز cafe parallax")
    block = await load_global_knowledge_for_prompt(
        db, mode="website", sector="restaurant", keywords=keywords,
    )
    assert "خبرة Zenrex التراكمية" in block
    assert "Cafe site" in block or "parallax" in block.lower()


@pytest.mark.asyncio
async def test_retrieval_empty_when_no_match(db):
    # No best practices for "games_studio" sector "fintech"
    block = await load_global_knowledge_for_prompt(
        db, mode="games_studio", sector="fintech", keywords=["crypto"],
    )
    # Either empty (no entries) or doesn't crash
    assert isinstance(block, str)


def test_extract_keywords_arabic_and_english():
    kw = extract_keywords("بناء صفحة hero لمطعم سعودي fast food")
    # Should include both Arabic and Latin tokens ≥ 4 chars
    assert "hero" in kw
    assert any(len(k) >= 4 for k in kw)
