"""
🧠 Cross-Project RAG — vector-based lesson retrieval.

Stores lessons (problem → solution pairs) from all projects in MongoDB
with embeddings. New projects can retrieve relevant lessons even if they
were solved in another project.

Uses Gemini embedding endpoint (cheaper) or OpenAI ada-002.

Schema (MongoDB collection `cross_project_lessons`):
  - id: uuid
  - problem: str (what went wrong)
  - solution: str (what fixed it)
  - tags: List[str] (e.g. ["xss", "cors", "react-state"])
  - project_id: str (source project)
  - embedding: List[float] (1536-d for openai-3-small)
  - created_at: datetime
  - uses_count: int (how many times retrieved & helpful)
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.cross_project_rag")


async def _get_embedding(text: str) -> Optional[List[float]]:
    """Use OpenAI text-embedding-3-small via Emergent key."""
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key or not text:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as cl:
            r = await cl.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {emergent_key}", "Content-Type": "application/json"},
                json={"model": "text-embedding-3-small", "input": text[:8000]},
            )
        if r.status_code != 200:
            logger.warning(f"[rag] embedding HTTP {r.status_code}: {r.text[:200]}")
            return None
        data = r.json()
        return data.get("data", [{}])[0].get("embedding")
    except Exception as e:
        logger.warning(f"[rag] embedding failed: {e}")
        return None


async def store_lesson(
    db, problem: str, solution: str,
    tags: Optional[List[str]] = None,
    project_id: Optional[str] = None,
) -> Optional[str]:
    """Store a lesson in the cross-project knowledge base."""
    if db is None or not problem or not solution:
        return None
    text = f"PROBLEM: {problem}\n\nSOLUTION: {solution}"
    emb = await _get_embedding(text)
    doc = {
        "id": str(uuid.uuid4()),
        "problem": problem[:2000],
        "solution": solution[:5000],
        "tags": (tags or [])[:10],
        "project_id": project_id,
        "embedding": emb,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "uses_count": 0,
    }
    try:
        await db.cross_project_lessons.insert_one(doc)
        return doc["id"]
    except Exception as e:
        logger.warning(f"[rag] insert failed: {e}")
        return None


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


async def retrieve_lessons(
    db, query: str,
    top_k: int = 5, min_similarity: float = 0.55,
    tags_filter: Optional[List[str]] = None,
    exclude_project_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve top-K most relevant lessons for a query."""
    if db is None or not query:
        return []
    q_emb = await _get_embedding(query)
    if not q_emb:
        return []
    # Pull candidates (filter by tags first to reduce candidate set)
    mongo_query: Dict[str, Any] = {"embedding": {"$exists": True}}
    if tags_filter:
        mongo_query["tags"] = {"$in": tags_filter}
    if exclude_project_id:
        mongo_query["project_id"] = {"$ne": exclude_project_id}
    try:
        cursor = db.cross_project_lessons.find(mongo_query, {"_id": 0}).limit(200)
        candidates = await cursor.to_list(length=200)
    except Exception as e:
        logger.warning(f"[rag] query failed: {e}")
        return []
    # Score
    scored = []
    for c in candidates:
        emb = c.get("embedding") or []
        sim = _cosine(q_emb, emb)
        if sim >= min_similarity:
            scored.append({**{k: c[k] for k in c if k != "embedding"}, "similarity": round(sim, 3)})
    scored.sort(key=lambda x: -x["similarity"])
    return scored[:top_k]


async def record_lesson_useful(db, lesson_id: str) -> None:
    """Increment uses_count when a lesson actually helped."""
    if db is None or not lesson_id:
        return
    try:
        await db.cross_project_lessons.update_one(
            {"id": lesson_id}, {"$inc": {"uses_count": 1}},
        )
    except Exception:
        pass


def render_lessons_hint_ar(lessons: List[Dict[str, Any]]) -> str:
    """Format retrieved lessons as a system-prompt hint."""
    if not lessons:
        return ""
    lines = [f"📚 **دروس متعلّمة من مشاريع سابقة ({len(lessons)} درس):**"]
    for i, l in enumerate(lessons, 1):
        sim = l.get("similarity", 0)
        tags = ", ".join(l.get("tags", [])[:3])
        lines.append(f"  {i}. [{tags}] (سيم: {sim}):")
        lines.append(f"     ❓ {(l.get('problem') or '')[:120]}")
        lines.append(f"     ✅ {(l.get('solution') or '')[:200]}")
    return "\n".join(lines)
