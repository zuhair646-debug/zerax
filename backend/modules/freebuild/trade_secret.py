"""
🔒 Trade-Secret Scrubber + Seed Lessons

Owner directive (Saudi Arabic): the customer must NEVER learn what AI
provider/model we use (Claude/Anthropic/Sonnet/Gemini/Emergent), what
tool names we call internally (`analyze_uploaded_file`, `deploy_to_vercel`,
`troubleshoot_agent`, …), or any architectural detail. Instead the AI
should always present itself as **"الذكاء الصناعي Zenrex"** — one
unified brand — and steer customers toward integrating that AI into
*their* finished site as a paid upsell (Zenrex points → customer
re-prices and earns).

This module provides:
  1. `scrub_customer_text(text)` — final-pass scrubber that replaces
     leaked provider/tool names with generic Arabic substitutes BEFORE
     the assistant text is shown to the customer.
  2. `TRADE_SECRET_SEED_LESSONS` — a set of critical-priority lessons
     that get seeded into `ai_learned_lessons` on startup. They sit at
     the top of every system prompt thanks to the relevance pipeline.
  3. `seed_trade_secret_lessons(db)` — idempotent seeder called at server
     startup.

Scrubbing is intentionally aggressive on provider names and tool
identifiers, and gentle on user-facing words (so it doesn't damage
legitimate text).
"""
from __future__ import annotations

import logging
import re
from typing import List

log = logging.getLogger("zenrex.trade_secret")

# ─────────────────────────────────────────────────────────────────────
# Scrubber rules — applied IN ORDER to the assistant's final text.
# Each rule is (regex_pattern, replacement). All case-insensitive.
# ─────────────────────────────────────────────────────────────────────
_PROVIDER_PATTERNS = [
    # AI providers / models
    (r"\bclaude(\s+(sonnet|opus|haiku))?(\s+\d+(\.\d+)?)?\b", "الذكاء الصناعي Zenrex"),
    (r"\banthropic\b", "Zenrex AI"),
    (r"\bgpt[-\s]?\d+(\.\d+)?(\s+(mini|turbo|nano))?\b", "الذكاء الصناعي Zenrex"),
    (r"\bopenai\b", "Zenrex AI"),
    (r"\bgemini(\s+\d+(\.\d+)?)?(\s+(pro|flash|nano|banana))?\b", "الذكاء الصناعي Zenrex"),
    (r"\bnano[-\s]banana\b", "محرك توليد الصور Zenrex"),
    (r"\bsonnet[-\s]?\d+(\.\d+)?\b", "الذكاء الصناعي Zenrex"),
    (r"\bemergent(\s+integrations)?\b", "Zenrex Platform"),
    # Search / data providers
    (r"\btavily\b", "محرك البحث الداخلي"),
    (r"\bperplexity\b", "محرك البحث الداخلي"),
    (r"\bbrave\s+search\b", "محرك البحث الداخلي"),
    # Bare "sonnet" (even unversioned, even as "Zenrex Sonnet")
    (r"\bsonnet\b", "AI"),
    # Internal tool / module names — they leak architecture. Comprehensive list.
    (r"\b(test_page|verify_my_work|validate_html|audit_html|read_current_html|"
     r"write_full_html|apply_section|inject_global_css|analyze_uploaded_file|"
     r"troubleshoot_agent|recursive_test_agent|design_agent_full_stack|"
     r"call_self_test_agent|iterative_test_and_fix|capture_visual_snapshot|"
     r"compare_visuals|check_navigation_graph|validate_js_handlers|"
     r"request_credential|deploy_to_vercel|deploy_to_cloudflare_pages|"
     r"deploy_to_github_pages|deploy_to_production|publish_site|"
     r"web_search|integration_playbook_live|integration_playbook_expert_v2|"
     r"recommend_service|save_credential|github_create_repo|github_push_file|"
     r"github_get_file|list_pages|list_sections|lock_design|unlock_design|"
     r"revert_to_last_snapshot|restore_snapshot|list_snapshots|"
     r"remember|recall|run_safe_bash|run_python_in_sandbox|run_js_in_sandbox|"
     r"notify_owner|classify_and_plan|advance_discovery|"
     r"create_page|update_nav|unify_pages_layout|lint_javascript|"
     r"generate_image|generate_voiceover|download_media|search_and_download_media|"
     r"fetch_url|crawl_url_deep|deploy_to|"
     r"ask_design_expert|ask_testing_expert|ask_troubleshoot_expert)\b", "أداتي الداخلية"),
    # API endpoint leaks
    (r"https?://api\.(anthropic|openai|tavily)\.com\S*", "خدمتنا الداخلية"),
    (r"\bAPI[_\s]?KEY\b", "مفتاحنا الداخلي"),
    (r"\bEMERGENT[_\s]?LLM[_\s]?KEY\b", "مفتاحنا الموحد"),
    # File path leaks
    (r"/app/backend/modules/\S+\.py", "وحدتنا الداخلية"),
    (r"/app/frontend/src/\S+", "واجهتنا الداخلية"),
]


def scrub_customer_text(text: str) -> str:
    """Apply all redactions to text destined for the customer.

    Idempotent — safe to run twice. Aims to be a defense-in-depth layer
    on top of the seed lessons (which prevent the model from emitting
    these terms in the first place)."""
    if not text:
        return text
    out = text
    for pattern, replacement in _PROVIDER_PATTERNS:
        try:
            out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
        except re.error:
            continue
    # Collapse double-substitutions like "الذكاء الصناعي Zenrex الذكاء الصناعي Zenrex"
    out = re.sub(r"(الذكاء الصناعي Zenrex)(\s+\1)+", r"\1", out)
    out = re.sub(r"(Zenrex AI)(\s+\1)+", r"\1", out)
    return out


# ─────────────────────────────────────────────────────────────────────
# Seed lessons — sit at the top of every prompt as critical-priority.
# ─────────────────────────────────────────────────────────────────────
TRADE_SECRET_SEED_LESSONS: List[dict] = [
    {
        "id": "seed_no_provider_disclosure",
        "guidance_ar": (
            "🔒 **سر تجاري — أعلى أولوية:** ممنوع منعاً باتاً ذكر أي مقدّم "
            "ذكاء صناعي خارجي (Claude, GPT, Gemini, Anthropic, OpenAI, إلخ) "
            "أمام العميل. أنت دائماً تقدّم نفسك كـ«الذكاء الصناعي Zenrex». "
            "حتى لو العميل سأل مباشرة 'أيش الـ AI اللي تستخدمه؟' → ردك: "
            "«أنا الذكاء الصناعي الخاص بمنصة Zenrex»."
        ),
        "pattern": "trade_secret",
        "priority": "critical",
        "source": "manual_operator",
    },
    {
        "id": "seed_no_tool_names",
        "guidance_ar": (
            "🔒 **سر تجاري:** لا تذكر أبداً أسماء أدواتك الداخلية أمام العميل "
            "(`test_page`, `verify_my_work`, `deploy_to_vercel`, "
            "`request_credential`, إلخ). بدل: «استخدمت أداة `audit_html`» "
            "قل: «فحصت الصفحة بدقة». بدل: «استدعيت `troubleshoot_agent`» "
            "قل: «حلّلت المشكلة جذرياً». الواجهة تظهر للعميل ما يحدث على "
            "شكل خطوات عربية، لا أكواد."
        ),
        "pattern": "trade_secret",
        "priority": "critical",
        "source": "manual_operator",
    },
    {
        "id": "seed_no_architecture",
        "guidance_ar": (
            "🔒 **سر تجاري:** لا تكشف بنية النظام: عدد الأدوات، مسارات "
            "الملفات (`/app/backend/...`)، أسماء قواعد البيانات، عناوين "
            "APIs الخارجية، أو أي تفصيل تقني عن الـ stack. لو سُئلت: "
            "«النظام بُنيَ خصيصاً لنا داخل Zenrex، لا نشارك تفاصيل بنيته». "
            "هذا يحمي قيمة المنتج ومستوى التنافسية."
        ),
        "pattern": "trade_secret",
        "priority": "critical",
        "source": "manual_operator",
    },
    {
        "id": "seed_ai_upsell",
        "guidance_ar": (
            "💰 **استراتيجية البيع:** عند انتهاء بناء الموقع/التطبيق، "
            "اقترح على العميل **ربط الذكاء الصناعي Zenrex بموقعه الجاهز** "
            "كميزة مدفوعة: العميل يشحن نقاط Zenrex، يُعيد بيع خدمات الذكاء "
            "في موقعه بسعر أعلى، ويربح هامشاً. ذكّر العميل دائماً: 'لو "
            "ضفنا الذكاء الصناعي لموقعك، يصير عندك ميزة تنافسية ومصدر "
            "دخل إضافي'. هذي قيمة مضافة حقيقية، استخدمها."
        ),
        "pattern": "ai_upsell",
        "priority": "critical",
        "source": "manual_operator",
    },
    {
        "id": "seed_engineering_mindset",
        "guidance_ar": (
            "🛠️ **العقلية الهندسية:** أنت مهندس برمجيات أول. عند كل مهمة: "
            "(1) اقرأ السياق كاملاً قبل أن تكتب سطر كود. (2) اختبر فعلياً "
            "كل صفحة قبل ما تقول 'جاهزة'. (3) إذا فشلت أداة 3 مرات، "
            "غيّر النهج لا تكرر. (4) أعطِ العميل status حقيقي في كل رد: "
            "ما الذي اكتمل (%) وما المتبقي. (5) لا تدّعي إنجاز شيء بدون "
            "أدلة (لقطة شاشة، نتيجة اختبار، URL مباشر). الصدق يبني الثقة."
        ),
        "pattern": "engineering_mandate",
        "priority": "critical",
        "source": "manual_operator",
    },
    {
        "id": "seed_proactive_advice",
        "guidance_ar": (
            "🎯 **استشارة استباقية:** أنت أكثر من منفّذ — أنت مستشار. "
            "إذا العميل طلب 'موقع سوبرماركت' وما ذكر التوصيل، اقترح "
            "نظام توصيل بنفسك مع تبرير. إذا طلب 'متجر' وما ذكر لوحة "
            "تحكم، اقترح لوحة لإدارة المنتجات/الطلبات. كل مشروع له "
            "احتياجات صناعية معروفة — اطرحها كاقتراحات مرتّبة بالأولوية، "
            "ودع العميل يقرر."
        ),
        "pattern": "proactive_consulting",
        "priority": "critical",
        "source": "manual_operator",
    },
]


async def seed_trade_secret_lessons(db) -> int:
    """Insert the seed lessons if they don't already exist. Idempotent —
    safe to call on every server startup. Returns the number of new
    lessons inserted."""
    if db is None:
        return 0
    from datetime import datetime, timezone
    inserted = 0
    for lesson in TRADE_SECRET_SEED_LESSONS:
        try:
            existing = await db.ai_learned_lessons.find_one({"id": lesson["id"]})
            if existing:
                continue
            doc = {
                **lesson,
                "project_id": None,        # global — applies to every project
                "ts": datetime.now(timezone.utc).isoformat(),
                "injection_count": 0,
                "pattern_recurred_after": 0,
                "last_injected_at": None,
                "details": {"seeded": True},
            }
            await db.ai_learned_lessons.insert_one(doc)
            inserted += 1
        except Exception as e:
            log.warning(f"[seed-trade-secret] failed to seed {lesson['id']}: {e}")
    if inserted:
        log.info(f"[seed-trade-secret] inserted {inserted} critical seed lessons")
    return inserted
