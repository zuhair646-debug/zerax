"""Renderer helpers — pure utilities used across render sub-modules."""
from typing import Any
import html as _html


def _esc(s: Any) -> str:
    return _html.escape(str(s or ""), quote=True)


_TYPE_LABELS = {
    "stories": "حالاتنا", "story_reel": "حالاتنا", "highlights": "أبرز المحطات",
    "banner": "عرض خاص", "promo_banner": "عرض خاص",
    "announce_bar_section": "إعلان",
    "events": "فعاليات قادمة", "blog": "مقالات", "news": "آخر الأخبار",
    "clients": "عملاؤنا", "partners": "شركاؤنا", "brands": "علامات تجارية",
    "awards": "جوائز وإنجازات", "timeline": "خط الزمن", "map": "موقعنا",
    "offers": "العروض", "services": "خدماتنا", "portfolio": "أعمالنا",
    "achievements": "إنجازاتنا", "stats": "إحصائيات", "instagram": "إنستقرام",
}

def _humanize_type(t: str) -> str:
    """Guess a user-friendly Arabic title for an unknown section type."""
    if not t:
        return "قسم مخصّص"
    if t in _TYPE_LABELS:
        return _TYPE_LABELS[t]
    return t.replace("_", " ").replace("-", " ").strip().title() or "قسم مخصّص"
