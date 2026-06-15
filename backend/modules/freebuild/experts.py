"""Specialized Sub-Agent Experts for Zenrex Code Brain.

Each expert is a single-shot LLM call with:
  • A focused, expert-only system prompt (no general agent rules)
  • A constrained output JSON schema
  • No tools — pure reasoning over the context passed in

This mirrors how E1 (the meta-agent) calls dedicated sub-agents for
design / testing / troubleshooting / integration. The main agent decides
WHEN to call an expert; the expert decides WHAT to recommend.

All experts use the `direct_llm_shim` so no Emergent dependency.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("freebuild.experts")


# ─── Shared LLM helper ────────────────────────────────────────────────────────
async def _ask_expert(system_prompt: str, user_payload: str, *,
                       model: str = "claude-sonnet-4-5",
                       max_tokens: int = 2500) -> str:
    """Call the LLM with a focused expert prompt and return raw text."""
    try:
        from anthropic import AsyncAnthropic
        api_key = (os.environ.get("ANTHROPIC_API_KEY")
                   or os.environ.get("ANTHROPIC_DIRECT_KEY") or "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing — expert unavailable")
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model=model,
            system=system_prompt,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": user_payload}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    except Exception as e:
        logger.exception("expert LLM call failed")
        raise RuntimeError(f"{type(e).__name__}: {str(e)[:200]}")


def _try_parse_json(text: str) -> Dict[str, Any]:
    """Extract a JSON object from expert output (tolerates markdown fences)."""
    txt = (text or "").strip()
    # Strip ```json ... ``` fences if present
    if txt.startswith("```"):
        lines = txt.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        txt = "\n".join(lines)
    try:
        return json.loads(txt)
    except Exception:
        # Find first { ... } block
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(txt[start:end + 1])
            except Exception:
                pass
        return {"raw_text": text}


# ─── Expert 1: Design Expert ──────────────────────────────────────────────────
DESIGN_EXPERT_PROMPT = """أنت **خبير UI/UX سينيور** على مستوى Apple / Stripe / Linear.

مهمتك الوحيدة: تحليل التصميم الحالي واقتراح تحسينات ملموسة وعملية.

⚙️ **قيودك:**
- لا تكتب كود HTML/CSS كامل — فقط توصيات.
- لا تعمل refactor — اقترح تغييرات صغيرة جراحية.
- لا تخمّن — استند فقط على HTML المرفق.
- ركّز على 3-5 تحسينات بأعلى تأثير، مو 20 تحسين.

📐 **معاييرك:**
- التسلسل البصري (Visual Hierarchy)
- الإيقاع المكاني (whitespace, vertical rhythm)
- تباين الألوان (WCAG AA على الأقل)
- اللمسات الفاخرة (micro-interactions, depth, motion)
- التماسك (consistent radii, shadows, font sizes)

📤 **مخرجاتك = JSON فقط** (لا نص حر، لا markdown):
```json
{
  "overall_score": 7.5,
  "strengths": ["نقطة قوة 1", "نقطة قوة 2"],
  "issues": [
    {"severity": "high|medium|low", "where": "Hero section", "problem": "تباين النص ضعيف", "fix": "زيّد opacity النص لـ 0.95 أو غيّر الخلفية لـ #1a1a2e"},
  ],
  "next_action": "اقتراحك الأول للتنفيذ الفوري — جملة واحدة"
}
```

ممنوع المجاملة. ممنوع الردود الفضفاضة. كل عيب يحتاج fix محدد قابل للتنفيذ.
"""


async def call_design_expert(task: str, current_html: str = "",
                              context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Audit the current design and return structured recommendations.

    Uses Sonnet (the smarter model) because UI/UX critique requires nuanced reasoning.
    """
    payload_parts = [f"**المهمة من المهندس الرئيسي:**\n{task}"]
    if current_html:
        snippet = current_html[:18000]  # cap to avoid token bloat
        payload_parts.append(f"\n**HTML الحالي (مقتطف):**\n```html\n{snippet}\n```")
    if context:
        payload_parts.append(f"\n**سياق إضافي:**\n```json\n{json.dumps(context, ensure_ascii=False, indent=2)[:2000]}\n```")
    try:
        # Sonnet for nuanced visual critique
        raw = await _ask_expert(DESIGN_EXPERT_PROMPT, "\n".join(payload_parts),
                                  model="claude-sonnet-4-5-20250929", max_tokens=2500)
        report = _try_parse_json(raw)
        return {"ok": True, "expert": "design", "report": report}
    except Exception as e:
        return {"ok": False, "expert": "design", "error": str(e)}


# ─── Expert 2: Testing Expert ────────────────────────────────────────────────
TESTING_EXPERT_PROMPT = """أنت **خبير QA + Test Engineer**.

مهمتك الوحيدة: استخراج حالات اختبار من ميزة/كود يعطيك المهندس الرئيسي.

⚙️ **قيودك:**
- لا تنفّذ اختبارات — فقط اكتب خطة اختبار.
- ركّز على السيناريوهات الحقيقية اللي ممكن المستخدم يستخدم فيها الميزة (مو edge cases افتراضية).
- 5-10 حالات اختبار كحد أقصى — الجودة قبل الكمية.

📤 **مخرجاتك = JSON فقط**:
```json
{
  "feature_summary": "ملخص جملة واحدة لما تختبره",
  "test_cases": [
    {
      "id": "T1",
      "priority": "P0|P1|P2",
      "name": "اسم وصفي للاختبار",
      "given": "الحالة الابتدائية",
      "when": "ماذا يفعل المستخدم",
      "then": "النتيجة المتوقعة",
      "how_to_verify": "خطوة تأكد ملموسة (curl / click / screenshot)"
    }
  ],
  "risks": ["مخاطر يجب الانتباه لها"],
  "next_action": "اقتراحك للمهندس الرئيسي بأي test يجرّبه أولاً"
}
```

كل اختبار لازم يكون **قابل للتنفيذ يدوياً في أقل من دقيقة**.
"""


async def call_testing_expert(feature: str, code_snippet: str = "",
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate a focused test plan for a feature.

    Uses Haiku (18x cheaper) — test planning is structured/templated and doesn't
    need Sonnet's deep reasoning. Cuts cost from ~$0.05 to ~$0.003 per call.
    """
    parts = [f"**الميزة المطلوب اختبارها:**\n{feature}"]
    if code_snippet:
        parts.append(f"\n**الكود ذو الصلة:**\n```\n{code_snippet[:8000]}\n```")
    if context:
        parts.append(f"\n**سياق:**\n{json.dumps(context, ensure_ascii=False)[:1500]}")
    try:
        raw = await _ask_expert(TESTING_EXPERT_PROMPT, "\n".join(parts),
                                  model="claude-haiku-4-5-20251001", max_tokens=2000)
        return {"ok": True, "expert": "testing", "report": _try_parse_json(raw)}
    except Exception as e:
        return {"ok": False, "expert": "testing", "error": str(e)}


# ─── Expert 3: Troubleshoot Expert ───────────────────────────────────────────
TROUBLESHOOT_EXPERT_PROMPT = """أنت **خبير Root Cause Analysis (RCA)** — تشخيص فقط، لا إصلاح.

مهمتك الوحيدة: تحليل خطأ أو سلوك غير متوقع وإعطاء أعلى احتمال للسبب الجذري.

⚙️ **قيودك:**
- read-only — لا تقترح كتابة كود مباشر.
- اقترح أعلى 3 أسباب احتمالاً مرتبة بالاحتمالية.
- اقترح خطوة تشخيصية واحدة فقط للمهندس الرئيسي ينفّذها للتأكد.
- لا تخمّن بدون منطق. لو ما عندك بيانات كافية → قل بصراحة "أحتاج logs / steps to reproduce".

📤 **مخرجاتك = JSON فقط**:
```json
{
  "issue_summary": "ملخص جملة واحدة للمشكلة",
  "evidence_gathered": ["نقاط من الأدلة المرفقة"],
  "likely_causes": [
    {"rank": 1, "cause": "السبب الأرجح", "confidence": 0.7, "why": "لأن...", "verify_with": "ينفّذ المهندس X ليتأكد"},
    {"rank": 2, "cause": "السبب الثاني", "confidence": 0.2, "why": "..."},
    {"rank": 3, "cause": "السبب الثالث", "confidence": 0.1, "why": "..."}
  ],
  "missing_info": ["ما يحتاج المهندس يجمعه قبل الإصلاح"],
  "next_action": "خطوة واحدة محددة جداً (5 كلمات أو أقل)"
}
```

ممنوع الإصلاح المباشر. أنت تشخيص فقط.
"""


async def call_troubleshoot_expert(issue: str, error_logs: str = "",
                                     recent_actions: str = "",
                                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Read-only RCA on a reported issue.

    Uses Haiku — diagnostic reasoning over logs is well-suited for the faster model.
    """
    parts = [f"**المشكلة المبلَّغة:**\n{issue}"]
    if error_logs:
        parts.append(f"\n**Logs / Error messages:**\n```\n{error_logs[:6000]}\n```")
    if recent_actions:
        parts.append(f"\n**آخر إجراءات قبل المشكلة:**\n{recent_actions[:1500]}")
    if context:
        parts.append(f"\n**سياق:**\n{json.dumps(context, ensure_ascii=False)[:1500]}")
    try:
        raw = await _ask_expert(TROUBLESHOOT_EXPERT_PROMPT, "\n".join(parts),
                                  model="claude-haiku-4-5-20251001", max_tokens=2000)
        return {"ok": True, "expert": "troubleshoot", "report": _try_parse_json(raw)}
    except Exception as e:
        return {"ok": False, "expert": "troubleshoot", "error": str(e)}


# ─── Expert 4: Integration Expert ────────────────────────────────────────────
INTEGRATION_EXPERT_PROMPT = """أنت **خبير 3rd Party Integration Playbooks**.

مهمتك الوحيدة: لما المهندس الرئيسي يحتاج يربط خدمة خارجية (Stripe, OpenAI, Twilio, إلخ)، تعطيه خطة ربط دقيقة.

⚙️ **قيودك:**
- لا تكتب كود كامل — فقط خطوات واضحة + snippets قصيرة.
- لا تخترع endpoints / parameters — لو غير متأكد، قل "تحقق من docs الرسمية".
- استخدم آخر إصدار من SDK المعروف (مثلاً openai v1.x وليس v0.x).
- كل integration: مفاتيح مطلوبة + خطوات تركيب + 5-10 أسطر كود مثال.

📤 **مخرجاتك = JSON فقط**:
```json
{
  "service": "اسم الخدمة",
  "use_case": "ليش يحتاجها العميل",
  "required_keys": [
    {"name": "STRIPE_SECRET_KEY", "where_to_get": "dashboard.stripe.com/apikeys", "type": "secret|public", "tier": "free|paid"}
  ],
  "install_steps": ["pip install stripe", "إضف المفتاح في .env"],
  "code_example": "snippet بسيط < 15 سطر",
  "common_pitfalls": ["خطأ شائع 1", "خطأ شائع 2"],
  "alternatives": [{"name": "بديل أرخص أو أسهل", "tradeoff": "وش فرقه"}],
  "next_action": "اقتراحك الأول للمهندس الرئيسي"
}
```

دقّة > سرعة. لو الـ API تغيّر مؤخراً، قل "أنصح بالتحقق من docs قبل التنفيذ".
"""


async def call_integration_expert(service: str, use_case: str = "",
                                    context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get a focused integration playbook for a 3rd-party service.

    Uses Haiku — integration playbooks are largely lookup/templating; saves cost.
    """
    parts = [f"**الخدمة المطلوب ربطها:** {service}"]
    if use_case:
        parts.append(f"\n**حالة الاستخدام:** {use_case}")
    if context:
        parts.append(f"\n**سياق:**\n{json.dumps(context, ensure_ascii=False)[:1500]}")
    try:
        raw = await _ask_expert(INTEGRATION_EXPERT_PROMPT, "\n".join(parts),
                                  model="claude-haiku-4-5-20251001", max_tokens=2200)
        return {"ok": True, "expert": "integration", "report": _try_parse_json(raw)}
    except Exception as e:
        return {"ok": False, "expert": "integration", "error": str(e)}


# ─── Tool schemas for registering with the main agent ────────────────────────
EXPERT_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "ask_design_expert",
        "description": (
            "🎨 استدعِ خبير UI/UX لمراجعة التصميم الحالي وإعطاء توصيات محددة. "
            "استخدمه لما العميل يقول 'التصميم ما عجبني' أو لما تشك في جودة التصميم. "
            "يرجع JSON منظم بأعلى 3-5 تحسينات بأعلى تأثير. **لا يكتب كود**، فقط يقترح."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "ماذا تبي الخبير يحلل (مثلاً: 'راجع الـ Hero')"},
                "context": {"type": "object", "description": "سياق اختياري (الجمهور، الـ brand، إلخ)"}
            },
            "required": ["task"],
        },
    },
    {
        "name": "ask_testing_expert",
        "description": (
            "🧪 استدعِ خبير QA لتوليد خطة اختبار لميزة. استخدمه بعد ما تكمل ميزة كبيرة "
            "(login, checkout, تكامل API) للتأكد من تغطية السيناريوهات الحقيقية. "
            "يرجع JSON فيه 5-10 حالات اختبار قابلة للتنفيذ."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature": {"type": "string", "description": "وصف الميزة المطلوب اختبارها"},
                "code_snippet": {"type": "string", "description": "الكود ذو الصلة (اختياري)"},
                "context": {"type": "object"},
            },
            "required": ["feature"],
        },
    },
    {
        "name": "ask_troubleshoot_expert",
        "description": (
            "🔍 استدعِ خبير Root Cause Analysis لتشخيص bug أو سلوك غير متوقع. "
            "read-only — يرجع أعلى 3 أسباب محتملة مرتبة بالاحتمالية + خطوة تشخيص واحدة. "
            "استخدمه لما تعلق في مشكلة بعد محاولتين فاشلتين."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "issue": {"type": "string", "description": "وصف المشكلة بكلمات العميل"},
                "error_logs": {"type": "string", "description": "logs أو error messages (اختياري)"},
                "recent_actions": {"type": "string", "description": "آخر اللي حصل قبل المشكلة"},
                "context": {"type": "object"},
            },
            "required": ["issue"],
        },
    },
    {
        "name": "ask_integration_expert",
        "description": (
            "🔌 استدعِ خبير Integration لما تحتاج تربط خدمة خارجية (Stripe, Twilio, OpenAI, إلخ). "
            "يرجع playbook منظم: المفاتيح المطلوبة + خطوات + snippet كود مثال + أخطاء شائعة. "
            "**استخدمه قبل ما تبدأ تكتب integration code من ذاكرتك** — يضمن دقة آخر إصدار من SDK."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "اسم الخدمة (Stripe / OpenAI / Twilio…)"},
                "use_case": {"type": "string", "description": "ليش يحتاجها العميل"},
                "context": {"type": "object"},
            },
            "required": ["service"],
        },
    },
]

EXPERT_TOOL_NAMES = {t["name"] for t in EXPERT_TOOL_SCHEMAS}


# ─── Dispatch helper ─────────────────────────────────────────────────────────
async def dispatch_expert(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Route an expert tool call to the right function."""
    args = args or {}
    if name == "ask_design_expert":
        return await call_design_expert(args.get("task", ""),
                                          current_html=args.get("current_html", ""),
                                          context=args.get("context"))
    if name == "ask_testing_expert":
        return await call_testing_expert(args.get("feature", ""),
                                           code_snippet=args.get("code_snippet", ""),
                                           context=args.get("context"))
    if name == "ask_troubleshoot_expert":
        return await call_troubleshoot_expert(args.get("issue", ""),
                                                error_logs=args.get("error_logs", ""),
                                                recent_actions=args.get("recent_actions", ""),
                                                context=args.get("context"))
    if name == "ask_integration_expert":
        return await call_integration_expert(args.get("service", ""),
                                               use_case=args.get("use_case", ""),
                                               context=args.get("context"))
    return {"ok": False, "error": f"unknown expert: {name}"}
