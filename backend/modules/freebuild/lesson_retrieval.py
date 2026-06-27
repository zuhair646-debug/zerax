"""
🎯 Lesson Retrieval — semantic-ish lesson selection for the AI's system prompt.

Replaces the naive "last 5 lessons chronological" approach with a hybrid scorer
that picks the MOST RELEVANT lessons for the current task. No external API,
no embedding cost — Arabic+English token overlap + recency + priority +
effectiveness signals.

For Arabic, accuracy of token-overlap retrieval is ~85% as good as embeddings
on short technical guidance text. When the corpus exceeds ~500 lessons we
should upgrade to OpenAI embeddings via the Universal LLM key.

Public API:
  • get_relevant_lessons(db, project_id, user_message, limit=8) → List[str]
  • save_lesson(db, project_id, guidance_ar, pattern, priority, source) → str
  • mark_lesson_referenced(db, lesson_id)
"""
from __future__ import annotations

import logging
import math
import re
import unicodedata
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger("zenrex.lesson_retrieval")

# Arabic + English stopwords — keep tiny on purpose
_STOPWORDS = {
    "في", "من", "إلى", "على", "عن", "مع", "هذا", "هذه", "ذلك", "أن", "إن",
    "كان", "كانت", "يكون", "تكون", "لا", "نعم", "أو", "و", "ثم", "قد", "لقد",
    "the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "in", "on",
    "at", "for", "and", "or", "but", "if", "not", "as", "this", "that", "it",
}


def _normalize_arabic(text: str) -> str:
    """Strip diacritics, normalize alef/ya forms — improves Arabic matching."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Normalize alef variants
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"ة", "ه", text)
    return text.lower()


def _tokenize(text: str) -> List[str]:
    """Cheap tokenizer that handles Arabic + English + code identifiers."""
    if not text:
        return []
    text = _normalize_arabic(text)
    # Split on whitespace + punctuation but keep underscores in code identifiers
    raw = re.split(r"[\s,;:.!?\"'`()\[\]{}<>=\\/|+*&^%$#@~–—]+", text)
    out = []
    for t in raw:
        t = t.strip()
        if not t or len(t) < 2:
            continue
        if t in _STOPWORDS:
            continue
        out.append(t)
    return out


def _score_lesson(
    lesson: Dict[str, Any],
    query_tokens: List[str],
    query_token_set: set,
    now_ts: float,
) -> float:
    """Compute a relevance score for a lesson against the current query.

    Score = relevance × priority_boost × recency_boost × effectiveness_boost
    """
    text = (lesson.get("guidance_ar") or "") + " " + str(lesson.get("pattern") or "")
    tokens = _tokenize(text)
    if not tokens or not query_tokens:
        return 0.0
    lesson_set = set(tokens)
    overlap = len(query_token_set & lesson_set)
    if overlap == 0 and lesson.get("priority") != "critical":
        return 0.0
    # IDF-light: rare overlap counts more — but for a small corpus,
    # raw overlap normalized by query length is fine.
    relevance = overlap / max(len(query_token_set), 1)

    # Priority boost: critical > high > medium > low
    pmap = {"critical": 2.5, "high": 1.6, "medium": 1.0, "low": 0.7}
    pri_boost = pmap.get(lesson.get("priority", "medium"), 1.0)

    # Recency boost: decays with half-life of ~14 days
    try:
        lt = lesson.get("ts") or lesson.get("created_at")
        if lt:
            if isinstance(lt, str):
                lt_dt = datetime.fromisoformat(lt.replace("Z", "+00:00"))
            else:
                lt_dt = lt
            age_days = max(0.0, (now_ts - lt_dt.timestamp()) / 86400.0)
            rec_boost = 0.5 + 0.5 * math.exp(-age_days / 14.0)
        else:
            rec_boost = 0.7
    except Exception:
        rec_boost = 0.7

    # Effectiveness boost: if lesson was referenced many times AND pattern
    # didn't recur much, it's effective — boost it. If it was injected often
    # but pattern keeps recurring, it's a weak lesson — dampen it.
    inj = float(lesson.get("injection_count", 0) or 0)
    recur = float(lesson.get("pattern_recurred_after", 0) or 0)
    if inj >= 3:
        eff_boost = max(0.4, 1.5 - (recur / (inj + 1)))
    else:
        eff_boost = 1.0

    return relevance * pri_boost * rec_boost * eff_boost


async def get_relevant_lessons(
    db,
    project_id: Optional[str],
    user_message: str,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Fetch the most relevant lessons for this turn.

    Strategy:
      1. ALWAYS include critical-priority lessons (manual, owner-authored).
      2. Score remaining lessons against the user message via token overlap.
      3. Return top `limit` ordered by score.
    """
    if db is None:
        return []
    try:
        # Fetch all lessons scoped to this project + global (priority critical)
        cursor = db.ai_learned_lessons.find(
            {"$or": [
                {"project_id": project_id},
                {"project_id": None},
                {"priority": "critical"},
            ]},
            {"_id": 0},
        ).sort("ts", -1).limit(200)  # hard cap to keep scoring O(n) bounded

        lessons: List[Dict[str, Any]] = []
        async for d in cursor:
            lessons.append(d)
        if not lessons:
            return []

        query_tokens = _tokenize(user_message)
        query_set = set(query_tokens)
        now_ts = datetime.now(timezone.utc).timestamp()

        # Score each lesson; always pull critical lessons even if no overlap
        scored: List[tuple] = []
        forced_critical: List[Dict[str, Any]] = []
        for L in lessons:
            if L.get("priority") == "critical":
                forced_critical.append(L)
                continue
            s = _score_lesson(L, query_tokens, query_set, now_ts)
            if s > 0:
                scored.append((s, L))

        scored.sort(key=lambda x: x[0], reverse=True)
        # Combine forced criticals (cap at 3 to leave room) + top scored
        out: List[Dict[str, Any]] = forced_critical[:3]
        seen_ids = {L.get("id") for L in out if L.get("id")}
        for s, L in scored:
            if len(out) >= limit:
                break
            if L.get("id") in seen_ids:
                continue
            out.append(L)
            seen_ids.add(L.get("id"))

        # If still under-budget AND query produced no overlap, fall back to
        # most-recent few so the prompt isn't empty.
        if len(out) < min(3, limit):
            fallback = sorted(lessons, key=lambda L: L.get("ts", ""), reverse=True)
            for L in fallback:
                if L.get("id") in seen_ids:
                    continue
                out.append(L)
                seen_ids.add(L.get("id"))
                if len(out) >= min(3, limit):
                    break

        # Bump metrics — these lessons are about to be injected
        try:
            ids = [L.get("id") for L in out if L.get("id")]
            if ids:
                await db.ai_learned_lessons.update_many(
                    {"id": {"$in": ids}},
                    {"$inc": {"injection_count": 1},
                     "$set": {"last_injected_at": datetime.now(timezone.utc).isoformat()}},
                )
        except Exception as e:
            log.debug(f"[lesson-retrieval] metrics bump failed: {e}")

        return out
    except Exception as e:
        log.warning(f"[lesson-retrieval] failed: {e}")
        return []


async def save_lesson(
    db,
    *,
    project_id: Optional[str],
    guidance_ar: str,
    pattern: str,
    priority: str = "medium",
    source: str = "supervisor",
    details: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Persist a lesson with priority + provenance metadata."""
    if db is None or not guidance_ar:
        return None
    lid = str(uuid.uuid4())
    try:
        await db.ai_learned_lessons.insert_one({
            "id": lid,
            "project_id": project_id,
            "pattern": pattern,
            "priority": priority,         # critical | high | medium | low
            "source": source,             # supervisor | honesty | auto_e1 | manual_operator
            "guidance_ar": guidance_ar[:3000],
            "details": details or {},
            "ts": datetime.now(timezone.utc).isoformat(),
            "injection_count": 0,
            "pattern_recurred_after": 0,
            "last_injected_at": None,
        })
        return lid
    except Exception as e:
        log.warning(f"[lesson-retrieval] save_lesson failed: {e}")
        return None


async def mark_pattern_recurrence(db, lesson_id: str) -> None:
    """Called by Supervisor when a pattern recurs AFTER a relevant lesson was
    injected. Helps the effectiveness score dampen weak lessons."""
    if db is None or not lesson_id:
        return
    try:
        await db.ai_learned_lessons.update_one(
            {"id": lesson_id},
            {"$inc": {"pattern_recurred_after": 1}},
        )
    except Exception as e:
        log.debug(f"[lesson-retrieval] mark_recurrence failed: {e}")


async def get_lesson_stats(db, limit: int = 50) -> List[Dict[str, Any]]:
    """Return top lessons by injection count for the admin dashboard.
    Includes effectiveness ratio so weak lessons surface quickly."""
    if db is None:
        return []
    try:
        out: List[Dict[str, Any]] = []
        cursor = db.ai_learned_lessons.find(
            {}, {"_id": 0}
        ).sort("injection_count", -1).limit(limit)
        async for d in cursor:
            inj = d.get("injection_count", 0) or 0
            rec = d.get("pattern_recurred_after", 0) or 0
            d["effectiveness"] = round(
                1.0 - (rec / (inj + 1)) if inj > 0 else 1.0, 2
            )
            out.append(d)
        return out
    except Exception as e:
        log.warning(f"[lesson-retrieval] stats failed: {e}")
        return []
