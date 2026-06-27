"""
🎯 Domain Classifier — pure regex + heuristics (zero LLM cost per request).

Returns DomainIntent with primary domain + optional secondary domains.

Domains:
  - "code"      : websites, apps, dashboards, HTML/JS, anything text-coded
  - "visual"    : image generation, logos, hero shots, mockups
  - "audio"     : voice synthesis, music, podcasts, jingles
  - "video"     : video clips, ads, animations, cinematic shots
  - "narrative" : copy writing, brand voice, scripts, stories, articles
  - "multi"     : the request mentions 2+ domains explicitly

The classifier favours FALSE NEGATIVES for non-code domains (i.e. when in
doubt → route to legacy code path). This is the safety bias.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class DomainIntent:
    primary: str = "code"
    secondary: List[str] = field(default_factory=list)
    confidence: float = 0.5
    rationale: str = ""


# Keyword sets — Arabic + English. Note: Arabic word boundaries (\b) are
# unreliable; we use look-arounds with whitespace/punctuation/start-of-string
# instead. The leading group `(?:^|[\s\W])` is the safe Arabic word boundary.
_VISUAL_KW = [
    r"(?:^|[\s\W])صور[ةا]?(?:$|[\s\W])", r"صورة", r"\bشعار\b", r"\blogo\b",
    r"\bimage\b", r"\bphoto\b", r"\bpicture\b", r"\billustration\b",
    r"\bmockup\b", r"\bposter\b", r"بوستر", r"ملصق", r"\bرسم\b", r"رسمة",
    r"\bicon\b", r"أيقونة", r"\bavatar\b", r"بروفايل\s*صور",
    r"\bhero\s*image\b", r"\bhero\s*shot\b", r"\bbanner\s*image\b",
    r"\bgenerate.*image\b", r"أنشئ?\s*صور", r"ولّد\s*صور", r"\bnano\s*banana\b",
    r"خلفية\s*صور", r"\bbackground\s*image\b",
]
_AUDIO_KW = [
    r"(?:^|[\s\W])صوت", r"صوتي", r"بصوت", r"\bsound\b", r"\baudio\b", r"\bvoice\b", r"\bvoiceover\b",
    r"تعليق\s*صوتي", r"تسجيل\s*صوتي", r"\bjingle\b", r"\bringtone\b",
    r"موسيقى", r"\bmusic\b", r"\bsoundtrack\b", r"\bmelody\b", r"تيون",
    r"\bnarration\b", r"\bsfx\b", r"\bsound\s*effect\b", r"مؤثر[ةا]?\s*صوتي",
    r"بودكاست", r"\bpodcast\b", r"\btext.?to.?speech\b", r"\btts\b",
    r"\belevenlabs\b", r"\bwhisper\b", r"اقرأ\s*(?:هذا\s*)?النص",
    r"رواي", r"تحدّث", r"انطق",
]
_VIDEO_KW = [
    r"فيديو", r"فيديوهات", r"\bvideo\b", r"\bclip\b", r"مقطع\s*مرئي",
    r"إعلان\s*(?:فيديو|متحرك|قصير)", r"\bvideo\s*ad\b",
    r"\banimation\s*video\b", r"\bcinematic\b", r"سينمائي",
    r"\bsora\b", r"\bkling\b", r"\bhailuo\b", r"\brunway\b", r"\bpika\b",
    r"تحريك\s*مشاهد?", r"\btrailer\b", r"تريلر",
    r"\bshort\s*film\b", r"فيلم\s*قصير", r"\breel\b", r"ريل",
]
_NARRATIVE_KW = [
    r"اكتب\s+(?:قصة|مقال|نص|سيناريو|رواية|قصيدة|بريد|محتوى)",
    r"(?:^|[\s\W])قصة", r"(?:^|[\s\W])رواية", r"(?:^|[\s\W])مقال",
    r"\barticle\b", r"\bblog\s*post\b", r"تدوينة",
    r"\bcopy(?:writing)?\b", r"\bsales\s*copy\b", r"\bemail\s*copy\b",
    r"\bbrand\s*voice\b", r"هوية\s*الكتابة",
    r"\bscript\b", r"سيناريو", r"سلوغان", r"\bslogan\b", r"\btagline\b",
    r"تقرير\s*(?:دراسة|بحث)", r"\bstudy\s*report\b",
    r"دراسة\s*جدوى", r"\bfeasibility\b",
]
_CODE_KW = [
    r"موقع", r"تطبيق", r"\bdashboard\b", r"\blanding\b",
    r"صفحة", r"\bpage\b", r"\bcode\b", r"\bweb\s*app\b", r"\bwebsite\b",
    r"\bhtml\b", r"\bjavascript\b", r"\breact\b", r"\bvue\b",
    r"\bbackend\b", r"\bfrontend\b", r"\bapi\b", r"\bdatabase\b",
    r"insert_html_at|inject_library|write_full_html|apply_section",
]


def _count_matches(text: str, patterns: list) -> int:
    n = 0
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            n += 1
    return n


def classify_intent_domain(message: str) -> DomainIntent:
    """Classify the message into one or more domains.

    Algorithm:
      1. Count keyword matches per domain.
      2. If only ONE domain has matches → that's primary, confidence high.
      3. If 2+ domains match → primary = highest-count, secondary = rest.
      4. If NO matches → primary = "code" (safe default).
    """
    if not message or not message.strip():
        return DomainIntent(primary="code", confidence=1.0, rationale="empty message → code default")

    msg = message.lower()
    scores = {
        "code":      _count_matches(msg, _CODE_KW),
        "visual":    _count_matches(msg, _VISUAL_KW),
        "audio":     _count_matches(msg, _AUDIO_KW),
        "video":     _count_matches(msg, _VIDEO_KW),
        "narrative": _count_matches(msg, _NARRATIVE_KW),
    }
    total = sum(scores.values())

    # No keyword hit anywhere → default to code (safe)
    if total == 0:
        return DomainIntent(primary="code", confidence=0.6,
                            rationale="no domain keywords matched → safe default code")

    # Find highest-scoring domain
    primary = max(scores, key=scores.get)
    primary_score = scores[primary]

    # Find secondary domains (any with score >= 1)
    secondary = []
    for d, s in scores.items():
        if d != primary and s >= 1:
            secondary.append(d)

    # Sort secondary by score (highest first)
    secondary.sort(key=lambda d: scores[d], reverse=True)

    # Multi-domain detection: explicit coordinator phrase OR 2+ domains scored
    is_multi_phrase = bool(re.search(
        r"و(?:كذلك|أيضا|أضف)|\bplus\b|\balong\s*with\b|بالإضافة|مع\s+(?:شعار|صور|فيديو|صوت|موسيقى)|\s\+\s",
        msg, re.IGNORECASE,
    ))
    is_multi_by_count = len(secondary) >= 1 and scores[primary] >= 1

    if (is_multi_phrase or is_multi_by_count) and len(secondary) >= 1:
        rationale = (
            f"multi-domain: primary={primary}({primary_score}), "
            f"secondary={secondary}, phrase={is_multi_phrase}, by_count={is_multi_by_count}"
        )
        return DomainIntent(
            primary=primary,
            secondary=secondary,
            confidence=0.85,
            rationale=rationale,
        )

    # Single-domain (with possible secondary noise we ignore)
    confidence = min(0.95, 0.5 + 0.1 * primary_score)
    return DomainIntent(
        primary=primary,
        secondary=[],
        confidence=confidence,
        rationale=f"primary={primary} (score={primary_score}/{total}); "
                  f"all_scores={scores}",
    )
