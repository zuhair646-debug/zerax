"""
🗄️ Backend Patterns Library — loader for production-ready backend snippets.

Provides 15+ pre-built patterns (JWT, WebSocket, Rate Limit, Jobs, Stripe,
Resend Email, Twilio SMS, etc.) that the AI can inject into a new project
with one tool call.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.backend_patterns")

_PATTERNS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "backend_patterns.json"
_CACHE: Dict[str, Any] = {}


def _load() -> Dict[str, Any]:
    if "data" not in _CACHE or _CACHE.get("path_mtime") != _PATTERNS_PATH.stat().st_mtime:
        try:
            with open(_PATTERNS_PATH, encoding="utf-8") as f:
                _CACHE["data"] = json.load(f)
                _CACHE["path_mtime"] = _PATTERNS_PATH.stat().st_mtime
        except Exception as e:
            logger.error(f"failed to load patterns: {e}")
            _CACHE["data"] = {"patterns": {}}
    return _CACHE["data"]


def list_patterns() -> List[Dict[str, str]]:
    data = _load()
    return [
        {"id": pid, "name": p.get("name", pid), "ar_label": p.get("ar_label", ""),
         "category": p.get("category", ""), "framework": p.get("framework", "fastapi")}
        for pid, p in data.get("patterns", {}).items()
    ]


def get_pattern(pattern_id: str) -> Optional[Dict[str, Any]]:
    data = _load()
    return data.get("patterns", {}).get(pattern_id)


_INTENT_KEYWORDS = {
    "jwt_auth_fastapi": ["jwt", "auth", "تسجيل دخول", "login"],
    "password_hashing_bcrypt": ["bcrypt", "كلمة سر", "password hash"],
    "websocket_fastapi": ["websocket", "realtime", "بث مباشر", "live chat"],
    "rate_limiter_redis": ["rate limit", "حد طلبات", "throttle"],
    "background_jobs_arq": ["jobs", "queue", "مهام خلفية", "celery", "background task"],
    "stripe_subscription_checkout": ["stripe", "subscription", "اشتراك", "checkout"],
    "file_upload_local": ["upload", "رفع ملف", "file upload"],
    "email_resend": ["email", "بريد", "resend", "send email"],
    "sms_twilio": ["sms", "twilio", "رسالة نصية"],
    "cors_middleware": ["cors"],
    "logging_structured": ["logging", "logs", "تسجيل أحداث"],
    "mongo_connection": ["mongo", "mongodb"],
    "postgres_sqlmodel": ["postgres", "sql", "postgresql"],
    "scheduled_tasks_apscheduler": ["cron", "scheduled", "مهام مجدولة"],
    "search_meilisearch": ["search", "بحث", "meilisearch"],
}


def find_patterns_for_intent(user_message: str, max_results: int = 5) -> List[str]:
    if not user_message:
        return []
    msg = user_message.lower()
    scores: Dict[str, int] = {}
    for pid, kws in _INTENT_KEYWORDS.items():
        s = sum(1 for kw in kws if kw.lower() in msg)
        if s > 0:
            scores[pid] = s
    return [pid for pid, _ in sorted(scores.items(), key=lambda x: -x[1])[:max_results]]


def render_patterns_catalog(max_chars: int = 1600) -> str:
    data = _load()
    by_cat: Dict[str, List[str]] = {}
    for pid, p in data.get("patterns", {}).items():
        cat = p.get("category", "misc")
        by_cat.setdefault(cat, []).append(f"`{pid}` ({p.get('ar_label', p.get('name', pid))})")
    lines = [f"🗄️ **Backend Patterns Library — {sum(len(v) for v in by_cat.values())} نمط جاهز:**"]
    for cat, items in by_cat.items():
        lines.append(f"  • **{cat}:** {' | '.join(items[:5])}")
    return "\n".join(lines)[:max_chars]
