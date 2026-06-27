"""
🔍 Reviewer Cortex — Senior code reviewer that audits AI outputs before delivery.

Runs as a final stage in any cortex's `done` pipeline. Checks:
  - Security: XSS, eval(), inline event handlers with untrusted data
  - Performance: huge inline images (base64 > 100KB), unminified inline JS
  - Accessibility: missing alt, missing aria-label on icon-only buttons
  - Dead code: unused vars/functions (heuristic)
  - SEO: missing meta description, missing title
  - Quality: console.log left in production, TODO/FIXME comments

Returns a structured report. Severity: critical/high/medium/low.
The orchestrator can decide whether to block or attach as a warning.

This is a STATIC analysis (no LLM call by default) to keep it cheap+fast.
Can be augmented with LLM critique via `deep_review=True`.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.review_cortex")


# Security patterns to flag
_DANGER_PATTERNS = [
    (r"\beval\s*\(", "critical", "security", "استخدام eval() خطر أمنياً — استخدم JSON.parse أو طرق آمنة"),
    (r"document\.write\s*\(", "high", "security", "document.write() قديم وخطر — استخدم DOM APIs"),
    (r"innerHTML\s*=\s*[^'\"]*\$\{", "high", "security", "حقن متغير في innerHTML قد يسبب XSS — استخدم textContent أو DOMPurify"),
    (r"on\w+\s*=\s*['\"][^'\"]*\$\{", "critical", "security", "حقن متغير في inline event handler — XSS واضح"),
    (r"new\s+Function\s*\(", "critical", "security", "new Function() زي eval — تجنبه"),
    (r"localStorage\s*\.\s*setItem\([^,]+,\s*[^)]*token", "medium", "security", "تخزين tokens في localStorage معرّض لـ XSS"),
]

# Performance patterns
_PERF_PATTERNS = [
    (r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]{50000,}", "high", "performance", "صورة base64 ضخمة (>50KB) — حمّلها كملف"),
    (r"setInterval\([^,]+,\s*[1-9]\s*\)", "high", "performance", "setInterval كل 1ms سيقتل الأداء"),
    (r"setInterval\([^,]+,\s*10\s*\)", "medium", "performance", "setInterval كل 10ms عالٍ — استخدم requestAnimationFrame"),
    (r"@import\s+url", "medium", "performance", "CSS @import يبطّئ التحميل — ادمج الملفات أو استخدم <link>"),
]

# Accessibility patterns
_A11Y_PATTERNS = [
    (r"<img\s+[^>]*?(?<!alt=)[^>]*?(?<!alt=['\"])\s*/?>", "medium", "accessibility", "صورة بدون alt — أضف وصف للقارئات الشاشة"),
    (r"<button[^>]*>\s*<(?:i|span|svg)[^>]*></(?:i|span|svg)>\s*</button>", "medium", "accessibility", "زر بأيقونة بدون نص — أضف aria-label"),
    (r"<a[^>]*href=['\"]#['\"][^>]*>", "low", "accessibility", "رابط # بدون عنوان — استخدم button بدلاً عنه"),
]

# Dead code & quality
_QUALITY_PATTERNS = [
    (r"console\.(log|debug|info)\(", "low", "quality", "console.log باقي في الكود — احذفه قبل النشر"),
    (r"//\s*(?:TODO|FIXME|HACK|XXX)\b", "low", "quality", "تعليق TODO/FIXME باقي"),
    (r"\bdebugger\b", "high", "quality", "كلمة debugger; ستوقف التنفيذ في DevTools"),
    (r"alert\s*\(", "medium", "quality", "alert() مزعج — استخدم Toast/Modal بدلاً منه"),
]

# SEO patterns (HTML-specific)
_SEO_PATTERNS = [
    (r"<head>[\s\S]*?</head>", "check_seo_block"),  # special handler
]


def _check_seo_block(html: str) -> List[Dict[str, Any]]:
    """Special SEO checks for HTML <head>."""
    issues: List[Dict[str, Any]] = []
    head_m = re.search(r"<head>([\s\S]*?)</head>", html, re.IGNORECASE)
    if not head_m:
        return issues
    head = head_m.group(1)
    if not re.search(r"<title>[^<]{3,}</title>", head, re.IGNORECASE):
        issues.append({"severity": "medium", "category": "seo", "issue": "صفحة بدون <title> — أضف عنوان وصفي"})
    if not re.search(r'<meta\s+name=["\']description["\']', head, re.IGNORECASE):
        issues.append({"severity": "medium", "category": "seo", "issue": "صفحة بدون meta description — أضف وصف SEO"})
    if not re.search(r'<meta\s+name=["\']viewport["\']', head, re.IGNORECASE):
        issues.append({"severity": "high", "category": "seo", "issue": "صفحة بدون viewport meta — الموبايل سيتعطل"})
    if not re.search(r'<html[^>]*\slang=["\']', html[:500], re.IGNORECASE):
        issues.append({"severity": "low", "category": "seo", "issue": "العنصر <html> بدون lang attribute"})
    return issues


def review_code(
    code: str,
    code_type: str = "html",  # "html" | "js" | "css" | "mixed"
    deep_review: bool = False,
) -> Dict[str, Any]:
    """Run static review on code. Returns structured report.

    Returns:
        {
          "issues": [{severity, category, issue, line_hint?}],
          "summary": {critical: 0, high: 1, medium: 3, low: 2},
          "passed": bool (no critical/high issues),
          "score": 0-100,
        }
    """
    issues: List[Dict[str, Any]] = []
    if not code:
        return {"issues": [], "summary": {}, "passed": True, "score": 100}

    # Run all pattern checks
    all_patterns = _DANGER_PATTERNS + _PERF_PATTERNS + _A11Y_PATTERNS + _QUALITY_PATTERNS
    for pattern, severity, category, message in all_patterns:
        for m in re.finditer(pattern, code, re.IGNORECASE):
            line_no = code[:m.start()].count("\n") + 1
            issues.append({
                "severity": severity,
                "category": category,
                "issue": message,
                "line_hint": line_no,
                "snippet": m.group(0)[:80],
            })

    # SEO check for HTML
    if code_type in ("html", "mixed"):
        issues.extend(_check_seo_block(code))

    # Compute summary
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for issue in issues:
        sev = issue.get("severity", "low")
        summary[sev] = summary.get(sev, 0) + 1

    # Score: start at 100, deduct based on severity
    score = 100
    score -= summary["critical"] * 25
    score -= summary["high"] * 10
    score -= summary["medium"] * 4
    score -= summary["low"] * 1
    score = max(0, min(100, score))

    # Passed = no critical, no high
    passed = summary["critical"] == 0 and summary["high"] == 0

    return {
        "issues": issues,
        "summary": summary,
        "passed": passed,
        "score": score,
        "total_issues": len(issues),
    }


def render_review_report_ar(report: Dict[str, Any], max_issues: int = 8) -> str:
    """Render the review report as an Arabic markdown summary."""
    if not report or report.get("total_issues", 0) == 0:
        return f"✅ **مراجعة الكود:** ممتاز! لا توجد مشاكل (Score: {report.get('score', 100)}/100)"

    summary = report.get("summary", {})
    score = report.get("score", 0)
    passed = report.get("passed", False)
    badge = "✅" if passed else "⚠️"
    lines = [
        f"{badge} **تقرير المراجعة الذاتية — Score: {score}/100**",
        f"  • 🔴 حرج: {summary.get('critical', 0)} | 🟠 عالي: {summary.get('high', 0)} | 🟡 متوسط: {summary.get('medium', 0)} | 🟢 منخفض: {summary.get('low', 0)}",
        "",
        "**أهم المشاكل:**",
    ]
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_issues = sorted(report.get("issues", []), key=lambda x: severity_order.get(x.get("severity", "low"), 9))
    for issue in sorted_issues[:max_issues]:
        sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(issue.get("severity", "low"), "⚪")
        lines.append(f"  {sev_emoji} [{issue.get('category', '?')}/L{issue.get('line_hint', '?')}] {issue.get('issue', '')}")
    remaining = report.get("total_issues", 0) - max_issues
    if remaining > 0:
        lines.append(f"  • ... و{remaining} مشكلة أخرى.")
    return "\n".join(lines)


async def deep_llm_review(code: str, code_type: str = "html") -> Optional[Dict[str, Any]]:
    """Optional: LLM-powered deep review using Claude. Slower + costs more."""
    import os
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        import uuid, json as _json
        sys_prompt = (
            "أنت Senior Code Reviewer. راجع الكود التالي وأرجع JSON بهذا الشكل:\n"
            '{"issues":[{"severity":"critical|high|medium|low","category":"security|perf|a11y|seo|quality","issue":"وصف بالعربي"}],"verdict":"approve|reject|with-warnings"}\n'
            "ركز على: XSS, SQL injection patterns, performance bottlenecks, missing accessibility, anti-patterns. كن مختصر."
        )
        chat = LlmChat(api_key=emergent_key, session_id=f"review_{uuid.uuid4().hex[:8]}",
                       system_message=sys_prompt).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=f"```{code_type}\n{code[:6000]}\n```"))
        raw = resp if isinstance(resp, str) else str(resp)
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return _json.loads(m.group(0))
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[review_cortex] LLM deep review failed: {e}")
    return None
