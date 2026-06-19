"""Zenrex HTML Validator & Auto-Healer — Tier-1 prevention layer.

Runs BEFORE the AI-generated HTML is saved to the project. Detects structural
defects, broken references, missing required elements, and security issues.
Returns a list of issues that the calling code uses to:
  • silently ask the AI for one corrective turn (auto-heal), OR
  • trigger Guardian if the corrective turn also fails.

The goal: <5% of generated sites should reach the customer with any defect.
"""

from __future__ import annotations

import re
from typing import Dict, List
from html.parser import HTMLParser

# ──────────────────────────────────────────────────────────────────────────────
# CHECKS LIBRARY
# Each check returns a list of issue dicts: {severity, code, msg, hint}
# Severity: critical | major | minor
# Critical/major issues trigger auto-heal; minor are advisory only.
# ──────────────────────────────────────────────────────────────────────────────


VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class _TagStackParser(HTMLParser):
    """Tracks open tag balance and reports mismatches."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: List[tuple] = []  # (tag, lineno, offset)
        self.errors: List[Dict] = []
        self.tag_counts: Dict[str, int] = {}

    def handle_starttag(self, tag, attrs):
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.lineno, self.offset))

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if not self.stack:
            self.errors.append({
                "severity": "major",
                "code": "stray_close",
                "msg": f"</{tag}> بلا فتح مقابل عند السطر {self.lineno}",
                "hint": f"احذف </{tag}> أو افتح <{tag}> قبله.",
            })
            return
        last_tag, last_line, _ = self.stack[-1]
        if last_tag == tag:
            self.stack.pop()
        else:
            # Mismatched — close the popped tag(s) and report
            self.errors.append({
                "severity": "major",
                "code": "tag_mismatch",
                "msg": f"</{tag}> بدل </{last_tag}> عند السطر {self.lineno} (فُتح في {last_line})",
                "hint": f"بدّل </{tag}> بـ </{last_tag}>، أو أغلق <{tag}> أولاً.",
            })
            # Try to recover by popping until match or empty
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break

    def close(self):
        super().close()
        # Anything left in stack is unclosed
        for tag, line, _ in self.stack:
            self.errors.append({
                "severity": "major",
                "code": "unclosed_tag",
                "msg": f"<{tag}> مفتوح بلا إغلاق عند السطر {line}",
                "hint": f"أضف </{tag}> في المكان المناسب.",
            })


def _check_structure(html: str) -> List[Dict]:
    """Verify the document has the basics."""
    issues: List[Dict] = []
    low = html.lower()
    if "<!doctype" not in low[:200]:
        issues.append({
            "severity": "major", "code": "missing_doctype",
            "msg": "DOCTYPE مفقود في بداية الملف.",
            "hint": "ابدأ الملف بـ <!DOCTYPE html>",
        })
    if "<html" not in low:
        issues.append({
            "severity": "critical", "code": "missing_html_tag",
            "msg": "وسم <html> مفقود.",
            "hint": "غلّف المحتوى بـ <html lang=\"ar\" dir=\"rtl\">...</html>",
        })
    if "<head" not in low:
        issues.append({
            "severity": "major", "code": "missing_head",
            "msg": "<head> مفقود — meta tags ضرورية للـSEO.",
            "hint": "أضف قسم <head> فيه title + meta description.",
        })
    if "<body" not in low:
        issues.append({
            "severity": "critical", "code": "missing_body",
            "msg": "<body> مفقود.",
            "hint": "غلّف المحتوى المرئي بـ <body>...</body>",
        })
    if "<title" not in low:
        issues.append({
            "severity": "major", "code": "missing_title",
            "msg": "<title> مفقود — مهم للـSEO وعرض التبويب.",
            "hint": "أضف <title>...</title> داخل <head>.",
        })
    if 'lang="ar"' not in low and "lang='ar'" not in low and "lang=ar" not in low:
        issues.append({
            "severity": "minor", "code": "missing_lang",
            "msg": "السمة lang=\"ar\" مفقودة على <html>.",
            "hint": "غيّر <html> إلى <html lang=\"ar\" dir=\"rtl\">",
        })
    if 'dir="rtl"' not in low and "dir='rtl'" not in low and "dir=rtl" not in low:
        issues.append({
            "severity": "minor", "code": "missing_rtl",
            "msg": "السمة dir=\"rtl\" مفقودة — سيؤثر على عرض النص العربي.",
            "hint": "أضف dir=\"rtl\" إلى <html>.",
        })
    if 'meta name="viewport"' not in low and "meta name='viewport'" not in low:
        issues.append({
            "severity": "major", "code": "missing_viewport",
            "msg": "viewport meta tag مفقود — الموقع لن يكون responsive على الجوال.",
            "hint": 'أضف <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        })
    if 'meta name="description"' not in low and "meta name='description'" not in low:
        issues.append({
            "severity": "minor", "code": "missing_meta_description",
            "msg": "meta description مفقودة — يضعف ظهور الموقع على Google.",
            "hint": "أضف <meta name=\"description\" content=\"وصف الموقع...\">",
        })
    return issues


def _check_internal_links(html: str) -> List[Dict]:
    """All <a href="#id"> targets must exist as id=... somewhere in the doc."""
    issues: List[Dict] = []
    # Collect every id="..."
    ids = set()
    for m in re.finditer(r'\bid\s*=\s*["\']([^"\']+)["\']', html, re.IGNORECASE):
        ids.add(m.group(1))
    # Find every internal href
    for m in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']#([^"\']+)["\']', html, re.IGNORECASE):
        target = m.group(1)
        if target and target not in ids:
            issues.append({
                "severity": "major",
                "code": "broken_anchor",
                "msg": f"الرابط href=\"#{target}\" يشير لقسم غير موجود.",
                "hint": f"إما أنشئ <section id=\"{target}\"> أو احذف الرابط.",
            })
    return issues


def _check_images(html: str) -> List[Dict]:
    """Images must have alt + valid src placeholder pattern."""
    issues: List[Dict] = []
    img_tags = re.findall(r'<img\b[^>]*>', html, re.IGNORECASE)
    for tag in img_tags:
        # Missing alt
        if not re.search(r'\balt\s*=', tag, re.IGNORECASE):
            issues.append({
                "severity": "minor",
                "code": "img_missing_alt",
                "msg": f"<img> بدون alt — يضر بـAccessibility والـSEO.",
                "hint": "أضف alt=\"وصف الصورة\" لكل صورة.",
            })
        # src that points to localhost / 127.0.0.1 / preview backend (will break on customer host)
        if re.search(r'src\s*=\s*["\'][^"\']*(?:localhost|127\.0\.0\.1|preview\.emergentagent)', tag, re.IGNORECASE):
            issues.append({
                "severity": "critical",
                "code": "img_local_url",
                "msg": "صورة تشير لـlocalhost/backend خاص بزنركس — ستنكسر عند العميل.",
                "hint": "استخدم Unsplash/Pexels CDN أو <<HERO:>> placeholder.",
            })
    return issues


def _check_script_balance(html: str) -> List[Dict]:
    """Naive JS syntax sanity: matching braces / parens / brackets in <script>."""
    issues: List[Dict] = []
    for script_match in re.finditer(r"<script\b[^>]*>(.*?)</script>", html, re.IGNORECASE | re.DOTALL):
        code = script_match.group(1)
        if not code.strip():
            continue
        # Strip string literals + comments to avoid false positives
        cleaned = re.sub(r'"(\\.|[^"\\])*"', '""', code)
        cleaned = re.sub(r"'(\\.|[^'\\])*'", "''", cleaned)
        cleaned = re.sub(r"`(\\.|[^`\\])*`", "``", cleaned)
        cleaned = re.sub(r"//[^\n]*", "", cleaned)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
        opens = {"(": ")", "[": "]", "{": "}"}
        stack: List[str] = []
        for ch in cleaned:
            if ch in opens:
                stack.append(opens[ch])
            elif ch in opens.values():
                if not stack or stack[-1] != ch:
                    issues.append({
                        "severity": "major",
                        "code": "js_brace_mismatch",
                        "msg": f"JavaScript قد يحتوي على خطأ في الأقواس (وجد '{ch}' بدون فتح مناسب).",
                        "hint": "افحص الـscripts للتأكد من تطابق الأقواس.",
                    })
                    break
                stack.pop()
        if stack:
            issues.append({
                "severity": "major",
                "code": "js_unclosed",
                "msg": f"JavaScript فيه أقواس مفتوحة بلا إغلاق: {''.join(stack)}",
                "hint": "أضف أقواس الإغلاق المفقودة.",
            })
    return issues


def _check_css(html: str) -> List[Dict]:
    """Naive CSS sanity: matching braces in <style> blocks."""
    issues: List[Dict] = []
    for m in re.finditer(r"<style\b[^>]*>(.*?)</style>", html, re.IGNORECASE | re.DOTALL):
        css = m.group(1)
        opens = css.count("{")
        closes = css.count("}")
        if opens != closes:
            issues.append({
                "severity": "major",
                "code": "css_brace_mismatch",
                "msg": f"CSS غير متوازن: {opens} '{{' مقابل {closes} '}}'.",
                "hint": "أضف أو احذف أقواس CSS حتى يتطابقا.",
            })
    return issues


def _check_security(html: str) -> List[Dict]:
    """Look for obvious security issues (inline event handlers calling external, secrets…)."""
    issues: List[Dict] = []
    secret_patterns = [
        (r"sk_live_[A-Za-z0-9]{20,}", "Stripe live secret key"),
        (r"sk_test_[A-Za-z0-9]{20,}", "Stripe test secret key"),
        (r"AIza[0-9A-Za-z\-_]{30,}", "Google API key"),
        (r"AKIA[0-9A-Z]{16}", "AWS access key"),
        (r"ghp_[A-Za-z0-9]{30,}", "GitHub personal access token"),
        (r"emergent[_-]?llm[_-]?key", "Emergent LLM key"),
    ]
    for pat, name in secret_patterns:
        if re.search(pat, html):
            issues.append({
                "severity": "critical",
                "code": "leaked_secret",
                "msg": f"الكود يحتوي على {name} — يجب حذفه فوراً.",
                "hint": "لا تضع مفاتيح API في HTML العام أبداً. استخدم backend proxy.",
            })
    return issues


def _check_size(html: str) -> List[Dict]:
    """Warn if size approaches limits."""
    issues: List[Dict] = []
    size_kb = len(html.encode("utf-8")) / 1024
    if size_kb > 300:
        issues.append({
            "severity": "minor",
            "code": "html_too_large",
            "msg": f"حجم الـHTML {size_kb:.0f}KB — يفضّل تقسيم الموقع لعدة صفحات.",
            "hint": "اقترح على العميل صفحات منفصلة (/about, /products) بدلاً من صفحة طويلة.",
        })
    return issues


def validate_html(html: str) -> Dict:
    """Run all checks and return a structured report.

    Output
    ------
    {
        "ok": bool,                  # True iff zero critical + zero major issues
        "size_kb": float,
        "issue_count": int,
        "critical": [issue, ...],
        "major":    [issue, ...],
        "minor":    [issue, ...],
        "summary":  "Arabic 1-line summary for log",
    }
    """
    if not html or not html.strip():
        return {
            "ok": False,
            "size_kb": 0,
            "issue_count": 1,
            "critical": [{
                "severity": "critical", "code": "empty",
                "msg": "الـHTML فارغ تماماً.",
                "hint": "ولّد الموقع كاملاً.",
            }],
            "major": [], "minor": [],
            "summary": "HTML فارغ",
        }

    all_issues: List[Dict] = []
    all_issues.extend(_check_structure(html))
    all_issues.extend(_check_internal_links(html))
    all_issues.extend(_check_images(html))
    all_issues.extend(_check_script_balance(html))
    all_issues.extend(_check_css(html))
    all_issues.extend(_check_security(html))
    all_issues.extend(_check_size(html))

    # Tag balance via parser (best-effort, swallow parser errors)
    try:
        parser = _TagStackParser()
        parser.feed(html)
        parser.close()
        all_issues.extend(parser.errors[:15])  # cap to avoid spam
    except Exception:  # noqa: BLE001
        pass

    critical = [i for i in all_issues if i["severity"] == "critical"]
    major = [i for i in all_issues if i["severity"] == "major"]
    minor = [i for i in all_issues if i["severity"] == "minor"]

    size_kb = round(len(html.encode("utf-8")) / 1024, 1)
    ok = len(critical) == 0 and len(major) == 0

    summary = (
        f"✅ OK ({size_kb}KB, {len(minor)} ملاحظات)"
        if ok
        else f"❌ {len(critical)} حرج + {len(major)} كبير + {len(minor)} ثانوي ({size_kb}KB)"
    )

    return {
        "ok": ok,
        "size_kb": size_kb,
        "issue_count": len(all_issues),
        "critical": critical,
        "major": major,
        "minor": minor,
        "summary": summary,
    }


def format_validation_for_ai(report: Dict) -> str:
    """Render the report as an Arabic block the AI can use to self-heal."""
    if report.get("ok"):
        return ""
    lines = ["\n[VALIDATION_REPORT — أصلح هذه المشاكل في ردك القادم بدون اعتذار]"]
    for kind, label in (("critical", "🔴 حرج"), ("major", "🟠 كبير")):
        for issue in report.get(kind, []):
            lines.append(f"  {label} [{issue['code']}]: {issue['msg']}")
            lines.append(f"     ↪ {issue['hint']}")
    lines.append("[/VALIDATION_REPORT]\n")
    lines.append("التزم بإصلاح كل المشاكل أعلاه. أرجع الـHTML كاملاً مصحَّحاً في ```html ... ``` block.")
    return "\n".join(lines)


__all__ = ["validate_html", "format_validation_for_ai"]
