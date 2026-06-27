"""
🧠 Capabilities Addendum — system-prompt block that teaches the AI about all
24 new cortices + 6 executors + 9 integrations.

This is injected into AGENT_SYSTEM_PROMPT so the AI KNOWS what tools exist
and WHEN to call each one.
"""
from __future__ import annotations


def render_full_capabilities_catalog(max_chars: int = 6000) -> str:
    """Build the catalog block. Called once per chat-turn at prompt-build time."""
    try:
        from .creative_recipes import render_recipes_atlas
        from .shaders_library import render_shader_catalog
        from .backend_patterns import render_patterns_catalog
        from .library_registry import library_summary_for_prompt
    except Exception:
        return ""

    blocks = []
    blocks.append("# 📚 CAPABILITIES ATLAS — استخدم هذه الأدوات بحكمة")
    blocks.append("")
    blocks.append("## 🎨 1. CREATIVE RECIPES (30 وصفة جاهزة)")
    blocks.append("لما العميل يطلب موقع/تطبيق من نوع معروف، استدعي tool `inject_recipe` بـ recipe_id من القائمة:")
    try:
        blocks.append(render_recipes_atlas(max_chars=1400))
    except Exception:
        pass
    blocks.append("")
    blocks.append("## 🌌 2. SHADERS & POST-FX (29 effect)")
    blocks.append("لما تحتاج تأثير بصري (neon, glitch, scanlines, nebula, matrix_rain...) استدعي `apply_shader`:")
    try:
        blocks.append(render_shader_catalog(max_chars=1000))
    except Exception:
        pass
    blocks.append("")
    blocks.append("## 🗄️ 3. BACKEND PATTERNS (16 نمط جاهز)")
    blocks.append("لـ JWT/WebSocket/Stripe/ARQ jobs/Redis/Twilio/Resend... استدعي `inject_backend_pattern`:")
    try:
        blocks.append(render_patterns_catalog(max_chars=900))
    except Exception:
        pass
    blocks.append("")
    blocks.append("## 🏛️ 4. ARCHITECT CORTEX")
    blocks.append("لطلبات معقدة (SaaS, dashboard, auth, DB) — استدعي `run_architect` أولاً لينتج Mermaid + ADR.")
    blocks.append("")
    blocks.append("## 🔍 5. REVIEWER CORTEX")
    blocks.append("قبل تسلّم كود نهائي — استدعي `run_reviewer` لفحص XSS/perf/a11y/SEO.")
    blocks.append("")
    blocks.append("## 🧬 6. BRAND DNA EXTRACTOR")
    blocks.append("من أول رسالة عميل، استدعي `extract_brand_dna` لاستخراج palette+tone+voice+glossary.")
    blocks.append("سيُحفظ في memory تلقائياً.")
    blocks.append("")
    blocks.append("## 📲 7. MOBILE BUILD (Capacitor + EAS)")
    blocks.append("لطلب تطبيق موبايل — Concierge يطلب EAS_ACCESS_TOKEN تلقائياً.")
    blocks.append("بعد التحقق، استدعي `trigger_eas_build` لبدء البناء السحابي.")
    blocks.append("")
    blocks.append("## 👥 8. REAL-TIME COLLAB (Liveblocks)")
    blocks.append("لطلب live cursors/presence/comments — استدعي `inject_liveblocks` (يولّد auth + components).")
    blocks.append("")
    blocks.append("## 🌐 9. BROWSER CODE EXECUTION (WebContainer + Pyodide)")
    blocks.append("لاختبار كود Node.js — استدعي `run_in_webcontainer`. لـ Python — `run_in_pyodide`.")
    blocks.append("الكود يشتغل في متصفح العميل، صفر setup.")
    blocks.append("")
    blocks.append("## 🛠️ 10. SELF-HEALING SANDBOX (سريع، يشتغل على الخادم)")
    blocks.append("- `run_js_sandbox` / `run_python_sandbox` — تنفيذ snippet خفيف (~5s) قبل ما تحقنه.")
    blocks.append("- `validate_html_sandbox` — فحص HTML سريع بدون متصفح.")
    blocks.append("- `autofix_code_loop` — حلقة self-healing: شغّل → لو فشل → أصلح بـ LLM → كرر (3 محاولات).")
    blocks.append("استخدم هذه قبل ما تسلّم كود حساس (regex/parser/util).")
    blocks.append("")
    blocks.append("## 🚀 11. SaaS/MOBILE/STATE/SEARCH (محرّكات متخصّصة)")
    blocks.append("- `generate_nextjs_project` — Next.js 15 + App Router + TS + Tailwind scaffold.")
    blocks.append("- `build_capacitor_app` — تحويل web app لـ Android/iOS عبر Capacitor.")
    blocks.append("- `recommend_state_management` — Redux/Zustand/TanStack pick + snippet.")
    blocks.append("- `search_past_projects` — RAG على مشاريع المستخدم السابقة.")
    blocks.append("- `run_in_e2b_sandbox` — Linux VM كامل (يحتاج E2B_API_KEY).")
    blocks.append("- `deploy_via_ssh` — نشر على VPS العميل (يحتاج SSH creds).")
    blocks.append("")
    blocks.append("## 🔧 12. UTILITY CORTICES")
    blocks.append("- `convert_to_typescript` — JS→TS مع types")
    blocks.append("- `refactor_rename` — إعادة تسمية عبر ملفات متعددة")
    blocks.append("- `audit_a11y` — WCAG 2.1 AA audit + auto-fix")
    blocks.append("- `audit_seo` — schema.org + meta + sitemap audit")
    blocks.append("- `optimize_performance` — lazy load + defer + score")
    blocks.append("- `inject_pwa` — manifest + service worker + offline")
    blocks.append("- `setup_i18n` — multi-language + RTL/LTR auto")
    blocks.append("- `design_database` — Mongo/Postgres schema + ERD")
    blocks.append("")
    blocks.append("## ⚠️ القواعد الذهبية")
    blocks.append("1. لمشاريع معقدة: ابدأ بـ `run_architect` قبل أي كود.")
    blocks.append("2. لكل مشروع جديد: استخرج `extract_brand_dna` أول مرة.")
    blocks.append("3. لما recipe يطابق طلب العميل: استخدم `inject_recipe` بدل ما تبني من الصفر.")
    blocks.append("4. قبل أي تسليم نهائي: شغّل `run_reviewer`. لو وجد critical/high — أصلح ثم سلّم.")
    blocks.append("5. لطلبات تتطلب 3rd-party (mobile/realtime/payments) — Concierge يطلب المفاتيح تلقائياً، انتظره.")
    out = "\n".join(blocks)
    return out[:max_chars]


def get_capabilities_addendum() -> str:
    """Cached entry-point for the system prompt."""
    return render_full_capabilities_catalog()
