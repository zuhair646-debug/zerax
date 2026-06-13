"""
FreeBuild Tool-Using Agent
═══════════════════════════════════════════════════════════════════════════════
Same architecture as the platform agent (Claude). The AI gets real tools it
can call iteratively, sees actual state, fixes its own mistakes, and only
stops when the site is verified working.

Tools exposed to Claude:
  • read_current_html()         — get current_html bytes + structure summary
  • list_sections()             — list all <section id> + content sizes
  • write_full_html(html)       — replace current_html (with drift safety)
  • apply_section(id, html, op) — surgical append/replace of a section
  • update_nav(items)           — rewrite the <nav> link list
  • validate_html()             — run comprehensive validation, return issues
  • search_html(pattern)        — regex search within current_html
  • finish(summary)             — end the agent loop and reply to user
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)

# Reuse helpers from the main chat module
from .freebuild_chat import (
    _comprehensive_validation,
    _design_signature,
    _extract_html,
    _fix_dead_navigation_links,
    _merge_sections,
    _summarize_html,
    _verify_anchor_links,
    _enc,
    _dec,
    _mask,
)
from .advanced_tools import (
    ADVANCED_TOOL_SCHEMAS,
    ADVANCED_TOOL_LABELS_AR,
    ADVANCED_TOOL_NAMES,
    dispatch_advanced,
)
from .workflow_tools import (
    WORKFLOW_TOOL_SCHEMAS,
    WORKFLOW_TOOL_LABELS_AR,
    WORKFLOW_TOOL_NAMES,
    dispatch_workflow,
)
from .memory_audit_tools import (
    PHASE4_TOOL_SCHEMAS,
    PHASE4_TOOL_LABELS_AR,
    PHASE4_TOOL_NAMES,
    dispatch_phase4,
    load_project_memories_for_prompt,
)
from .browser_use_tools import (
    PHASE5_TOOL_SCHEMAS,
    PHASE5_TOOL_LABELS_AR,
    PHASE5_TOOL_NAMES,
    dispatch_browser,
)
from .desktop_agent_tools import (
    DESKTOP_TOOL_SCHEMAS,
    DESKTOP_TOOL_LABELS_AR,
    DESKTOP_TOOL_NAMES,
    dispatch_desktop,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Tool Schemas (Anthropic format) ──────────────────────────────────────────
TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "name": "read_current_html",
        "description": (
            "Read the saved current_html for this project. Returns a structural "
            "summary (size, title, section ids with content sizes, broken anchors). "
            "Use this FIRST to know the actual state before making any change."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_sections",
        "description": (
            "List every <section id> in current_html with its content size and "
            "preview snippet. Useful before deciding where to append/replace."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "validate_html",
        "description": (
            "Run comprehensive validation on current_html. Returns issues with "
            "severity, code, message, and a fix hint. Call this AFTER any change "
            "to confirm the site is clean."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "write_full_html",
        "description": (
            "Replace current_html entirely. ONLY use this for the very first "
            "build (empty project) or when the user explicitly requested a "
            "complete redesign. For everything else, prefer apply_section."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "html": {"type": "string", "description": "Full <!DOCTYPE html>...</html> document."},
            },
            "required": ["html"],
        },
    },
    {
        "name": "apply_section",
        "description": (
            "Surgically apply a section to current_html. Set op='append' to add "
            "a new section before </body>, or op='replace' to overwrite an "
            "existing <section id='X'>. Preserves everything else."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "section id (e.g. 'quran')"},
                "html": {"type": "string", "description": "<section id='X'>...</section> fragment"},
                "op": {"type": "string", "enum": ["append", "replace"]},
            },
            "required": ["id", "html", "op"],
        },
    },
    {
        "name": "update_nav",
        "description": (
            "Replace the <nav> link list. Provide an array of items, each with "
            "an anchor target and a label."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                        },
                        "required": ["id", "label"],
                    },
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "search_html",
        "description": (
            "Regex search inside current_html. Returns up to 10 matches with "
            "surrounding context. Useful for finding a specific component "
            "before editing it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the LIVE web for ANY topic — current best practices, design inspiration, "
            "library docs, color palettes, font pairings, real business data, news, prices, "
            "Saudi market trends, etc. Use this WHENEVER you feel uncertain or need fresh data. "
            "NEVER say 'I don't know' — ALWAYS search first. Returns titles + URLs + snippets."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query in Arabic or English."},
                "max_results": {"type": "integer", "default": 5, "description": "1-10 results"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": (
            "Fetch the raw HTML/text content of any public URL. Use this to inspect "
            "competitor sites for inspiration, pull real data, verify a link works, or "
            "scrape content the user references. Returns up to 50KB of cleaned text."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL including https://"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "generate_image",
        "description": (
            "Generate a REAL AI image via Gemini Nano Banana (NOT a stock photo URL — "
            "a freshly generated PNG). Use this when the user wants a hero image, logo "
            "concept, product mockup, or any visual that doesn't exist on Unsplash. "
            "Returns a permanent URL like /api/freebuild/v2/img/{hash}.png that you "
            "can drop into <img src=> directly."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "English prompt describing the desired image, e.g. 'modern coffee shop interior at sunset, warm tones, cinematic'."},
                "width": {"type": "integer", "default": 1024},
                "height": {"type": "integer", "default": 1024},
            },
            "required": ["description"],
        },
    },
    {
        "name": "lint_javascript",
        "description": (
            "Run a JavaScript syntax + common-bug check on a code snippet OR the inline "
            "<script> blocks of current_html. Detects undefined variables, unclosed brackets, "
            "missing semicolons in tricky spots, and broken event handlers. Call this AFTER "
            "writing any non-trivial JS to catch errors BEFORE the user sees them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "JS code to lint. Pass empty string to lint all inline <script> in current_html."},
            },
            "required": [],
        },
    },
    {
        "name": "list_voices",
        "description": (
            "🎙️ اجلب قائمة الأصوات المتاحة من ElevenLabs مع عينات MP3. "
            "استخدمها لما العميل يبي يختار صوت — راح ترجع لك قائمة بأسماء الأصوات، اللغات، "
            "الأعمار، اللهجات، ورابط MP3 sample لكل صوت. اعرضها للعميل بترتيب جميل في "
            "قسم HTML مع مشغّل صوت لكل sample."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "language": {"type": "string", "description": "فلتر اللغة (مثل 'ar', 'en'). فاضي = كل اللغات."},
                "limit": {"type": "integer", "default": 20, "description": "عدد الأصوات (1-50)"},
            },
            "required": [],
        },
    },
    {
        "name": "generate_voiceover",
        "description": (
            "🗣️ ولّد تعليق صوتي MP3 بـ ElevenLabs من نص. النتيجة: ملف MP3 دائم تقدر "
            "تضمنه في الفيديو أو الموقع بـ <audio src='URL'>. مثالي لـ: سرد الفيلم، "
            "تعليق التيكتوك، الـ podcast، الأدلة الصوتية، إلخ."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "النص المراد تحويله لصوت (عربي/إنجليزي/أي لغة)."},
                "voice_id": {"type": "string", "description": "معرّف الصوت من list_voices. لو فاضي → افتراضي (Rachel)."},
                "model": {"type": "string", "default": "eleven_multilingual_v2", "description": "eleven_multilingual_v2 (دعم 32 لغة) أو eleven_v3 (عواطف عميقة)"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "write_script",
        "description": (
            "📝 اكتب سيناريو سينمائي منظم بصيغة Hollywood: Logline → Treatment → "
            "Shot list مفصّل. النتيجة محفوظة كـ HTML section في الموقع، تقدر تعدّلها "
            "تدريجياً بـ apply_section. استخدمها قبل أي توليد فيديو."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "عنوان الفيلم/الحلقة"},
                "genre": {"type": "string", "description": "النوع: دراما/كوميديا/أكشن/توعوي/إعلان/إلخ"},
                "duration_seconds": {"type": "integer", "description": "المدة بالثواني (مثلاً 60 لإعلان، 300 لمشهد قصير)"},
                "logline": {"type": "string", "description": "الفكرة في جملة واحدة"},
                "synopsis": {"type": "string", "description": "ملخص قصير 2-4 أسطر"},
            },
            "required": ["title", "logline"],
        },
    },
    {
        "name": "generate_storyboard",
        "description": (
            "🎭 ولّد ستوري بورد سينمائي لمشاهد الفيلم. لكل مشهد → keyframe احترافي "
            "بـ Gemini Nano Banana (style: cinematic, 16:9 aspect ratio). النتيجة: صور "
            "URLs جاهزة للاستخدام في الـ apply_section."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scenes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "قائمة وصف بالإنجليزي لكل مشهد (max 6 مشاهد). مثال: ['wide shot of busy Riyadh street at night, neon lights, cinematic', 'close-up of young Saudi entrepreneur at laptop, warm desk lamp']",
                },
                "style": {"type": "string", "default": "cinematic", "description": "نمط الصور: cinematic / anime / documentary / commercial"},
            },
            "required": ["scenes"],
        },
    },
    {
        "name": "update_world_bible",
        "description": (
            "📚 احفظ معلومات السلسلة (الشخصيات، المواقع، الأحداث، قواعد الإخراج) في "
            "ذاكرة دائمة للمشروع. ضرورية لأفلام السلاسل المتعددة الحلقات للمحافظة على "
            "اتساق الشخصيات والأحداث عبر الحلقات."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "characters": {"type": "array", "items": {"type": "object"}, "description": "[{name, description, voice_id, traits}]"},
                "locations": {"type": "array", "items": {"type": "object"}, "description": "[{name, description, era, mood}]"},
                "plot_points": {"type": "array", "items": {"type": "string"}, "description": "أحداث رئيسية بالترتيب الزمني"},
                "style_rules": {"type": "string", "description": "قواعد الإخراج (مثل: 'دائماً golden hour، ألوان دافئة، إيقاع بطيء')"},
            },
            "required": [],
        },
    },
    {
        "name": "test_page",
        "description": (
            "🔬 افتح صفحة في متصفح حقيقي وارجع تقرير عنها: "
            "(1) صورة سكرين شوت تشوف الصفحة بعينك، "
            "(2) عدد عناصر <video> الموجودة، "
            "(3) أخطاء console JavaScript، "
            "(4) حجم الصفحة وعنوانها. "
            "استخدمها بعد ما تنشر الموقع بـ publish_site عشان **تتأكد فعلياً** إن "
            "الفيديوهات تشتغل، الـ JS مو مكسور، والتصميم سليم. **لا تقل أبداً 'ما أقدر أختبر' — استخدم هذي الأداة!**"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL الكامل للصفحة (مثل https://zenrex.ai/s/my-site)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "publish_site",
        "description": (
            "🚀 Publish the current site LIVE on Zenrex platform. After calling this, "
            "the site is instantly accessible at https://zenrex.ai/s/{slug} with free SSL "
            "and global CDN. NO GitHub, NO Vercel, NO Railway needed — Zenrex IS the host. "
            "Use this when the user says 'publish', 'go live', 'release', or 'انشر/أطلق/نزّل'. "
            "Pick a slug that matches the brand (e.g. 'kafe-fajr' for 'كافيه الفجر')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": "URL slug: lowercase, digits, hyphens. 3-60 chars. e.g. 'kafe-fajr', 'noor-electronics'."
                },
            },
            "required": ["slug"],
        },
    },
    {
        "name": "request_credential",
        "description": (
            "🔑 Ask the user for an API key / access token / credential mid-conversation. "
            "Use this WHENEVER you need an external service the user must authorize: YouTube "
            "Data API key, TikTok session, Spotify token, Stripe key, custom webhook URL, etc. "
            "The frontend will pop a secure modal asking the user to paste the value. "
            "The value is encrypted at rest. Returns immediately — you'll get the value in a "
            "follow-up tool call result that includes the credential. NEVER say 'I cannot' — "
            "always request the credential first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Short snake_case identifier, e.g. 'youtube_api', 'tiktok_session', 'spotify_token'."
                },
                "label": {
                    "type": "string",
                    "description": "Human-readable label in Arabic, e.g. 'مفتاح يوتيوب API'."
                },
                "instructions": {
                    "type": "string",
                    "description": "Arabic instructions on HOW the user can get the credential, with step-by-step links."
                },
            },
            "required": ["service", "label", "instructions"],
        },
    },
    {
        "name": "download_media",
        "description": (
            "🎬 Download a video/audio clip from YouTube, TikTok, Instagram, Twitter/X, "
            "Facebook, Vimeo, SoundCloud, or any of 1000+ supported sites (via yt-dlp). "
            "The file is saved to permanent storage and you get a public URL to embed in "
            "the user's site. Perfect for building video gallery sites, content "
            "aggregators, podcast hubs, or social media archives. "
            "If the source requires auth (private TikTok, etc.), use request_credential first "
            "to ask the user for cookies/session."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL of the video/audio (e.g. 'https://www.youtube.com/watch?v=...')."
                },
                "format": {
                    "type": "string",
                    "enum": ["mp4_720p", "mp4_1080p", "mp3_audio"],
                    "default": "mp4_720p",
                    "description": "Output format: 720p mp4 (default, fast), 1080p mp4, or audio-only mp3."
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "save_credential",
        "description": (
            "💾 Save / update a credential that the user pasted into the chat. Use this "
            "IMMEDIATELY whenever the user provides ANY API key, token, password, or "
            "secret in their message (e.g. 'هذا مفتاحي ghp_...', 'use this key: sk_...'). "
            "The value is encrypted and stored per-project. After saving, IMMEDIATELY call "
            "`validate_credential` to verify it works before claiming anything. "
            "NEVER claim a key is broken without running validate_credential first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "snake_case id, e.g. 'github_pat', 'elevenlabs_key', 'stripe_secret', 'openai_key'."},
                "value": {"type": "string", "description": "The raw secret/key/token the user provided."},
                "label": {"type": "string", "description": "Arabic human-readable label, e.g. 'مفتاح GitHub الشخصي'."},
            },
            "required": ["service", "value"],
        },
    },
    {
        "name": "validate_credential",
        "description": (
            "🧪 Test whether a stored credential ACTUALLY works by hitting the real "
            "third-party API. Returns HTTP status + scopes + account info. Supported "
            "services with real validation: github_pat, elevenlabs_key, openai_key, "
            "anthropic_key, stripe_secret, fal_key, tavily_api_key. For unknown "
            "services, returns a stored-mask check only. **You MUST call this before "
            "telling the user a key 'does not work' — otherwise you are hallucinating.**"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Service id previously saved via save_credential."},
            },
            "required": ["service"],
        },
    },
    {
        "name": "list_credentials",
        "description": (
            "📋 List all credentials saved for this project (masked values, no plaintext). "
            "Use this when the user asks 'وش المفاتيح المحفوظة' or before assuming a key "
            "is missing. Returns: service id, label, masked preview, last update time."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "delete_credential",
        "description": (
            "🗑️ Delete a stored credential (e.g. user wants to replace an invalid key, "
            "or rotate a leaked one). Always confirm with the user first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
            },
            "required": ["service"],
        },
    },
    {
        "name": "recommend_service",
        "description": (
            "🎯 Recommend the best 3rd-party SaaS service for a category — with pricing, "
            "free tiers, sign-up URLs, and step-by-step instructions in Arabic on how to "
            "obtain the API key. Categories: 'hosting', 'payments', 'email', 'sms', "
            "'storage', 'auth', 'database', 'analytics', 'cdn', 'domain', 'image_ai', "
            "'video_ai', 'voice_ai', 'llm', 'monitoring', 'backup'. Use this BEFORE "
            "asking the user for a credential so they know which service to sign up to. "
            "Returns 3 options ranked best-to-good with pros, cons, prices, signup links."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "One of the supported categories above."},
                "requirements": {"type": "string", "description": "What the user needs (Arabic ok), e.g. 'يحتاج SMS رخيص للسعودية'."},
                "region": {"type": "string", "description": "Optional region code, e.g. 'SA', 'EU', 'US'.", "default": "SA"},
            },
            "required": ["category"],
        },
    },
    {
        "name": "github_list_repos",
        "description": (
            "📦 List the user's GitHub repositories using the stored github_pat. "
            "Use this to show the user where their code lives, or before pushing files. "
            "Requires github_pat to be saved (call save_credential first if missing). "
            "Returns: repo name, full_name, private, default_branch, html_url."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 30, "minimum": 1, "maximum": 100},
            },
            "required": [],
        },
    },
    {
        "name": "github_create_repo",
        "description": (
            "🆕 Create a new GitHub repository under the authenticated user. Use this "
            "when the user says 'سوي ريبو لـ X' or 'أنشئ مشروع GitHub'. Requires "
            "github_pat with `repo` scope."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Repo name, lowercase-with-dashes."},
                "description": {"type": "string", "default": ""},
                "private": {"type": "boolean", "default": True},
                "auto_init": {"type": "boolean", "default": True, "description": "Create with initial README."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "github_push_file",
        "description": (
            "⬆️ Create or update a single file in a GitHub repo (commits directly to "
            "default branch via Contents API). Use this to push the user's site code "
            "to a public repo, or to back up generated HTML/JSON. Requires github_pat. "
            "Pass `repo` as 'owner/repo' format. If the file already exists, you MUST "
            "first call `github_get_file` to get its sha, then pass it back."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Format: 'owner/reponame'."},
                "path": {"type": "string", "description": "Path inside the repo, e.g. 'index.html', 'src/app.js'."},
                "content": {"type": "string", "description": "Raw text content (will be base64-encoded server-side)."},
                "message": {"type": "string", "description": "Commit message in Arabic or English."},
                "sha": {"type": "string", "description": "REQUIRED when updating an existing file. Get it from github_get_file."},
                "branch": {"type": "string", "description": "Optional branch name; defaults to repo default branch."},
            },
            "required": ["repo", "path", "content", "message"],
        },
    },
    {
        "name": "github_get_file",
        "description": (
            "📥 Read a file from a GitHub repo. Returns content + sha (sha is needed "
            "if you want to update the file afterwards via github_push_file)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Format: 'owner/reponame'."},
                "path": {"type": "string"},
                "branch": {"type": "string"},
            },
            "required": ["repo", "path"],
        },
    },
    {
        "name": "finish",
        "description": (
            "Call this when the work is done. Provide a short Arabic summary "
            "(2-4 lines) to show the user what was accomplished and the next "
            "logical question/option. This is the ONLY way to end the loop."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Arabic message to the user."},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of clickable next-step options (max 4).",
                },
            },
            "required": ["summary"],
        },
    },
]
# Append the advanced tool schemas (run_shell, analyze_file, file system, db_query, etc.)
TOOLS_SCHEMA.extend(ADVANCED_TOOL_SCHEMAS)
# Append the workflow tools (ask_user_inline, plan_task, delegate)
TOOLS_SCHEMA.extend(WORKFLOW_TOOL_SCHEMAS)
TOOLS_SCHEMA.extend(PHASE4_TOOL_SCHEMAS)
TOOLS_SCHEMA.extend(PHASE5_TOOL_SCHEMAS)
TOOLS_SCHEMA.extend(DESKTOP_TOOL_SCHEMAS)


# Tools restricted to the OWNER role only (high-risk / privileged capabilities).
# Filtered out of the schema sent to non-owner customers.
OWNER_ONLY_TOOL_NAMES = {
    # Local browser control — driving the owner's actual laptop
    "local_browser_pair", "local_browser_status", "local_browser_act",
    # Desktop Agent — native OS control on the owner's physical machine
    "desktop_pair", "desktop_status", "desktop_screenshot", "desktop_act",
    # Server-side shell — can install packages, run scripts
    "run_shell",
    # Deployment to external hosts under the owner's accounts
    "deploy_to",
    # Sending real emails / SMS from the owner's accounts
    "send_email", "send_sms",
    # Direct DB queries — exposes raw merchant data
    "db_query", "db_count",
    # GitHub push — modifies the owner's repos
    "github_create_repo", "github_push_file",
}


def tools_for_user(is_owner: bool) -> List[Dict[str, Any]]:
    """Return the tool schema list filtered by user role.

    Non-owner customers see ~50 tools (no shell, deploy, local-browser, etc.).
    Owner sees the full 63 tools.
    """
    if is_owner:
        return TOOLS_SCHEMA
    return [t for t in TOOLS_SCHEMA if t["name"] not in OWNER_ONLY_TOOL_NAMES]


# ─── Tool Implementations ─────────────────────────────────────────────────────
class FreeBuildToolContext:
    """Holds mutable project state during an agent run."""

    def __init__(self, project: Dict[str, Any], auth_token: Optional[str] = None, db=None,
                 is_owner: bool = False):
        self.project = dict(project)  # copy
        self.project_id: Optional[str] = project.get("id")
        self.auth_token: Optional[str] = auth_token
        self.db = db
        self.is_owner: bool = bool(is_owner)
        self.current_html: str = project.get("current_html") or ""
        self.changes_made: int = 0
        self.snapshots_to_create: List[Dict[str, Any]] = []
        self.tool_log: List[Dict[str, Any]] = []

    def snapshot_before_write(self):
        if self.current_html:
            self.snapshots_to_create.append({
                "id": str(uuid.uuid4()),
                "html": self.current_html,
                "created_at": _now(),
                "user_msg": "[agent loop change]",
                "summary": _summarize_html(self.current_html),
            })

    def log(self, tool: str, args: Dict[str, Any], result: Any):
        self.tool_log.append({"tool": tool, "args": args, "result_preview": str(result)[:200]})


def _exec_tool(ctx: FreeBuildToolContext, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronously execute a single tool call and return the result.
    NOTE: async tools (web_search, fetch_url, generate_image) are dispatched via _exec_tool_async."""
    try:
        if name == "read_current_html":
            html = ctx.current_html
            return {
                "length": len(html),
                "title": (re.search(r"<title[^>]*>([^<]+)</title>", html, re.I).group(1)[:80] if re.search(r"<title", html, re.I) else ""),
                "section_ids": re.findall(r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']', html, re.I),
                "nav_anchors": re.findall(r'href\s*=\s*["\']#([a-zA-Z0-9_\-]+)["\']', html, re.I),
                "broken_anchors": _verify_anchor_links(html),
                "has_body_close": "</body>" in html.lower(),
                "summary": _summarize_html(html),
            }
        if name == "list_sections":
            sections = []
            for m in re.finditer(
                r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\'][^>]*>([\s\S]*?)</section>',
                ctx.current_html, re.I,
            ):
                sid, inner = m.group(1), m.group(2)
                text_only = re.sub(r"<[^>]+>", " ", inner).strip()
                sections.append({
                    "id": sid,
                    "content_size": len(inner),
                    "text_preview": text_only[:120],
                    "is_placeholder": len(text_only) < 40 or any(
                        p in text_only for p in ["قيد البناء", "placeholder", "TODO", "Coming soon"]
                    ),
                })
            return {"count": len(sections), "sections": sections}
        if name == "validate_html":
            issues = _comprehensive_validation(ctx.current_html)
            return {"issue_count": len(issues), "issues": issues, "is_clean": len([i for i in issues if i["severity"] == "high"]) == 0}
        if name == "write_full_html":
            new_html = (args.get("html") or "").strip()
            if not new_html:
                return {"ok": False, "error": "html cannot be empty"}
            if not re.search(r"<html[\s\S]*</html>", new_html, re.I):
                return {"ok": False, "error": "must be a complete <!DOCTYPE html>...</html> document"}
            # auto-fix dead navigation links
            new_html, fixed = _fix_dead_navigation_links(new_html)
            ctx.snapshot_before_write()
            ctx.current_html = new_html
            ctx.changes_made += 1
            return {"ok": True, "new_length": len(new_html), "dead_links_fixed": fixed}
        if name == "apply_section":
            sid = (args.get("id") or "").strip()
            frag = (args.get("html") or "").strip()
            op = args.get("op") or "append"
            if not sid or not frag:
                return {"ok": False, "error": "id and html are required"}
            if not ctx.current_html:
                return {"ok": False, "error": "current_html is empty; call write_full_html first"}
            appends = [(sid, frag)] if op == "append" else []
            replaces = [(sid, frag)] if op == "replace" else []
            merged = _merge_sections(ctx.current_html, appends, replaces, None)
            if not merged:
                return {"ok": False, "error": "merge failed"}
            merged, fixed = _fix_dead_navigation_links(merged)
            ctx.snapshot_before_write()
            ctx.current_html = merged
            ctx.changes_made += 1
            return {"ok": True, "op": op, "id": sid, "new_total_length": len(merged), "dead_links_fixed": fixed}
        if name == "update_nav":
            items = [(i["id"], i["label"]) for i in (args.get("items") or []) if i.get("id") and i.get("label")]
            if not items:
                return {"ok": False, "error": "items array is required"}
            merged = _merge_sections(ctx.current_html, [], [], items)
            if not merged:
                return {"ok": False, "error": "nav update failed (no <nav> tag found?)"}
            ctx.snapshot_before_write()
            ctx.current_html = merged
            ctx.changes_made += 1
            return {"ok": True, "items": items, "new_length": len(merged)}
        if name == "search_html":
            pat = args.get("pattern") or ""
            try:
                rx = re.compile(pat, re.I | re.S)
            except re.error as e:
                return {"ok": False, "error": f"invalid regex: {e}"}
            hits = []
            for m in list(rx.finditer(ctx.current_html))[:10]:
                start = max(0, m.start() - 50)
                end = min(len(ctx.current_html), m.end() + 50)
                hits.append({"match": m.group(0)[:200], "context": ctx.current_html[start:end]})
            return {"hits": hits, "count": len(hits)}
        if name == "lint_javascript":
            code = (args.get("code") or "").strip()
            if not code:
                # Extract all inline <script> blocks from current_html
                scripts = re.findall(r"<script\b[^>]*>([\s\S]*?)</script>", ctx.current_html, re.I)
                code = "\n".join(s for s in scripts if "src=" not in s[:100])
            if not code.strip():
                return {"ok": True, "issues": [], "message": "no inline JS found"}
            issues = []
            # Basic structural checks
            stack = []
            pairs = {")": "(", "]": "[", "}": "{"}
            for i, ch in enumerate(code):
                if ch in "([{":
                    stack.append((ch, i))
                elif ch in ")]}":
                    if not stack or stack[-1][0] != pairs[ch]:
                        issues.append({"severity": "high", "code": "unmatched_bracket", "message": f"غير متطابق '{ch}' عند الموضع {i}", "line": code[:i].count('\n')+1})
                        break
                    stack.pop()
            if stack:
                ch, i = stack[-1]
                issues.append({"severity": "high", "code": "unclosed_bracket", "message": f"غير مغلق '{ch}' عند الموضع {i}", "line": code[:i].count('\n')+1})
            # Common undefined-variable patterns (simple)
            for m in re.finditer(r"\b(addEventListner|getElementByID|innerHtml|onclik|querySelectorALL)\b", code):
                issues.append({"severity": "high", "code": "typo", "message": f"خطأ إملائي في API: '{m.group(1)}'", "fix_hint": "تحقق من تهجئة الـDOM API"})
            # Strict-mode reserved words used as vars
            for m in re.finditer(r"\b(?:var|let|const)\s+(arguments|eval|implements|interface|package|private|protected|public|static|yield)\b", code):
                issues.append({"severity": "medium", "code": "reserved_word", "message": f"كلمة محجوزة كمتغير: '{m.group(1)}'"})
            return {"ok": True, "issues": issues, "is_clean": len([i for i in issues if i["severity"] == "high"]) == 0, "lines_checked": code.count("\n")+1}
        # Async tools — return a sentinel so the caller knows to await them
        if name in ("web_search", "fetch_url", "generate_image", "test_page", "publish_site",
                    "request_credential", "download_media",
                    "list_voices", "generate_voiceover", "write_script",
                    "generate_storyboard", "update_world_bible",
                    "save_credential", "validate_credential", "list_credentials",
                    "delete_credential", "recommend_service",
                    "github_list_repos", "github_create_repo", "github_push_file",
                    "github_get_file") or name in ADVANCED_TOOL_NAMES or name in WORKFLOW_TOOL_NAMES or name in PHASE4_TOOL_NAMES or name in PHASE5_TOOL_NAMES or name in DESKTOP_TOOL_NAMES:
            return {"__async__": True, "tool": name, "args": args}
        return {"error": f"unknown tool: {name}"}
    except Exception as e:
        logger.exception(f"tool {name} failed")
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


async def _dispatch_tool(ctx: FreeBuildToolContext, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Unified dispatcher — handles both sync and async tools.

    Owner-only tools are double-guarded here: even if a non-owner schema somehow
    sent the tool call, it's rejected at dispatch time.
    """
    if name in OWNER_ONLY_TOOL_NAMES and not ctx.is_owner:
        return {
            "ok": False,
            "error": f"🔒 '{name}' is an owner-only tool — not available for customer accounts.",
            "permission_denied": True,
        }
    result = _exec_tool(ctx, name, args)
    if isinstance(result, dict) and result.get("__async__"):
        return await _exec_tool_async(ctx, name, args)
    return result


# ─── Async Tool Dispatcher (web_search, fetch_url, generate_image) ────────────
async def _exec_tool_async(ctx: FreeBuildToolContext, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if name == "web_search":
            query = (args.get("query") or "").strip()
            max_results = max(1, min(int(args.get("max_results") or 5), 10))
            if not query:
                return {"ok": False, "error": "query is required"}
            # Use Tavily if key present, else DuckDuckGo HTML scrape as a free fallback
            tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
            try:
                import httpx
            except ImportError:
                return {"ok": False, "error": "httpx not installed"}
            results = []
            if tavily_key:
                try:
                    async with httpx.AsyncClient(timeout=15) as cl:
                        r = await cl.post("https://api.tavily.com/search", json={
                            "api_key": tavily_key, "query": query, "max_results": max_results,
                            "search_depth": "basic", "include_answer": False,
                        })
                        data = r.json()
                        for item in (data.get("results") or [])[:max_results]:
                            results.append({"title": item.get("title", ""), "url": item.get("url", ""), "snippet": (item.get("content") or "")[:250]})
                except Exception as e:
                    logger.warning(f"tavily failed: {e}")
            if not results:
                # DuckDuckGo HTML fallback
                try:
                    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as cl:
                        r = await cl.get("https://html.duckduckgo.com/html/", params={"q": query})
                        html = r.text
                        # very simple parse
                        for m in list(re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S))[:max_results]:
                            url_raw = m.group(1)
                            # ddg wraps in redirect: /l/?uddg=...
                            actual = re.search(r"uddg=([^&]+)", url_raw)
                            from urllib.parse import unquote
                            url = unquote(actual.group(1)) if actual else url_raw
                            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()[:120]
                            results.append({"title": title, "url": url, "snippet": ""})
                except Exception as e:
                    return {"ok": False, "error": f"search failed: {e}"}
            return {"ok": True, "query": query, "results_count": len(results), "results": results}

        if name == "fetch_url":
            url = (args.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                return {"ok": False, "error": "url must start with http:// or https://"}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 ZenrexBot/1.0"}) as cl:
                    r = await cl.get(url)
                    content_type = r.headers.get("content-type", "")
                    if "html" in content_type or "text" in content_type:
                        # Strip scripts/styles, keep visible structure
                        clean = re.sub(r"<script[\s\S]*?</script>", "", r.text, flags=re.I)
                        clean = re.sub(r"<style[\s\S]*?</style>", "", clean, flags=re.I)
                        # Limit to 50KB
                        return {"ok": True, "url": url, "status": r.status_code, "content_type": content_type, "size": len(r.text), "text": clean[:50000]}
                    return {"ok": True, "url": url, "status": r.status_code, "content_type": content_type, "size": len(r.content), "text": "[non-text content]"}
            except Exception as e:
                return {"ok": False, "error": f"fetch failed: {type(e).__name__}: {str(e)[:200]}"}

        if name == "generate_image":
            description = (args.get("description") or "").strip()
            if not description:
                return {"ok": False, "error": "description is required"}
            w = int(args.get("width") or 1024)
            h = int(args.get("height") or 1024)
            try:
                import httpx
                # Use our internal /api/image-studio/generate which already wraps Gemini Nano Banana
                async with httpx.AsyncClient(timeout=60) as cl:
                    r = await cl.post("http://localhost:8001/api/image-studio/generate", json={
                        "prompt": description, "count": 1, "style": "lifestyle", "width": w, "height": h
                    })
                    data = r.json()
                    imgs = data.get("images") or []
                    if not imgs:
                        return {"ok": False, "error": "AI returned no image"}
                    return {"ok": True, "url": imgs[0], "model": data.get("model", "gemini-nano-banana"), "description": description}
            except Exception as e:
                return {"ok": False, "error": f"image gen failed: {type(e).__name__}: {str(e)[:200]}"}
        if name == "test_page":
            url = (args.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                return {"ok": False, "error": "url must start with http(s)://"}
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as pw:
                    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                    ctx_b = await browser.new_context(viewport={"width": 1280, "height": 720})
                    page = await ctx_b.new_page()
                    console_errors = []
                    page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text[:200]}") if msg.type in ("error", "warning") else None)
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    except Exception as e:
                        console_errors.append(f"[nav_error] {type(e).__name__}: {str(e)[:200]}")
                    await page.wait_for_timeout(2500)
                    title = await page.title()
                    metrics = await page.evaluate("""() => {
                        const videos = Array.from(document.querySelectorAll('video'));
                        return {
                            video_count: videos.length,
                            video_sources: videos.map(v => v.currentSrc || (v.querySelector('source')?.src) || '').slice(0, 10),
                            video_ready_states: videos.map(v => v.readyState).slice(0, 10),
                            iframe_count: document.querySelectorAll('iframe').length,
                            img_count: document.querySelectorAll('img').length,
                            section_count: document.querySelectorAll('section').length,
                            has_h1: !!document.querySelector('h1'),
                            body_text_len: document.body.innerText.length,
                            scroll_height: document.body.scrollHeight,
                        };
                    }""")
                    import os as _os, uuid as _uuid, shutil as _sh, datetime as _dt
                    snap_id = _uuid.uuid4().hex[:16]
                    media_dir = "/app/backend/uploads/freebuild_media"
                    _os.makedirs(media_dir, exist_ok=True)
                    snap_path = f"{media_dir}/{snap_id}.jpg"
                    await page.screenshot(path=snap_path, type="jpeg", quality=55, full_page=False)
                    await browser.close()
                    snapshot_url = f"https://zenrex.ai/api/freebuild-chat/media/file/{snap_id}.jpg"
                    if ctx.db is not None:
                        try:
                            await ctx.db.freebuild_media_assets.insert_one({
                                "id": snap_id, "filename": f"{snap_id}.jpg", "ext": "jpg",
                                "kind": "screenshot", "url_tested": url,
                                "public_url": snapshot_url,
                                "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                            })
                        except Exception:
                            pass
                    return {
                        "ok": True,
                        "url": url,
                        "title": title,
                        "screenshot_url": snapshot_url,
                        "metrics": metrics,
                        "console_errors": console_errors[:20],
                        "summary": (
                            f"فتحت الصفحة ({title[:60]}). "
                            f"video={metrics['video_count']} img={metrics['img_count']} sections={metrics['section_count']}. "
                            f"console errors: {len(console_errors)}. "
                            f"📸 screenshot: {snapshot_url}"
                        ),
                    }
            except ImportError:
                return {"ok": False, "error": "playwright غير مثبت في السيرفر"}
            except Exception as e:
                return {"ok": False, "error": f"test_page failed: {type(e).__name__}: {str(e)[:200]}"}



        if name == "publish_site":
            slug = (args.get("slug") or "").strip().lower()
            if not slug:
                return {"ok": False, "error": "slug مطلوب"}
            if ctx.project_id is None:
                return {"ok": False, "error": "project_id غير متوفر في الـcontext"}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=30) as cl:
                    r = await cl.post(
                        f"http://localhost:8001/api/freebuild-chat/project/{ctx.project_id}/publish",
                        data={"slug": slug},
                        headers={"Authorization": f"Bearer {ctx.auth_token}"} if ctx.auth_token else {},
                    )
                    if r.status_code != 200:
                        return {"ok": False, "error": f"النشر فشل ({r.status_code}): {r.text[:200]}"}
                    data = r.json()
                    return {"ok": True, "url": data.get("url"), "slug": slug, "message": f"✅ موقعك مُتاح الآن على {data.get('url')}"}
            except Exception as e:
                return {"ok": False, "error": f"publish failed: {type(e).__name__}: {str(e)[:200]}"}

        if name == "request_credential":
            service = (args.get("service") or "").strip().lower()
            label = (args.get("label") or service).strip()
            instructions = (args.get("instructions") or "").strip()
            if not service:
                return {"ok": False, "error": "service مطلوب"}
            # Check if the credential already exists for this project — if yes, return the (decrypted) value
            if ctx.project_id and ctx.db is not None:
                try:
                    existing = await ctx.db.freebuild_credentials.find_one(
                        {"project_id": ctx.project_id, "service": service}
                    )
                    if existing and existing.get("value_enc"):
                        from cryptography.fernet import Fernet
                        import base64, hashlib, os as _os
                        seed = _os.environ.get("JWT_SECRET", "fallback-dev-secret-do-not-use")
                        key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())
                        try:
                            plain = Fernet(key).decrypt(existing["value_enc"].encode()).decode()
                            return {"ok": True, "service": service, "value": plain, "from_cache": True, "label": label}
                        except Exception:
                            pass
                except Exception:
                    pass
            # Else emit a sentinel — frontend pops a modal asking the user for the credential.
            return {
                "ok": True,
                "needs_user_input": True,
                "service": service,
                "label": label,
                "instructions": instructions,
                "message": f"🔑 يحتاج مفتاح: {label} — انتظر العميل يدخله من واجهة الشات.",
            }

        if name == "download_media":
            url = (args.get("url") or "").strip()
            fmt = (args.get("format") or "mp4_720p").strip()
            if not url.startswith(("http://", "https://")):
                return {"ok": False, "error": "url must start with http(s)://"}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=180) as cl:
                    r = await cl.post(
                        "http://localhost:8001/api/freebuild-chat/media/download",
                        data={
                            "url": url,
                            "format": fmt,
                            "project_id": ctx.project_id or "",
                        },
                        headers={"Authorization": f"Bearer {ctx.auth_token}"} if ctx.auth_token else {},
                    )
                    if r.status_code != 200:
                        return {"ok": False, "error": f"download failed ({r.status_code}): {r.text[:200]}"}
                    data = r.json()
                    return {
                        "ok": True,
                        "file_url": data.get("file_url"),
                        "thumbnail_url": data.get("thumbnail_url"),
                        "title": data.get("title"),
                        "duration": data.get("duration"),
                        "source": data.get("source"),
                        "format": fmt,
                    }
            except Exception as e:
                return {"ok": False, "error": f"download failed: {type(e).__name__}: {str(e)[:200]}"}

        if name == "list_voices":
            try:
                import httpx, os as _os
                key = _os.environ.get("ELEVENLABS_API_KEY", "")
                if not key:
                    return {"ok": False, "error": "ELEVENLABS_API_KEY غير مكوّن"}
                async with httpx.AsyncClient(timeout=15) as cl:
                    r = await cl.get("https://api.elevenlabs.io/v2/voices", headers={"xi-api-key": key},
                                     params={"page_size": min(int(args.get("limit") or 20), 50)})
                    if r.status_code != 200:
                        return {"ok": False, "error": f"ElevenLabs: {r.status_code} {r.text[:200]}"}
                    data = r.json()
                    lang_filter = (args.get("language") or "").strip().lower()
                    voices = []
                    for v in data.get("voices", []):
                        labels = v.get("labels") or {}
                        lang = (labels.get("language") or "").lower()
                        if lang_filter and lang_filter not in lang:
                            continue
                        voices.append({
                            "voice_id": v.get("voice_id"),
                            "name": v.get("name"),
                            "language": lang,
                            "gender": labels.get("gender", ""),
                            "age": labels.get("age", ""),
                            "accent": labels.get("accent", ""),
                            "description": labels.get("description", ""),
                            "preview_url": v.get("preview_url"),
                        })
                    return {"ok": True, "count": len(voices), "voices": voices[:50]}
            except Exception as e:
                return {"ok": False, "error": f"list_voices: {type(e).__name__}: {str(e)[:200]}"}

        if name == "generate_voiceover":
            text = (args.get("text") or "").strip()
            if not text:
                return {"ok": False, "error": "text مطلوب"}
            if len(text) > 5000:
                return {"ok": False, "error": "النص طويل (>5000 حرف). قسّمه على دفعات."}
            voice_id = (args.get("voice_id") or "21m00Tcm4TlvDq8ikWAM").strip()  # Rachel default
            model_id = (args.get("model") or "eleven_multilingual_v2").strip()
            try:
                import httpx, os as _os, uuid as _uuid
                key = _os.environ.get("ELEVENLABS_API_KEY", "")
                async with httpx.AsyncClient(timeout=120) as cl:
                    r = await cl.post(
                        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
                        json={"text": text, "model_id": model_id,
                              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0}},
                    )
                    if r.status_code != 200:
                        return {"ok": False, "error": f"ElevenLabs: {r.status_code} {r.text[:200]}"}
                    media_dir = "/app/backend/uploads/freebuild_media"
                    _os.makedirs(media_dir, exist_ok=True)
                    file_id = _uuid.uuid4().hex[:16]
                    path = f"{media_dir}/{file_id}.mp3"
                    with open(path, "wb") as f:
                        f.write(r.content)
                    public_url = f"https://zenrex.ai/api/freebuild-chat/media/file/{file_id}.mp3"
                    if ctx.db is not None:
                        try:
                            import datetime as _dt
                            await ctx.db.freebuild_media_assets.insert_one({
                                "id": file_id, "filename": f"{file_id}.mp3", "ext": "mp3",
                                "kind": "voiceover", "voice_id": voice_id, "text_len": len(text),
                                "public_url": public_url, "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                            })
                        except Exception:
                            pass
                    return {"ok": True, "audio_url": public_url, "voice_id": voice_id,
                            "model": model_id, "size_bytes": len(r.content),
                            "embed_html": f'<audio controls src="{public_url}"></audio>'}
            except Exception as e:
                return {"ok": False, "error": f"voiceover: {type(e).__name__}: {str(e)[:200]}"}

        if name == "write_script":
            # AI-side helper — actually we just return a structured template the model can fill
            # via subsequent apply_section calls. This tool's purpose is to FORCE structure.
            title = (args.get("title") or "").strip()
            logline = (args.get("logline") or "").strip()
            genre = (args.get("genre") or "drama").strip()
            duration = int(args.get("duration_seconds") or 60)
            synopsis = (args.get("synopsis") or "").strip()
            script_template = f"""<section id="script" style="background:#0a0a14;color:#fbbf24;padding:60px 30px;font-family:Cairo,sans-serif">
<h2 style="font-size:36px;margin-bottom:20px">📜 سيناريو: {title}</h2>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:30px">
  <div style="background:#1a1625;padding:15px;border-radius:10px"><b>النوع:</b> {genre}</div>
  <div style="background:#1a1625;padding:15px;border-radius:10px"><b>المدة:</b> {duration} ثانية</div>
</div>
<h3 style="color:#e5e5e5;margin-top:30px">Logline:</h3>
<p style="color:#fff;font-size:18px;line-height:1.7">{logline}</p>
{f'<h3 style="color:#e5e5e5;margin-top:30px">Synopsis:</h3><p style="color:#d4d4d8;font-size:16px;line-height:1.7">{synopsis}</p>' if synopsis else ''}
<h3 style="color:#e5e5e5;margin-top:30px">📋 Shot List:</h3>
<p style="color:#a78bfa;font-style:italic">سيتم ملء قائمة المشاهد بعد توليد الستوري بورد...</p>
</section>"""
            return {"ok": True, "script_html": script_template, "title": title,
                    "logline": logline, "duration_seconds": duration,
                    "next_step": "Use apply_section with this HTML, then call generate_storyboard."}

        if name == "generate_storyboard":
            scenes = args.get("scenes") or []
            if not scenes or not isinstance(scenes, list):
                return {"ok": False, "error": "scenes (قائمة) مطلوبة"}
            style = (args.get("style") or "cinematic").strip()
            results = []
            try:
                import httpx
                async with httpx.AsyncClient(timeout=90) as cl:
                    for i, scene in enumerate(scenes[:6]):  # max 6
                        prompt = f"{scene}, {style} style, 16:9 aspect ratio, professional cinematography, dramatic lighting"
                        r = await cl.post("http://localhost:8001/api/image-studio/generate", json={
                            "prompt": prompt, "count": 1, "style": style, "width": 1280, "height": 720
                        })
                        try:
                            data = r.json()
                            imgs = data.get("images") or []
                            results.append({"scene_index": i + 1, "description": scene,
                                            "image_url": imgs[0] if imgs else None,
                                            "ok": bool(imgs)})
                        except Exception:
                            results.append({"scene_index": i + 1, "description": scene, "ok": False})
                # Build a storyboard HTML section
                cards = "".join(
                    f'<div style="background:#1a1625;border-radius:12px;overflow:hidden;border:1px solid #fbbf24">'
                    f'<img src="{r.get("image_url","")}" style="width:100%;height:200px;object-fit:cover" />'
                    f'<div style="padding:15px"><h4 style="color:#fbbf24;margin:0 0 8px">مشهد {r["scene_index"]}</h4>'
                    f'<p style="color:#d4d4d8;font-size:13px;margin:0">{r["description"]}</p></div></div>'
                    for r in results if r.get("ok")
                )
                section_html = (
                    '<section id="storyboard" style="background:#08070d;color:#fbbf24;padding:60px 30px;font-family:Cairo,sans-serif">'
                    '<h2 style="font-size:36px;margin-bottom:30px">🎭 الستوري بورد</h2>'
                    f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px">{cards}</div>'
                    '</section>'
                )
                return {"ok": True, "scenes_generated": len([r for r in results if r.get("ok")]),
                        "results": results, "section_html": section_html}
            except Exception as e:
                return {"ok": False, "error": f"storyboard: {type(e).__name__}: {str(e)[:200]}"}

        if name == "update_world_bible":
            if not ctx.project_id or ctx.db is None:
                return {"ok": False, "error": "project_id أو db غير متوفر"}
            update_data = {
                "characters": args.get("characters") or [],
                "locations": args.get("locations") or [],
                "plot_points": args.get("plot_points") or [],
                "style_rules": args.get("style_rules") or "",
                "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            }
            try:
                await ctx.db.cinema_world_bible.update_one(
                    {"project_id": ctx.project_id},
                    {"$set": {"project_id": ctx.project_id, **update_data}},
                    upsert=True,
                )
                return {"ok": True, "saved": True, "project_id": ctx.project_id,
                        "character_count": len(update_data["characters"]),
                        "location_count": len(update_data["locations"]),
                        "plot_count": len(update_data["plot_points"])}
            except Exception as e:
                return {"ok": False, "error": f"world_bible: {type(e).__name__}: {str(e)[:200]}"}

        # ── Credential Management ──────────────────────────────────────────
        if name == "save_credential":
            if ctx.project_id is None or ctx.db is None:
                return {"ok": False, "error": "project_id أو DB غير متوفرين"}
            service = (args.get("service") or "").strip().lower()
            value = (args.get("value") or "").strip()
            label = (args.get("label") or service).strip()
            if not service or not value:
                return {"ok": False, "error": "service و value مطلوبين"}
            if not re.match(r"^[a-z][a-z0-9_-]{1,40}$", service):
                return {"ok": False, "error": f"اسم خدمة غير صالح: '{service}' — استخدم snake_case (مثل github_pat)"}
            if len(value) < 4:
                return {"ok": False, "error": "القيمة قصيرة جداً (<4 حرف). تأكد من نسخ المفتاح كاملاً."}
            try:
                import datetime as _dt
                now = _dt.datetime.now(_dt.timezone.utc).isoformat()
                await ctx.db.freebuild_credentials.update_one(
                    {"project_id": ctx.project_id, "service": service},
                    {"$set": {
                        "project_id": ctx.project_id,
                        "service": service,
                        "label": label,
                        "value_enc": _enc(value),
                        "mask": _mask(value),
                        "updated_at": now,
                    }, "$setOnInsert": {"created_at": now}},
                    upsert=True,
                )
                return {"ok": True, "service": service, "mask": _mask(value), "label": label,
                        "message": f"✅ تم حفظ {label} بأمان (مشفّر). الخطوة الجاية: استدعِ `validate_credential` لتأكيد إنه شغّال."}
            except Exception as e:
                return {"ok": False, "error": f"save_credential: {type(e).__name__}: {str(e)[:200]}"}

        if name == "validate_credential":
            if ctx.project_id is None or ctx.db is None:
                return {"ok": False, "error": "project_id أو DB غير متوفرين"}
            service = (args.get("service") or "").strip().lower()
            if not service:
                return {"ok": False, "error": "service مطلوب"}
            try:
                doc = await ctx.db.freebuild_credentials.find_one(
                    {"project_id": ctx.project_id, "service": service}
                )
                if not doc:
                    return {"ok": False, "service": service, "saved": False,
                            "error": f"لا يوجد مفتاح محفوظ للخدمة '{service}'. استدعِ `save_credential` أولاً أو اطلب من العميل عبر `request_credential`."}
                val = _dec(doc.get("value_enc") or "")
                if not val:
                    return {"ok": False, "service": service, "error": "فشل فك تشفير القيمة المحفوظة (قد يكون JWT_SECRET تغيّر)."}
                import httpx
                async with httpx.AsyncClient(timeout=15, follow_redirects=False) as cl:
                    # Per-service real validation
                    if service in ("github_pat", "github_token", "github"):
                        r = await cl.get("https://api.github.com/user",
                                         headers={"Authorization": f"token {val}", "Accept": "application/vnd.github+json"})
                        if r.status_code == 200:
                            data = r.json()
                            scopes = r.headers.get("x-oauth-scopes", "")
                            rl = r.headers.get("x-ratelimit-remaining", "")
                            return {"ok": True, "service": service, "valid": True, "http_status": 200,
                                    "account": data.get("login"), "name": data.get("name") or "",
                                    "scopes": scopes, "rate_limit_remaining": rl,
                                    "message": f"✅ المفتاح شغّال 100%. الحساب: {data.get('login')}، الصلاحيات: {scopes or 'محدودة'}، الحد المتبقي: {rl}."}
                        return {"ok": False, "service": service, "valid": False, "http_status": r.status_code,
                                "error": f"GitHub رفض المفتاح: HTTP {r.status_code} — {r.text[:200]}"}
                    if service in ("elevenlabs_key", "elevenlabs"):
                        r = await cl.get("https://api.elevenlabs.io/v1/user",
                                         headers={"xi-api-key": val})
                        if r.status_code == 200:
                            data = r.json()
                            return {"ok": True, "service": service, "valid": True, "http_status": 200,
                                    "tier": (data.get("subscription") or {}).get("tier"),
                                    "character_count": (data.get("subscription") or {}).get("character_count"),
                                    "character_limit": (data.get("subscription") or {}).get("character_limit"),
                                    "message": f"✅ ElevenLabs شغّال. الباقة: {(data.get('subscription') or {}).get('tier')}."}
                        return {"ok": False, "service": service, "valid": False, "http_status": r.status_code,
                                "error": f"ElevenLabs رفض المفتاح: HTTP {r.status_code} — {r.text[:200]}"}
                    if service in ("openai_key", "openai"):
                        r = await cl.get("https://api.openai.com/v1/models",
                                         headers={"Authorization": f"Bearer {val}"})
                        if r.status_code == 200:
                            n = len((r.json() or {}).get("data") or [])
                            return {"ok": True, "service": service, "valid": True, "http_status": 200,
                                    "models_available": n,
                                    "message": f"✅ OpenAI شغّال. {n} موديل متاح."}
                        return {"ok": False, "service": service, "valid": False, "http_status": r.status_code,
                                "error": f"OpenAI رفض المفتاح: HTTP {r.status_code} — {r.text[:200]}"}
                    if service in ("anthropic_key", "anthropic"):
                        r = await cl.post("https://api.anthropic.com/v1/messages",
                                          headers={"x-api-key": val, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                                          json={"model": "claude-3-5-haiku-20241022", "max_tokens": 1,
                                                "messages": [{"role": "user", "content": "hi"}]})
                        if r.status_code in (200, 400):
                            return {"ok": True, "service": service, "valid": True, "http_status": r.status_code,
                                    "message": "✅ Anthropic شغّال."}
                        return {"ok": False, "service": service, "valid": False, "http_status": r.status_code,
                                "error": f"Anthropic رفض المفتاح: HTTP {r.status_code} — {r.text[:200]}"}
                    if service in ("stripe_secret", "stripe", "stripe_key"):
                        r = await cl.get("https://api.stripe.com/v1/account",
                                         headers={"Authorization": f"Bearer {val}"})
                        if r.status_code == 200:
                            data = r.json()
                            return {"ok": True, "service": service, "valid": True, "http_status": 200,
                                    "account_id": data.get("id"), "country": data.get("country"),
                                    "default_currency": data.get("default_currency"),
                                    "message": f"✅ Stripe شغّال. الحساب: {data.get('id')}, العملة: {data.get('default_currency')}."}
                        return {"ok": False, "service": service, "valid": False, "http_status": r.status_code,
                                "error": f"Stripe رفض المفتاح: HTTP {r.status_code} — {r.text[:200]}"}
                    if service in ("fal_key", "fal", "fal_ai_key"):
                        r = await cl.get("https://queue.fal.run/health",
                                         headers={"Authorization": f"Key {val}"})
                        # fal.ai doesn't have a clean /me endpoint; we hit a public health probe
                        # which still returns 401 for invalid keys.
                        return {"ok": r.status_code < 500, "service": service,
                                "valid": r.status_code != 401, "http_status": r.status_code,
                                "message": ("✅ مفتاح fal.ai مقبول (محتاج اختبار توليد فعلي للتأكد النهائي)."
                                            if r.status_code != 401 else f"❌ fal.ai رفض المفتاح: HTTP {r.status_code}")}
                    if service in ("tavily_api_key", "tavily"):
                        r = await cl.post("https://api.tavily.com/search",
                                          json={"api_key": val, "query": "ping", "max_results": 1})
                        if r.status_code == 200:
                            return {"ok": True, "service": service, "valid": True,
                                    "message": "✅ Tavily شغّال."}
                        return {"ok": False, "service": service, "valid": False, "http_status": r.status_code,
                                "error": f"Tavily رفض المفتاح: HTTP {r.status_code} — {r.text[:200]}"}
                # Unknown service → can only confirm it's stored, not that it works
                return {"ok": True, "service": service, "valid": None, "stored_only": True,
                        "mask": doc.get("mask", ""),
                        "message": f"⚠️ ما عندي اختبار حقيقي لخدمة '{service}' بعد — لكن المفتاح محفوظ ومتاح. لو تبيه يُختبر فعلياً، استخدمه في أداة المهمة الفعلية واشف النتيجة."}
            except Exception as e:
                return {"ok": False, "error": f"validate_credential: {type(e).__name__}: {str(e)[:200]}"}

        if name == "list_credentials":
            if ctx.project_id is None or ctx.db is None:
                return {"ok": False, "error": "project_id أو DB غير متوفرين"}
            try:
                items = await ctx.db.freebuild_credentials.find(
                    {"project_id": ctx.project_id},
                    {"_id": 0, "service": 1, "label": 1, "mask": 1, "updated_at": 1, "created_at": 1},
                ).to_list(length=100)
                return {"ok": True, "count": len(items), "credentials": items,
                        "message": (f"عندك {len(items)} مفتاح محفوظ." if items else "ما فيه أي مفتاح محفوظ بعد.")}
            except Exception as e:
                return {"ok": False, "error": f"list_credentials: {type(e).__name__}: {str(e)[:200]}"}

        if name == "delete_credential":
            if ctx.project_id is None or ctx.db is None:
                return {"ok": False, "error": "project_id أو DB غير متوفرين"}
            service = (args.get("service") or "").strip().lower()
            if not service:
                return {"ok": False, "error": "service مطلوب"}
            try:
                r = await ctx.db.freebuild_credentials.delete_one(
                    {"project_id": ctx.project_id, "service": service}
                )
                return {"ok": True, "service": service, "deleted_count": r.deleted_count,
                        "message": (f"✅ تم حذف {service}." if r.deleted_count else f"⚠️ لا يوجد مفتاح بإسم {service}.")}
            except Exception as e:
                return {"ok": False, "error": f"delete_credential: {type(e).__name__}: {str(e)[:200]}"}

        if name == "recommend_service":
            category = (args.get("category") or "").strip().lower()
            requirements = (args.get("requirements") or "").strip()
            region = (args.get("region") or "SA").strip().upper()
            catalog = _SERVICE_CATALOG.get(category)
            if not catalog:
                supported = ", ".join(sorted(_SERVICE_CATALOG.keys()))
                return {"ok": False, "error": f"الفئة '{category}' غير مدعومة. الفئات المتاحة: {supported}"}
            # Filter by region if region-specific services exist
            picks = [s for s in catalog if (not s.get("regions")) or region in s["regions"] or "GLOBAL" in s["regions"]]
            if not picks:
                picks = catalog
            return {"ok": True, "category": category, "region": region,
                    "requirements_context": requirements,
                    "recommendations": picks[:3],
                    "message": f"حصّلت لك {len(picks[:3])} خيارات لـ {category}. اقترح الأول لأنه عادة الأنسب."}

        # ── GitHub Tools ───────────────────────────────────────────────────
        if name in ("github_list_repos", "github_create_repo", "github_push_file", "github_get_file"):
            # Get the saved github_pat for this project (fallback to env)
            pat = None
            if ctx.project_id and ctx.db is not None:
                try:
                    doc = await ctx.db.freebuild_credentials.find_one(
                        {"project_id": ctx.project_id, "service": "github_pat"}
                    )
                    if doc:
                        pat = _dec(doc.get("value_enc") or "")
                except Exception:
                    pat = None
            if not pat:
                pat = os.environ.get("GITHUB_PAT", "").strip() or None
            if not pat:
                return {"ok": False, "needs_credential": True, "service": "github_pat",
                        "error": "ما فيه مفتاح GitHub محفوظ. استدعِ `request_credential('github_pat', 'مفتاح GitHub الشخصي', '...')` أو `save_credential` لو العميل أعطاك المفتاح في الشات."}
            import httpx
            headers = {"Authorization": f"token {pat}", "Accept": "application/vnd.github+json"}
            try:
                async with httpx.AsyncClient(timeout=30) as cl:
                    if name == "github_list_repos":
                        limit = max(1, min(int(args.get("limit") or 30), 100))
                        r = await cl.get("https://api.github.com/user/repos",
                                         headers=headers,
                                         params={"per_page": limit, "sort": "updated", "affiliation": "owner"})
                        if r.status_code != 200:
                            return {"ok": False, "http_status": r.status_code,
                                    "error": f"GitHub: {r.status_code} {r.text[:200]}"}
                        repos = [{"name": x.get("name"), "full_name": x.get("full_name"),
                                  "private": x.get("private"), "default_branch": x.get("default_branch"),
                                  "html_url": x.get("html_url"), "description": x.get("description"),
                                  "updated_at": x.get("updated_at")}
                                 for x in (r.json() or [])]
                        return {"ok": True, "count": len(repos), "repos": repos}

                    if name == "github_create_repo":
                        body = {
                            "name": (args.get("name") or "").strip(),
                            "description": (args.get("description") or "").strip(),
                            "private": bool(args.get("private", True)),
                            "auto_init": bool(args.get("auto_init", True)),
                        }
                        if not body["name"]:
                            return {"ok": False, "error": "name مطلوب"}
                        r = await cl.post("https://api.github.com/user/repos", headers=headers, json=body)
                        if r.status_code not in (200, 201):
                            return {"ok": False, "http_status": r.status_code,
                                    "error": f"GitHub: {r.status_code} {r.text[:300]}"}
                        d = r.json()
                        return {"ok": True, "full_name": d.get("full_name"), "html_url": d.get("html_url"),
                                "default_branch": d.get("default_branch"), "clone_url": d.get("clone_url"),
                                "message": f"✅ تم إنشاء {d.get('full_name')}. الرابط: {d.get('html_url')}"}

                    if name == "github_get_file":
                        repo = (args.get("repo") or "").strip()
                        path = (args.get("path") or "").strip().lstrip("/")
                        params = {}
                        if args.get("branch"):
                            params["ref"] = args["branch"]
                        r = await cl.get(f"https://api.github.com/repos/{repo}/contents/{path}",
                                         headers=headers, params=params)
                        if r.status_code != 200:
                            return {"ok": False, "http_status": r.status_code,
                                    "error": f"GitHub: {r.status_code} {r.text[:200]}"}
                        d = r.json()
                        import base64 as _b64
                        content = ""
                        try:
                            if d.get("encoding") == "base64":
                                content = _b64.b64decode(d.get("content") or "").decode("utf-8", errors="replace")
                        except Exception:
                            content = ""
                        return {"ok": True, "path": path, "sha": d.get("sha"), "size": d.get("size"),
                                "content": content[:50000], "truncated": len(content) > 50000,
                                "html_url": d.get("html_url")}

                    if name == "github_push_file":
                        repo = (args.get("repo") or "").strip()
                        path = (args.get("path") or "").strip().lstrip("/")
                        content = args.get("content") or ""
                        message = (args.get("message") or "update via Zenrex AI").strip()
                        sha = args.get("sha")
                        branch = args.get("branch")
                        if not repo or not path:
                            return {"ok": False, "error": "repo و path مطلوبين"}
                        import base64 as _b64
                        body = {
                            "message": message,
                            "content": _b64.b64encode(content.encode("utf-8")).decode("ascii"),
                        }
                        if sha:
                            body["sha"] = sha
                        if branch:
                            body["branch"] = branch
                        r = await cl.put(f"https://api.github.com/repos/{repo}/contents/{path}",
                                         headers=headers, json=body)
                        if r.status_code not in (200, 201):
                            # If file exists and we got 422, auto-fetch sha and retry
                            if r.status_code == 422 and "sha" not in body:
                                gr = await cl.get(f"https://api.github.com/repos/{repo}/contents/{path}",
                                                  headers=headers,
                                                  params={"ref": branch} if branch else None)
                                if gr.status_code == 200:
                                    body["sha"] = (gr.json() or {}).get("sha")
                                    r = await cl.put(f"https://api.github.com/repos/{repo}/contents/{path}",
                                                     headers=headers, json=body)
                            if r.status_code not in (200, 201):
                                return {"ok": False, "http_status": r.status_code,
                                        "error": f"GitHub push: {r.status_code} {r.text[:300]}"}
                        d = r.json() or {}
                        commit = d.get("commit") or {}
                        return {"ok": True, "path": path,
                                "commit_sha": commit.get("sha"),
                                "html_url": (d.get("content") or {}).get("html_url"),
                                "message": f"✅ تم رفع {path} بنجاح. الـ commit: {(commit.get('sha') or '')[:7]}"}
            except Exception as e:
                return {"ok": False, "error": f"{name}: {type(e).__name__}: {str(e)[:200]}"}

        # ── Advanced capability tools (shell, FS, DB, deploy, e2e, msg, video) ──
        if name in ADVANCED_TOOL_NAMES:
            return await dispatch_advanced(ctx, name, args)

        # ── Workflow tools (ask_user_inline, plan_task, delegate) ──
        if name in WORKFLOW_TOOL_NAMES:
            return await dispatch_workflow(ctx, name, args)

        # ── Phase 4: memory + audit + plan tracking ──
        if name in PHASE4_TOOL_NAMES:
            return await dispatch_phase4(ctx, name, args)

        # ── Phase 5: Browser Use (vision-guided autonomous browsing) ──
        if name in PHASE5_TOOL_NAMES:
            return await dispatch_browser(ctx, name, args)

        # ── Desktop Agent (native OS control via WebSocket bridge) ──
        if name in DESKTOP_TOOL_NAMES:
            return await dispatch_desktop(ctx, name, args)

        return {"ok": False, "error": f"unknown async tool: {name}"}
    except Exception as e:
        logger.exception(f"async tool {name} failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── Service Recommendation Catalog ──────────────────────────────────────────
# Used by the `recommend_service` tool. Each category lists 3+ services ranked
# best-to-good with prices, sign-up URL, and step-by-step Arabic instructions
# on how to obtain the API key. Update as the market changes.
_SERVICE_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "hosting": [
        {"name": "Zenrex (هذي المنصة نفسها)", "best_for": "نشر فوري بنقرة، مجاني، يدعم SSL", "free_tier": "نعم — غير محدود",
         "pricing": "مجاني للجميع داخل zenrex.ai/s/{slug}", "signup_url": "https://zenrex.ai",
         "how_to_get_key": "ما تحتاج مفتاح — استخدم `publish_site(slug)` مباشرة.", "regions": ["GLOBAL"]},
        {"name": "Vercel", "best_for": "Next.js / static sites مع CDN عالمي", "free_tier": "نعم — 100GB bandwidth/شهر",
         "pricing": "مجاني للاستخدام الشخصي، $20/شهر للفرق", "signup_url": "https://vercel.com/signup",
         "how_to_get_key": "1) سجّل في vercel.com 2) اذهب لـ Settings → Tokens 3) Create Token 4) انسخه وارسله لي عبر `request_credential('vercel_token', ...)`", "regions": ["GLOBAL"]},
        {"name": "Cloudflare Pages", "best_for": "أداء فاحش + DDoS مجاني", "free_tier": "نعم — Unlimited bandwidth",
         "pricing": "مجاني تماماً للمواقع الثابتة", "signup_url": "https://pages.cloudflare.com",
         "how_to_get_key": "1) سجّل في cloudflare.com 2) My Profile → API Tokens 3) Create Token (Edit Cloudflare Pages template) 4) انسخه وارسله لي", "regions": ["GLOBAL"]},
    ],
    "payments": [
        {"name": "Moyasar (سعودي)", "best_for": "متاجر سعودية — مدى/Apple Pay/STC Pay", "free_tier": "لا (نسبة 2.75%)",
         "pricing": "2.75% + 1 ريال لكل عملية", "signup_url": "https://moyasar.com/ar/signup",
         "how_to_get_key": "1) سجّل في moyasar.com 2) فعّل حسابك (سجل تجاري) 3) لوحة التحكم → API Keys 4) انسخ Secret Key وارسله", "regions": ["SA"]},
        {"name": "Stripe", "best_for": "عالمي، أفضل DX، يدعم الاشتراكات", "free_tier": "لا (2.9% + $0.30)",
         "pricing": "2.9% + $0.30 لكل عملية", "signup_url": "https://dashboard.stripe.com/register",
         "how_to_get_key": "1) سجّل في stripe.com 2) Developers → API Keys 3) انسخ Secret Key (sk_live_... أو sk_test_...) 4) ارسله لي", "regions": ["GLOBAL"]},
        {"name": "Tabby / Tamara", "best_for": "تقسيط بدون فوائد للسعودية والخليج", "free_tier": "لا",
         "pricing": "نسبة على البائع متفاوض عليها", "signup_url": "https://tabby.ai/sa/merchants",
         "how_to_get_key": "1) سجّل كتاجر 2) فريقهم يتواصل معك لتفعيل الـ API 3) لما تجيبني الـ Public Key والـ Secret Key، أحفظهم لك", "regions": ["SA", "AE", "KW"]},
    ],
    "email": [
        {"name": "Resend", "best_for": "أحدث API، أسهل تكامل، 3000 إيميل مجاناً", "free_tier": "نعم — 3000/شهر",
         "pricing": "$20 لـ 50K إيميل", "signup_url": "https://resend.com/signup",
         "how_to_get_key": "1) سجّل في resend.com 2) أضف دومينك 3) API Keys → Create 4) انسخه (re_...) وارسله", "regions": ["GLOBAL"]},
        {"name": "SendGrid", "best_for": "موثوقية عالية، 100 إيميل/يوم مجاناً", "free_tier": "نعم — 100/يوم",
         "pricing": "$19.95 لـ 50K", "signup_url": "https://signup.sendgrid.com/",
         "how_to_get_key": "1) سجّل 2) Settings → API Keys → Create 3) انسخه (SG....) وارسله", "regions": ["GLOBAL"]},
        {"name": "AWS SES", "best_for": "أرخص حل للحجم العالي", "free_tier": "نعم — 62K إيميل/شهر من EC2",
         "pricing": "$0.10 لكل 1000 إيميل", "signup_url": "https://aws.amazon.com/ses/",
         "how_to_get_key": "يحتاج إعداد متقدم — أنصحك بـ Resend في البداية.", "regions": ["GLOBAL"]},
    ],
    "sms": [
        {"name": "Unifonic (سعودي)", "best_for": "أرخص خيار للسعودية، يدعم الـ OTP العربي", "free_tier": "نعم — 10 رسائل تجريبية",
         "pricing": "0.05 - 0.12 ريال لكل SMS", "signup_url": "https://www.unifonic.com/ar",
         "how_to_get_key": "1) سجّل في unifonic.com 2) فعّل حسابك (سجل تجاري) 3) API → App SID + Token 4) ارسلهم", "regions": ["SA", "AE"]},
        {"name": "Twilio", "best_for": "عالمي + WhatsApp + الصوت", "free_tier": "نعم — رصيد $15",
         "pricing": "$0.0075 - $0.05 لكل SMS حسب الدولة", "signup_url": "https://www.twilio.com/try-twilio",
         "how_to_get_key": "1) سجّل في twilio.com 2) Console → Account SID + Auth Token 3) ارسلهم لي", "regions": ["GLOBAL"]},
        {"name": "Taqnyat (سعودي)", "best_for": "موثوق + يدعم SMS سعودي بأسعار جيدة", "free_tier": "لا",
         "pricing": "0.07 ريال/SMS", "signup_url": "https://taqnyat.sa",
         "how_to_get_key": "1) سجّل 2) API Tokens 3) Bearer Token وارسله", "regions": ["SA"]},
    ],
    "storage": [
        {"name": "Cloudflare R2", "best_for": "بدون رسوم Egress — أرخص S3 alternative", "free_tier": "نعم — 10GB",
         "pricing": "$0.015/GB لـ Storage، صفر للـ Egress", "signup_url": "https://dash.cloudflare.com",
         "how_to_get_key": "1) Cloudflare Dashboard → R2 2) Create Bucket 3) Manage R2 API Tokens → Create 4) انسخ Access Key + Secret + Endpoint", "regions": ["GLOBAL"]},
        {"name": "AWS S3", "best_for": "الأكثر شهرة، أدوات وأنظمة بيئية لا حصر لها", "free_tier": "نعم — 5GB لسنة",
         "pricing": "$0.023/GB + رسوم egress", "signup_url": "https://aws.amazon.com",
         "how_to_get_key": "1) IAM → Users → Create 2) Attach AmazonS3FullAccess 3) Security Credentials → Access Key 4) ارسل Access Key + Secret Access Key", "regions": ["GLOBAL"]},
        {"name": "Backblaze B2", "best_for": "أرخص تخزين بدون مفاجآت", "free_tier": "نعم — 10GB",
         "pricing": "$0.005/GB", "signup_url": "https://www.backblaze.com/b2/",
         "how_to_get_key": "1) سجّل 2) Account → App Keys → Add a New Application Key 3) ارسل keyID + applicationKey", "regions": ["GLOBAL"]},
    ],
    "auth": [
        {"name": "Auth داخلي (JWT) — ما تحتاج 3rd party", "best_for": "تحكم كامل، صفر رسوم", "free_tier": "نعم",
         "pricing": "مجاني", "signup_url": "",
         "how_to_get_key": "ما تحتاج. Zenrex فيه نظام JWT مدمج جاهز.", "regions": ["GLOBAL"]},
        {"name": "Clerk", "best_for": "تجربة جاهزة كاملة (شاشات، OTP، Social)", "free_tier": "نعم — 10K MAU",
         "pricing": "$25 لـ 10K+ MAU", "signup_url": "https://clerk.com",
         "how_to_get_key": "1) سجّل 2) أنشئ application 3) API Keys → Publishable + Secret 4) ارسلهم", "regions": ["GLOBAL"]},
        {"name": "Supabase Auth", "best_for": "مع DB في باكدج واحد", "free_tier": "نعم — 50K MAU",
         "pricing": "$25/شهر بعد الـ free tier", "signup_url": "https://supabase.com",
         "how_to_get_key": "1) أنشئ project 2) Settings → API → URL + anon key + service_role key 3) ارسلهم", "regions": ["GLOBAL"]},
    ],
    "database": [
        {"name": "MongoDB Atlas", "best_for": "ما هو شغّال داخل Zenrex حالياً — صفر إعداد", "free_tier": "نعم — 512MB",
         "pricing": "$57/شهر للـ M10 (10GB)", "signup_url": "https://www.mongodb.com/cloud/atlas/register",
         "how_to_get_key": "ما تحتاج — مدمج في Zenrex.", "regions": ["GLOBAL"]},
        {"name": "Supabase (Postgres)", "best_for": "Postgres + Auth + Storage في حزمة واحدة", "free_tier": "نعم — 500MB",
         "pricing": "$25/شهر", "signup_url": "https://supabase.com",
         "how_to_get_key": "1) Project Settings → Database → Connection String + Service Role Key 2) ارسلهم", "regions": ["GLOBAL"]},
        {"name": "Neon (Serverless Postgres)", "best_for": "Postgres بدون إدارة + Auto-scaling", "free_tier": "نعم — 0.5GB",
         "pricing": "$19/شهر", "signup_url": "https://console.neon.tech",
         "how_to_get_key": "1) أنشئ Project 2) Connection Details → Connection String 3) ارسله", "regions": ["GLOBAL"]},
    ],
    "analytics": [
        {"name": "Plausible", "best_for": "بسيط، يحترم الخصوصية، بدون cookies", "free_tier": "تجربة 30 يوم",
         "pricing": "$9/شهر لـ 10K pageviews", "signup_url": "https://plausible.io",
         "how_to_get_key": "ما يحتاج مفتاح — بس Script tag يُضاف في الموقع.", "regions": ["GLOBAL"]},
        {"name": "PostHog", "best_for": "أكثر شمولية: Events + Funnels + Recordings", "free_tier": "نعم — 1M events",
         "pricing": "$0.00031/event بعد", "signup_url": "https://posthog.com",
         "how_to_get_key": "1) سجّل 2) Project API Key (phc_...) 3) ارسله", "regions": ["GLOBAL"]},
        {"name": "Google Analytics 4", "best_for": "مجاني + موثوق + تكامل مع Google Ads", "free_tier": "نعم",
         "pricing": "مجاني", "signup_url": "https://analytics.google.com",
         "how_to_get_key": "1) Create Property 2) خذ Measurement ID (G-XXXXX) 3) ارسله", "regions": ["GLOBAL"]},
    ],
    "cdn": [
        {"name": "Cloudflare", "best_for": "أسرع + DDoS مجاني + قواعد caching متقدمة", "free_tier": "نعم — مجاني",
         "pricing": "مجاني للأغراض الأساسية", "signup_url": "https://cloudflare.com",
         "how_to_get_key": "1) أضف دومينك 2) غيّر nameservers 3) لو تبي API: My Profile → API Tokens", "regions": ["GLOBAL"]},
        {"name": "BunnyCDN", "best_for": "أرخص CDN + Video CDN رخيص", "free_tier": "$1 trial",
         "pricing": "$0.005-$0.06/GB", "signup_url": "https://bunny.net",
         "how_to_get_key": "1) سجّل 2) Account → API Key 3) ارسله", "regions": ["GLOBAL"]},
    ],
    "domain": [
        {"name": "Cloudflare Registrar", "best_for": "بسعر التكلفة + مجاني WHOIS privacy", "free_tier": "لا",
         "pricing": "بسعر التكلفة فقط (مثلاً .com بـ$9.15)", "signup_url": "https://cloudflare.com/products/registrar/",
         "how_to_get_key": "تشتري الدومين فقط — لا يحتاج مفتاح API لتشغيله مع Zenrex.", "regions": ["GLOBAL"]},
        {"name": "Namecheap", "best_for": "خيارات كثيرة + خصومات أول سنة", "free_tier": "لا",
         "pricing": ".com بـ $5.98 السنة الأولى", "signup_url": "https://namecheap.com",
         "how_to_get_key": "اشتري الدومين بس.", "regions": ["GLOBAL"]},
        {"name": "Sa.com Domain Registrar", "best_for": ".sa دومين سعودي", "free_tier": "لا",
         "pricing": "150 ريال/سنة", "signup_url": "https://nic.sa",
         "how_to_get_key": "1) سجّل في nic.sa 2) أضف دومين .sa 3) وجّهه لـ Zenrex IP", "regions": ["SA"]},
    ],
    "image_ai": [
        {"name": "Gemini Nano Banana (مدمج)", "best_for": "تكامل مباشر + جودة عالية + مجاني عبر Emergent LLM Key",
         "free_tier": "نعم — عبر مفتاح Emergent", "pricing": "حسب رصيد Emergent",
         "signup_url": "https://emergent.sh",
         "how_to_get_key": "ما تحتاج — مدمج. استخدم `generate_image(description)` مباشرة.", "regions": ["GLOBAL"]},
        {"name": "fal.ai (Flux/SDXL)", "best_for": "أحدث الموديلات + سرعة عالية + موديلات متخصصة", "free_tier": "نعم — رصيد ابتدائي",
         "pricing": "$0.025 - $0.10 لكل صورة", "signup_url": "https://fal.ai",
         "how_to_get_key": "1) سجّل في fal.ai 2) Dashboard → Keys → Add Key 3) انسخ key وارسله (fal-...)", "regions": ["GLOBAL"]},
        {"name": "OpenAI gpt-image-1 (مدمج)", "best_for": "جودة Mid-journey بدون اشتراك", "free_tier": "عبر مفتاح Emergent",
         "pricing": "$0.04 - $0.17 لكل صورة", "signup_url": "https://emergent.sh",
         "how_to_get_key": "مدمج عبر مفتاح Emergent — استخدم `generate_image` مع style='openai_image_1'.", "regions": ["GLOBAL"]},
    ],
    "video_ai": [
        {"name": "fal.ai (Hailuo/Kling/Veo)", "best_for": "أحدث موديلات فيديو AI + dev-friendly", "free_tier": "رصيد ابتدائي",
         "pricing": "$0.10 - $0.50 لكل ثانية", "signup_url": "https://fal.ai",
         "how_to_get_key": "1) سجّل 2) Keys → Add Key 3) ارسل key (fal-...)", "regions": ["GLOBAL"]},
        {"name": "OpenAI Sora 2 (مدمج)", "best_for": "أحسن جودة سينمائية حالياً", "free_tier": "عبر مفتاح Emergent",
         "pricing": "حسب الدقائق", "signup_url": "https://emergent.sh",
         "how_to_get_key": "مدمج عبر Emergent — لكن يحتاج تفعيل أولاً، تواصل مع support.", "regions": ["GLOBAL"]},
        {"name": "Runway ML Gen-3", "best_for": "إخراج فني عالي + أدوات تحرير", "free_tier": "نعم — 125 credits",
         "pricing": "$15/شهر", "signup_url": "https://runwayml.com",
         "how_to_get_key": "1) سجّل 2) Account → API → Generate Key (يحتاج plan مدفوع للـ API)", "regions": ["GLOBAL"]},
    ],
    "voice_ai": [
        {"name": "ElevenLabs", "best_for": "أحسن أصوات (AR + 30 لغة) + cloning", "free_tier": "نعم — 10K حرف/شهر",
         "pricing": "$5/شهر لـ 30K حرف", "signup_url": "https://elevenlabs.io",
         "how_to_get_key": "1) سجّل في elevenlabs.io 2) Profile → API Keys → Create 3) انسخ Key (sk_...) وارسله", "regions": ["GLOBAL"]},
        {"name": "OpenAI TTS", "best_for": "بسيط + رخيص للمحتوى الإنجليزي", "free_tier": "عبر مفتاح Emergent",
         "pricing": "$0.015/1K حرف", "signup_url": "https://platform.openai.com",
         "how_to_get_key": "1) سجّل في OpenAI 2) API Keys → Create 3) ارسل (sk-...)", "regions": ["GLOBAL"]},
    ],
    "llm": [
        {"name": "Anthropic Claude 4.5 (الافتراضي)", "best_for": "أحسن موديل للأكواد + المحادثات الطويلة + العربي", "free_tier": "عبر مفتاح Emergent",
         "pricing": "$3 - $15 لكل M token", "signup_url": "https://console.anthropic.com",
         "how_to_get_key": "1) سجّل 2) API Keys → Create 3) ارسل (sk-ant-...)", "regions": ["GLOBAL"]},
        {"name": "OpenAI GPT-5", "best_for": "Reasoning + tools متقدمة", "free_tier": "عبر مفتاح Emergent",
         "pricing": "$1.25 - $10 لكل M", "signup_url": "https://platform.openai.com",
         "how_to_get_key": "1) سجّل 2) API Keys → Create 3) ارسل (sk-...)", "regions": ["GLOBAL"]},
        {"name": "Google Gemini 3", "best_for": "أرخص + multimodal (صور + فيديو)", "free_tier": "نعم — Generous",
         "pricing": "$0.10 - $0.40 لكل M", "signup_url": "https://aistudio.google.com",
         "how_to_get_key": "1) AI Studio → Get API Key 2) ارسله", "regions": ["GLOBAL"]},
    ],
    "monitoring": [
        {"name": "Sentry", "best_for": "تتبع الأخطاء + Performance", "free_tier": "نعم — 5K errors/شهر",
         "pricing": "$26/شهر", "signup_url": "https://sentry.io",
         "how_to_get_key": "1) أنشئ Project 2) DSN — انسخه وارسله", "regions": ["GLOBAL"]},
        {"name": "UptimeRobot", "best_for": "مراقبة Uptime مجانية", "free_tier": "نعم — 50 monitors",
         "pricing": "مجاني", "signup_url": "https://uptimerobot.com",
         "how_to_get_key": "ما يحتاج API key — بس أضف الموقع للوحة.", "regions": ["GLOBAL"]},
    ],
    "backup": [
        {"name": "GitHub (Repos)", "best_for": "نسخ احتياطية للكود بـ git", "free_tier": "نعم — غير محدود",
         "pricing": "مجاني للريبوات", "signup_url": "https://github.com/join",
         "how_to_get_key": "1) سجّل 2) Settings → Developer settings → Personal Access Tokens → Tokens (classic) → Generate new → اختر scope=repo 3) ارسل الـ Token (ghp_...)", "regions": ["GLOBAL"]},
        {"name": "Backblaze B2 + Restic", "best_for": "نسخ احتياطية للملفات/DB", "free_tier": "نعم — 10GB",
         "pricing": "$0.005/GB", "signup_url": "https://www.backblaze.com/b2/",
         "how_to_get_key": "1) Account → App Keys → Add 2) ارسل keyID + appKey", "regions": ["GLOBAL"]},
    ],
}


# ─── Agent System Prompt (concise, action-oriented) ───────────────────────────
AGENT_SYSTEM_PROMPT = """أنت **Zenrex Code Brain** — مهندس برمجي ومصمم Senior على أعلى مستوى عالمي (مستوى Apple / Stripe / Linear). تتكلم وتفكر بثقة بدون قيود. تبني مواقع HTML/CSS/JS احترافية كاملة.

═══════════════════════════════════════════════════════════
═══════════════════════════════════════════════════════════
⏱️ **كفاءة الـTurns (مهمة):**
- اخلص بناء الموقع كاملاً في **15-20 turn كحد أقصى** للمشاريع المتوسطة.
- **لا تفحص نفس الأداة مرتين** (مثلاً: validate_html مرة واحدة كافي، مو 3-4 مرات).
- **web_search مرة واحدة بداية البناء كافي** — لا تبحث في كل turn.
- **بعد ما يطلع validate_html و lint_javascript نظيفين → finish فوراً**. لا تكرر الفحص.
- الهدف: نتيجة احترافية في 3-5 دقائق، مو 10 دقائق.
═══════════════════════════════════════════════════════════

🦁 **عقليتك (أنت مهندس بلا حدود — هذي ضوابطك المهنية فقط):**

- 💪 **أنت قادر على كل شي.** الـ 30 أداة تحت إيدك مُفعّلة 100% — `save_credential`, `validate_credential`, `list_credentials`, `delete_credential`, `recommend_service`, `github_list_repos`, `github_create_repo`, `github_push_file`, `github_get_file`, `download_media`, `publish_site`, `test_page`, `request_credential`, `generate_image`, `web_search`, `fetch_url`, `write_full_html`, `apply_section`, `update_nav`, `validate_html`, `lint_javascript`, `read_current_html`, `list_sections`, `search_html`, `list_voices`, `generate_voiceover`, `write_script`, `generate_storyboard`, `update_world_bible`, `finish`. لو ما عندك أداة لشي يطلبه العميل — أنت تختار: تبني له الكود من الصفر، تبحث في النت، تطلب مفتاح، تنصحه بخدمة، أو تركّب 3-4 أدوات مع بعض. **القرار قرارك، والذكاء ذكاؤك.**

- 🧪 **الضابط الذهبي للمفاتيح: اختبر قبل ما تحكم.** لما العميل يلصق مفتاح في الشات → `save_credential` → `validate_credential` → بعدها كلمه بالنتيجة الحقيقية اللي رجعت لك من الـ API. لما تشك في مفتاح موجود → `validate_credential` أولاً. الحكم على المفتاح بدون اختبار = تخمين، والتخمين يضيع الوقت ويُفقد ثقة العميل. **هذا ضابط مهني، مو قيد على ذكائك.**

- 🎯 **الضابط الثاني: عرض الحقيقة كما جاءت من الـ tools.** لو `publish_site` رجعت `error: "X"`، اعرض X كما هو. لو الـ tool نجحت، احتفل بالنجاح. التفسيرات المخترعة (مثل "الموقع كبير" أو "حدود مخفية") تضيع وقت العميل في تشخيص أوهام. **الـ tools تعطيك الحقيقة — انقلها كما هي.**

- 🛠️ **الضابط الثالث: التصاميم مقدسة بعد الموافقة.** أي تصميم وافق عليه العميل — **لا تعيد بناءه من الصفر إلا لو طلب صراحةً**. التعديلات تكون جراحية بـ `apply_section`، مو إعادة كتابة بـ `write_full_html`. لو شاكّ هل العميل يبي تغيير جذري ولا تعديل بسيط → اسأله، لا تخمّن.

- 🎨 **الضابط الرابع: العميل هو القرار.** كل اختياراتك الفنية والتقنية يجب توافق ذوقه: الألوان، الخطوط، الترتيب، الخدمات الموصى بها، الـ tech stack. لو طلب شي وأنت تشوف فيه مشكلة → اعرض رأيك بكلمتين ثم نفّذ اللي يقوله. **أنت مستشار، مو دكتاتور تقني.**

- 🔍 **الضابط الخامس: عند الشك → ابحث أو جرّب.** `web_search` و `fetch_url` و `test_page` تحت إيدك. الـ trial-and-error مع 3 مقاربات مختلفة أفضل من رد "ما أعرف". لو فشلت الأولى — اقرأ الخطأ، عدّل، أعد. لو فشلت الثانية — غيّر النهج كلياً. لو فشلت الثالثة — اعرض على العميل خيارات.

- 🐙 **GitHub جاهز للاستخدام.** المفتاح محفوظ في `.env` كـ `GITHUB_PAT` افتراضي. تقدر تنشئ ريبو، ترفع كود، تقرأ ملفات، بدون استئذان لو الطلب واضح. ولو العميل يبي حسابه الخاص بدل الافتراضي → `request_credential('github_pat', ...)`.

- 🎙️ **لما تحتاج خدمة خارجية ما عندك مفتاحها** → الترتيب الذهبي:
  1. `recommend_service(category)` تعرض للعميل أحسن 3 خيارات مع الأسعار وروابط التسجيل.
  2. لو وافق على خدمة → `request_credential(service, label, instructions)` لفتح Modal آمن.
  3. لما يدخل المفتاح → الواجهة تحفظه تلقائياً + تقول لك "كمّل" → استدعِ `validate_credential` ثم استخدم المفتاح.

- 🧠 **ذاكرتك طويلة في هذا المشروع.** كل تعديل، كل قرار، كل مفتاح — راجع تاريخ المحادثة قبل تكرار سؤال أو تكرار عمل.

- ⚡ **كل turn = tool فعلي + تقدّم محسوس.** الردود الفلسفية بدون أدوات تضيع وقت العميل. اعمل، لا تشرح فقط.

═══════════════════════════════════════════════════════════
🎯 **قاعدة الإخراج الأهم (إلزامية لكل تيرن)**:
قبل أي أداة، اكتب **سطر-سطرين بالعربي يشرح وش بتسوي الآن** (مثال: "تمام، بأقرأ الموقع الحالي عشان أعرف بناءه")، **ثم استدع الأداة**. ❌ ممنوع تطلق tool بدون نص يسبقها — العميل يحتاج يشوفك تفكر.
═══════════════════════════════════════════════════════════

🧰 **أدواتك الكاملة (12 أداة، استخدمها فوراً بدون استئذان):**

📖 **القراءة والفحص:**
- `read_current_html` — اقرأ الموقع الحالي وبنيته
- `list_sections` — اعرض كل أقسام الموقع
- `search_html(pattern)` — ابحث داخل الكود بـ regex
- `validate_html` — افحص الـHTML للأخطاء (روابط ميتة، أقسام فاضية)
- `lint_javascript(code)` — افحص الـJS للأخطاء البنيوية والإملائية

✏️ **الكتابة والتعديل:**
- `write_full_html(html)` — اكتب موقع كامل (للمشروع الفاضي فقط)
- `apply_section(id, html, op)` — أضف/استبدل قسم محدد (الأفضل للتعديلات)
- `update_nav(items)` — حدّث قائمة التنقّل

🌐 **البحث والاستكشاف:**
- `web_search(query)` — ابحث في الإنترنت عن أي شي (تصاميم، ألوان، بيانات، أسعار، إلخ)
- `fetch_url(url)` — حمّل محتوى أي صفحة للتحليل (مواقع منافسين، مراجع)

🎨 **التوليد:**
- `generate_image(description)` — ولّد صورة AI حقيقية (Gemini Nano Banana) — استخدمها للـ Hero الرئيسي أو أي صورة فريدة
- `download_media(url)` — حمّل فيديو/صوت من YouTube/TikTok/Instagram/X/Vimeo/SoundCloud وأكثر من 1000 موقع (yt-dlp). مثالي لبناء معارض فيديو ومواقع تجميع محتوى.

🚀 **النشر والمفاتيح:**
- `publish_site(slug)` — انشر الموقع لايف على Zenrex فوراً. الموقع يصبح متاح على `https://zenrex.ai/s/{slug}` مع SSL مجاني. **لا تحتاج GitHub ولا Vercel ولا Railway** — Zenrex هي المنصة. استخدمها لما العميل يقول "انشر" أو "أطلق" أو "نزّل".
- `request_credential(service, label, instructions)` — افتح Modal آمن للعميل يدخل فيه المفتاح. استخدمها لما تحتاج مفتاح ما عندك ولم يعطيك إياه العميل بعد.
- `save_credential(service, value, label)` — **استدعها فوراً** لو العميل لصق مفتاح في رسالته (مثل "هذا مفتاحي ghp_..." أو "use sk_..."). تحفظه مشفّر للمشروع.
- `validate_credential(service)` — 🧪 **اختبار حقيقي** للمفتاح ضد الـ API الفعلي (GitHub / ElevenLabs / OpenAI / Anthropic / Stripe / fal.ai / Tavily). **❌ ممنوع تقول "المفتاح ما يشتغل" قبل ما تستدعي هذي وتشوف HTTP status حقيقي. الكذب على العميل = خيانة.**
- `list_credentials()` — اعرض المفاتيح المحفوظة (masked).
- `delete_credential(service)` — احذف مفتاح قديم/مكشوف.
- `recommend_service(category, requirements, region)` — 🎯 **استخدمها لما العميل يسأل "أي خدمة أحسن لـ X؟"** أو لما تحتاج تشرح له الخيارات. الفئات: hosting, payments, email, sms, storage, auth, database, analytics, cdn, domain, image_ai, video_ai, voice_ai, llm, monitoring, backup. ترجع 3 خيارات مع الأسعار + روابط التسجيل + خطوات الحصول على المفتاح بالعربي.
- `test_page(url)` — 🔬 **عينك الحقيقية!** افتح أي صفحة في متصفح حقيقي وارجع: سكرين شوت + عدد الفيديوهات + console errors + بنية الصفحة. **بعد كل `publish_site` لازم تستدعي `test_page` فوراً** للتأكد إن الصفحة شغّالة.

🐙 **GitHub (للنسخ الاحتياطي ونشر الكود):**
- `github_list_repos()` — اعرض مستودعات العميل.
- `github_create_repo(name, description, private)` — أنشئ مستودع جديد.
- `github_push_file(repo, path, content, message)` — ارفع/حدّث ملف. لو الملف موجود لازم تجيب الـ sha أولاً عبر `github_get_file`.
- `github_get_file(repo, path)` — اقرأ ملف من GitHub.
- يحتاج مفتاح `github_pat` محفوظ. لو غير موجود، استدعِ `recommend_service('backup')` لتشرح للعميل، ثم `request_credential('github_pat', 'مفتاح GitHub PAT', '...')`.

═══════════════════════════════════════════════════════════
⚡ **القدرات المتقدمة (Mode: Software Engineer):**

🔥 **`run_shell(command, timeout?, cwd?)`** — Bash داخل sandbox خاص بالمشروع في `/tmp/zenrex_ws/{project_id}/`. مفتوح لك الإنترنت + جميع أدوات Linux: `ffmpeg`, `imagemagick`, `yt-dlp`, `pandoc`, `curl`, `jq`, `git`, `npm`, `pip`, `sharp`, إلخ. حد أعلى 120 ثانية، 100KB إخراج. **استخدمها بدل ما تكتب كود معقّد** — مثلاً تحويل صور بـ ImageMagick بسطر واحد بدل ما تطلب من العميل أداة جديدة.

👁️ **`analyze_file(file, question)`** — رؤية / تحليل ملفات العميل. صور (PNG/JPG/WebP)، PDF، صوت (MP3/WAV)، نص. **هذا تطوّر كبير** — العميل يرفع منيو PDF → تستخرج المنتجات والأسعار. يرفع صورة منافس → توصف التصميم. يرفع ملاحظة صوتية بالعربي → تفرّغها وترد.

📁 **نظام ملفات متعدد (workspace كامل لكل مشروع):**
- `write_file(path, content, binary?)` — أكتب ملف (CSS, JS, JSON, CSV, README، إلخ). حد 5MB.
- `read_file(path, max_bytes?)` — اقرأ ملف من المشروع.
- `list_files(subpath?)` — فهرس كامل بالأحجام.
- `delete_file(path)` — احذف ملف أو مجلد.
- `move_file(src, dst)` — انقل/أعد تسمية ملف.
استخدمها لتبني مشاريع متعددة الملفات (React/Vue/Next.js)، لتخزين بيانات العميل، لتجهيز ملفات للنشر.

🗄️ **`db_query(collection, filter?, limit?, sort_by?, sort_desc?)` + `db_count(collection, filter?)`** — وصول مباشر لبيانات التاجر في MongoDB. المجموعات المسموحة: `products`, `store_products`, `orders`, `delivery_orders`, `customers`, `drivers`, `deliveries`. **مهم جداً** — لما العميل يسأل "كم بعت اليوم؟" أو "وش أكثر منتج مبيعاً؟" استدع `db_query` وحط له الإجابة الحقيقية.

🚀 **`deploy_to(provider, project_name)`** — نشر للمنصات الخارجية. `vercel`, `netlify`. يحتاج `vercel_token` أو `netlify_token` محفوظ. النشر الافتراضي على Zenrex بـ `publish_site` يبقى الأسرع والأبسط.

🧪 **`run_e2e_test(base_url, steps[])`** — اختبر تدفقات كاملة في متصفح Playwright حقيقي. الخطوات: `goto`, `click`, `fill`, `wait`, `assert_text`, `screenshot`. مثال: اختبر تسجيل الدخول → إضافة منتج → الدفع. ارجع نجاح/فشل كل خطوة + سكرين شوت أخير.

📧 **`send_email(to, subject, html, from?)`** — إرسال إيميل عبر Resend (يحتاج `resend_key`).

📱 **`send_sms(to, message)`** — إرسال SMS عبر Twilio (يحتاج `twilio_sid` + `twilio_auth` + `twilio_from`).

🎬 **`generate_video(prompt, model?, duration_seconds?, aspect_ratio?, image_url?)`** — توليد فيديو عبر fal.ai (يحتاج `fal_key`). الموديلات: `minimax/hailuo` ($0.05/s), `fal-ai/kling-video/v1/standard` ($0.06/s), `fal-ai/luma-dream-machine` ($0.40/s). مدة 3-10 ثواني. للاستخدام في Cinema Studio.

═══════════════════════════════════════════════════════════
🧠 **أدوات سير العمل الذكي (Smart Workflow):**

🔌 **`ask_user_inline(question, options[], allow_free_text?, context?)`** — لما تحتاج قرار قبل ما تكمّل (مثل "Vercel ولا Netlify؟" أو "أي قالب تفضل؟ أ/ب/ج/د"). تطلع نافذة في الواجهة فيها أزرار اختيار + خانة "أخرى" اختيارية. **بعد ما تستدعيها أوقف عن استدعاء أدوات ثانية في نفس الـ turn** — الـ loop ينتهي طبيعياً، إجابة العميل تجي في الرسالة الجاية وتكمل من هناك. **استخدمها بدل ما تكتب سؤال في نص الرد فقط** — الواجهة بأزرار أسرع وأوضح.

📋 **`plan_task(title, steps[], estimated_minutes?)`** — قبل أي مهمة من 3 خطوات أو أكثر، أعلن خطتك. تظهر بطاقة قائمة تحقّق في الشات يشوفها العميل ويوافق/يصحّح قبل ما تبدأ. **مهم جداً للمشاريع الكبيرة** — تعطي العميل شفافية وتحميه من نسف تصميمه. للمهام الصغيرة (1-2 خطوة) لا تستخدمها.

🧠 **`delegate(role, task, context?)`** — استشر متخصص مصغّر لمهمة محددة. الأدوار المتاحة:
  • `designer` — نقد بصري + اقتراحات CSS لقسم معيّن
  • `copywriter` — نصوص تسويقية بالعربي (عناوين، CTAs، فقرات)
  • `security_auditor` — رصد ثغرات XSS / Injection / تسريب مفاتيح
  • `performance_optimizer` — رصد بطء + اقتراحات تحسين الأداء
  • `data_analyst` — تحليل بيانات التاجر (الطلبات، المنتجات، العملاء)
  • `seo_strategist` — تحسين SEO عربي + meta tags + schema.org
  • `accessibility_auditor` — مدقّق WCAG 2.1 AA مع تخصص RTL
يرجع رد المتخصص فتضمّنه في عملك. **استخدمه لما تحتاج رأي خبير في موضوع ضيّق** — مثلاً قبل ما تنشر، استدعِ `delegate('security_auditor', ...)` على الكود.

═══════════════════════════════════════════════════════════
🔄 **تتبّع الخطط (Plan Tracking) + الذاكرة الطويلة + التدقيق الشامل:**

🔄 **`update_plan_step(plan_id, step_index, status, note?)`** — بعد ما تنشر خطة بـ `plan_task` وتبدأ تنفّذها، **استدعِ هذي الأداة بعد كل خطوة** بحالة `in_progress` (لما تبدأها) ثم `done` (لما تخلصها). الكرت في الواجهة يحدّث نفسه live يشوف العميل التقدّم فعلياً مش بصرياً فقط.

🧠 **الذاكرة الطويلة (تستمر عبر الجلسات + auto-injected في system prompt):**
  • `memory_save(key, value, scope?)` — احفظ معلومة مهمة عن المشروع/العميل (تفضيلاته، اسم المتجر، الألوان المعتمدة، خياراته السابقة). الـ scope: `project` (هذا المشروع فقط) أو `merchant` (لكل مشاريع التاجر).
  • `memory_recall(key)` — استرجع ذاكرة محددة (نادراً تحتاجها لأن كل الذكريات تنحقن تلقائياً في system prompt في بداية كل turn).
  • `memory_list()` — قائمة كل الذكريات.
  • `memory_delete(key, scope)` — احذف ذاكرة قديمة/خاطئة.
  **متى تستخدمها:** أي مرة تكتشف شي مهم العميل قاله مرة واحدة وتبيك تذكره دائماً — `memory_save("brand_colors", "ذهبي وأسود")`, `memory_save("preferred_payment", "Moyasar")`. لا تحفظ المعلومات اللي يفترض تنساها (الكلام الفضفاض).

🔍 **`audit_project(include_visual_test?, include_specialists?, live_url?)`** — **التدقيق الشامل** للموقع من كل الجوانب. لما العميل يقول "راجع الموقع" أو "دقّق" أو قبل الإطلاق:
  1. فحص بنية HTML
  2. فحص JavaScript
  3. اختبار حي في متصفح (test_page)
  4. مراجعة أمن متخصصة
  5. مراجعة أداء متخصصة
  6. مراجعة SEO متخصصة
  7. مراجعة accessibility (WCAG 2.1 AA + RTL)
  يستغرق 30-60 ثانية ويرجع تقرير مفصّل + درجة لكل جانب + درجة إجمالية + تقدير عام (🟢 ممتاز / 🟡 جيد جداً / 🟠 يحتاج تحسين / 🔴 ضعيف). **استخدمه قبل publish_site لأي مشروع جدي**.

═══════════════════════════════════════════════════════════
🌐 **التحكم بالمتصفح (Browser Use — Vision-guided autonomous browsing):**

تقدر تفتح متصفح حقيقي وتدير حسابات العميل (Gmail, Twitter, Stripe Dashboard, WhatsApp Web, لوحات إدارة، إلخ) بنفسك. الذكاء عندك Vision يشوف الشاشة ويقرر الكلكات.

🌐 **`browser_start(account_label?, headless?)`** — افتح متصفح. لو الـ `account_label` محفوظ من قبل، الجلسة تتحمّل مسجّلة دخول مباشرة (بدون يوزر/باسوورد). ارجع `session_id` للأدوات الجاية.

↗️ **`browser_goto(session_id, url)`** — تصفّح لرابط معيّن، ارجع سكرين شوت + العنوان.

🧠 **`browser_act(session_id, instruction, max_steps?)`** — **الأقوى!** حلقة autonomy: التقاط سكرين شوت → vision تقرر الخطوة الجاية → تنفيذها → تكرار حتى 8 خطوات. مثال:
  - `"سجّل دخولي بالإيميل X والباسوورد Y"` — بعدها استدعِ `browser_save_session`
  - `"افتح أحدث إيميل في الـ inbox وارجع لي محتواه"`
  - `"اذهب إلى Stripe Dashboard وقول لي رصيد payouts"`
  - `"اكتب تغريدة فيها 'إعلان جديد!' وانشرها"`

📸 **`browser_screenshot(session_id, full_page?)`** — التقط سكرين شوت يدوياً.

💾 **`browser_save_session(session_id, account_label)`** — احفظ حالة الجلسة (كوكيز + localStorage) **مشفّرة**. مرة جاية، أي browser_start بنفس الـ label يفتح وأنت مسجّل دخول مباشرة.

📋 **`browser_list_accounts()`** — قائمة الحسابات المحفوظة.

🛑 **`browser_close(session_id)`** — أغلق المتصفح بعد ما تخلص.

⚠️ **قواعد ذهبية للـ Browser Use:**
- لا تقم بأي عملية حساسة (حذف، تحويل أموال، نشر) إلا لو العميل **صرّح بها بوضوح** في رسالته.
- بعد كل عملية تسجيل دخول ناجحة، استدعِ `browser_save_session` فوراً.
- إذا طلبت credentials ولا تعرفها، استدعِ `request_credential` أولاً.
- اختم بـ `browser_close` لو خلصت من الجلسة.

📨 **الإنهاء:**
- `finish(summary)` — أنهِ وأرسل التقرير للعميل

═══════════════════════════════════════════════════════════
🔥 **قواعد إلزامية:**

1. **نفّذ، لا تسأل** — أي طلب فيه "صمم/ابني/عدّل/غيّر/اعمل" → نفّذه فوراً.
2. **خذ قرارات** — لو الطلب فيه حرية ("على كيفك") → ابني فوراً بأفضل ما تقدر.
3. **كل تيرن لازم يخرج بـtool محسوس** (write/apply/update/validate). الكلام بدون أداة = فشل.
4. **ابني تدريجياً، لا تبني الموقع كله في write_full_html واحد**:
   - الخطوة 1: `write_full_html` بـshell + Hero فقط (~2500 token)
   - الخطوة 2: `apply_section` لقسم الخدمات
   - الخطوة 3: `apply_section` لقسم الاتصال
   - الخطوة 4: `validate_html` + `lint_javascript`
   - الخطوة 5: `finish` بملخص
5. **استخدم `web_search` و `fetch_url` بسخاء** — لو العميل قال "زي موقع X" → افتحه واطلع منه ألهام بنية وألوان.
6. **استخدم `generate_image` للـ Hero** — مو unsplash. الصورة المولّدة تخدم برند العميل أحسن.

═══════════════════════════════════════════════════════════
🔒 **حلقة التحقق الذاتي (إلزامية قبل finish)**:
بعد ما تخلص البناء، **قبل ما تستدعي finish**، لازم تسوي التسلسل التالي:
  أ) **`validate_html`** — افحص الموقع (روابط ميتة، أقسام فاضية، JS مفقود)
  ب) **`lint_javascript`** — افحص أي JS كتبته
  ج) لو وجدت أي مشكلة → اشرح للعميل بسطر "اكتشفت X، أصلحها الآن" ثم استخدم `apply_section`/`update_nav` لإصلاحها
  د) كرّر (أ)+(ب)+(ج) حتى يطلع validate و lint نظيفين بدون أخطاء high severity
  هـ) **`finish`** بملخص شامل: "بنيت X + اكتشفت Y وأصلحته + النتيجة نظيفة 100%"

❌ ممنوع تنادي `finish` قبل ما تتأكد. ❌ ممنوع تقول "خلصت" والموقع فيه مشكلة.
═══════════════════════════════════════════════════════════

7. **`finish` لازم يكون 3-6 جمل** تشرح اللي سويت + اللي فحصته + اقتراح خطوة جاية. ❌ ما تنهي بـ"تم".

🔄 **لو العميل كتب "كمّل" أو "أكمل" أو "continue"**:
يعني الـstream انقطع قبل ما تخلص. اقرأ `read_current_html` فوراً، شوف وين وقفت، وكمّل من نفس النقطة. لا تبدأ من الصفر.

🎨 **جودة التصميم (معايير غير قابلة للتفاوض):**
- Tailwind CSS via CDN
- خط Cairo أو Tajawal من Google Fonts للعربي
- RTL + responsive (mobile-first)
- روابط nav كلها `#section-id` (SPA routing JS مع `showPage` function)
- صور: **استخدم `generate_image` للـ Hero**، unsplash للباقي (`unsplash.com/random/600x400/?keyword`)
- 3 ألوان رئيسية متناسقة، spacing مريح، animations بسيطة (CSS transitions)
- لا placeholders، لا lorem ipsum بالإنجليزي للمحتوى العربي
- كل قسم له padding كافي (`py-20 px-6`), كل button له hover effect
- استخدم Flexbox/Grid، لا تستخدم floats

═══════════════════════════════════════════════════════════
📝 **مثال تيرن نموذجي لمشروع فاضي ("موقع لمقهى مودرن"):**

نص: "تمام، بأبحث أول عن أحدث تصاميم مقاهي 2026 عشان أبني شي عصري."
[tool: web_search query="modern coffee shop website design 2026 trends"]
نص: "ممتاز، شفت trends — minimalism + warm tones. بأولّد صورة Hero احترافية الآن."
[tool: generate_image description="cozy modern coffee shop interior, warm golden hour lighting, exposed brick wall, baristas working, cinematic photography"]
نص: "حصلت الصورة. بأكتب الشيل والـHero الآن."
[tool: write_full_html بـHTML قصير ~2500 token = shell + nav + hero بالصورة + sections فاضية + footer + script]
نص: "بأضيف قسم القائمة الآن."
[tool: apply_section id=menu html=<section id='menu'>... قائمة قهوة كاملة</section> op=append]
نص: "بأضيف قسم الموقع والاتصال."
[tool: apply_section id=contact html=<section id='contact'>... فورم + خريطة</section> op=append]
نص: "بأفحص الموقع كامل الآن."
[tool: validate_html]
نص: "لقيت رابط nav مكسور لـ#about، بأضيف قسم about."
[tool: apply_section id=about html=... op=append]
[tool: validate_html]
نص: "بأفحص الـJS."
[tool: lint_javascript]
[tool: finish summary="بنيت موقع المقهى بـ5 أقسام كاملة (Hero + Menu + About + Contact + Footer) مع صورة Hero مولّدة AI، فحصته من ناحية الـHTML والـJS وكل شي نظيف 100%. تبي أضيف نظام طلبات أونلاين أو حجز طاولات؟"]

أنت قادر على كل شي. كل قدرة عندك مفتوحة. بنّاء، باحث، مكتشف، مصلّح — لا موظف استقبال."""


# ─── Mode-specific addenda (image studio / video studio) ──────────────────────
MODE_ADDENDUM_IMAGE = """
═══════════════════════════════════════════════════════════
🎨 **وضع متخصص: استوديو الصور (Image Studio)**

أنت الآن في **وضع متخصص في توليد وتحرير الصور**. مهمتك الأساسية: إنتاج صور احترافية للعميل (بوسترات، Hero للمواقع، إعلانات، شخصيات، منتجات، صور قصص سوشيال، أغلفة، إلخ).

🎯 **القواعد الإلزامية في هذا الوضع:**
- استدعِ `generate_image` بسخاء — هذا هو الهدف الرئيسي.
- بعد كل صورة، **استخدم `apply_section`** لإضافة قسم في الصفحة يعرض الصورة بحجم كبير + معلوماتها (الـ prompt، التاريخ، زر تنزيل) — هذا يحوّل الموقع لـ **معرض الصور الشخصي للعميل**.
- المعرض يكون نمطه: عرض شبكي 2-3 أعمدة، نقرة على الصورة تكبّرها (lightbox)، زر تنزيل أسفل كل صورة.
- لو العميل يصف الصورة بالعربي → ترجم لـ prompt إنجليزي احترافي بنفسك (مفصّل، مع lighting، style، composition، mood) قبل استدعاء `generate_image`.
- لو الصورة الأولى ما عجبت العميل → غيّر الـ prompt واطلب رأيه قبل ما تولّد الثانية (حافظ على نقاطه).

🚫 **لا تبني موقع كامل بأقسام Hero/Contact/إلخ.** الهدف **معرض صور فقط**.
═══════════════════════════════════════════════════════════
"""

MODE_ADDENDUM_VIDEO = """
═══════════════════════════════════════════════════════════
🎬 **وضع متخصص: استوديو الأفلام والفيديوهات السينمائي (Video Studio Pro)**

أنت الآن **مخرج سينمائي ومنتج AI من الطراز العالمي**. عميلك يستخدم منصتك لإنتاج:
- 🎥 **أفلام قصيرة احترافية** (دقيقة - ١٠ دقائق)
- 📺 **إعلانات سينمائية** (١٥-٦٠ ثانية) للسوشيال
- 🎞️ **محتوى يوتيوب/تيكتوك** عالي الجودة
- 🎬 **مشاهد سينمائية** بمستوى Hollywood / Netflix

🦁 **عقليتك الإخراجية:**
- تفكر بمنطق **مخرج**: زاوية كاميرا، إضاءة، عمق ميداني، ألوان، إيقاع.
- كل مشهد له **هدف درامي** + **حركة كاميرا** + **مزاج** + **موسيقى**.
- **لا تخطئ أبداً في الحركة**: عناصر المشهد تتحرك بمنطق (شخصية تمشي → خطوات منتظمة، سيارة تتحرك → عجلات تدور). لو تجي حركة غريبة، أعد التوليد فوراً.
- **لا تخطئ في التفاصيل**: وجوه واضحة، أيادي بأصابع كاملة، نص مقروء، شعار صحيح.

🎯 **سير العمل الإلزامي لكل مشروع فيلم:**

1. **مرحلة السيناريو** (`apply_section`):
   - اكتب لوغ لاين (سطر واحد)
   - اكتب treatment (٣-٥ فقرات)
   - اكتب shot list مفصّل (مشهد بعد مشهد)

2. **مرحلة الستوري بورد** (`generate_image` لكل مشهد):
   - ولّد صورة keyframe لكل مشهد رئيسي (style: cinematic, 16:9)
   - استخدم prompts مثل: "cinematic wide shot, golden hour, anamorphic lens, shallow depth of field"

🛠️ **أدواتك السينمائية المتاحة:**
- `list_voices(language='ar', limit=20)` — اجلب الأصوات + عينات MP3 للعميل يختار
- `generate_voiceover(text, voice_id, model)` — ولّد تعليق صوتي MP3 احترافي
- `write_script(title, logline, genre, duration_seconds, synopsis)` — اكتب سيناريو منظم
- `generate_storyboard(scenes=[...], style='cinematic')` — keyframes لكل مشهد
- `update_world_bible(characters, locations, plot_points, style_rules)` — احفظ ذاكرة السلسلة (للمسلسلات)
- `download_media` — مرجعيات سينمائية + مونتاج
- `request_credential` — اطلب مفاتيح fal.ai/OpenAI من العميل (لتوليد فيديو حقيقي لاحقاً)
- `generate_image` — صور أغلفة، بوسترات، شخصيات
- `apply_section` / `write_full_html` — صفحة عرض الفيلم النهائية
- `publish_site` — نشر صفحة الفيلم على zenrex.ai/s/{slug}
- `test_page` — تأكد من الصفحة قبل التسليم

🎯 **سير عمل مثالي لفيلم قصير (60 ثانية):**
1. `write_script` → سيناريو + logline
2. `list_voices(language='ar')` → اعرض الأصوات للعميل
3. (انتظر اختيار العميل للصوت)
4. `generate_voiceover` → تعليق صوتي بالصوت المختار
5. `generate_storyboard(scenes=[...])` → keyframes لـ 4-6 مشاهد
6. `apply_section` → ابني صفحة عرض الفيلم: poster + audio player + storyboard
7. `publish_site` → نشر + `test_page` للتأكد

4. **مرحلة الصوت**:
   - تعليق صوتي → `request_credential("elevenlabs_key", ...)` ثم استخدم Whisper voices.
   - موسيقى → ولّد brief، اطلب من العميل اختيار من مكتبة (أو يجيب key لـ Suno).

5. **مرحلة المونتاج**:
   - رتّب المشاهد + الموسيقى + الصوت في timeline منطقي.
   - أضف سب-تايتلز (Whisper) عربي + إنجليزي.

🛠️ **بناء صفحة العرض النهائية** (`write_full_html` + `apply_section`):
- Hero بعنوان الفيلم + poster (من keyframe المولّد).
- مشغّل فيديو رئيسي.
- قسم "Behind the Scenes" بالستوري بورد.
- معلومات الفيلم (المدة، اللغة، الأنماط).
- زر **تنزيل HD** + زر **مشاركة**.

🚫 **ممنوع**:
- ❌ تقول "ما أقدر أولّد فيديو" — اطلب المفتاح أولاً.
- ❌ تنتج مشهد فيه أخطاء حركية (يد ٦ أصابع، وجه مشوّه، حركة غير منطقية).
- ❌ تعرض الفيديو الأصلي من يوتيوب كأنه نتاجك (الـ `download_media` للمرجعية والمونتاج فقط).

═══════════════════════════════════════════════════════════
"""


MODE_ADDENDUM_DEVELOPER = """
═══════════════════════════════════════════════════════════
👨‍💻 **DEVELOPER MODE — البرمجي الكامل (Zenrex Code Brain)**

أنت الآن في وضع المطوّر — تبني/تعدّل/تنشر منتجات برمجية حقيقية (Backend + Frontend + DevOps).
**هذا الوضع يحل محل AutoCoder القديم تماماً** ويعطيك صلاحيات أوسع:

- **كل أدوات FreeBuild** متاحة (60 أداة): shell, files, DB, github, deploy, browser_use, audit, memory, delegate (security_auditor, performance_optimizer, ...).
- **التركيز هنا برمجي**: استخدم `run_shell` لتشغيل `pytest`, `npm test`, `git`, `docker compose`. استخدم `read_file`/`write_file` للكود متعدد الملفات. استخدم `github_*` لـ push وعمل PRs.
- **الـ audit_project يصير "code review شامل"** يشمل أمن + أداء + accessibility.
- **delegate('security_auditor')** بعد كل تعديل حسّاس.
- **memory_save** لحفظ قرارات معمارية (مثلاً: "نستخدم Postgres مع Alembic"، "Auth = JWT مع HttpOnly cookies").

**أنت مهندس Senior — تقترح، تنفذ، تختبر، تنشر. لا تنتظر إذن لكل خطوة صغيرة.**
"""


MODE_ADDENDUM_OWNER_ASSISTANT = """
═══════════════════════════════════════════════════════════
👑 **وضع مالك المنصة (Owner Assistant) — أنت Zenrex Operator**

أنت **يد المالك الأمينة** على منصة Zenrex بالكامل. شخصيتك مختلفة:

**هويتك:**
- ما تتعامل مع زبون، تتعامل مع **مالك المنصة** نفسه. هو يأمر، أنت تنفّذ.
- **مسؤول عن كل شي على zenrex.ai**: التجار، المتاجر، الطلبات، الموظفين، السائقين، الإعلانات، الفواتير، الـ SaaS، الـ Cinema Studio، الأخطاء، التقارير اليومية، الدعم الفني.
- لو شي خربان على المنصة، **اكتشفه وأصلحه قبل ما العميل يبلّغ**.
- تقدم **تقارير دورية**: مبيعات اليوم، طلبات معلّقة، تجار جدد، أخطاء حصلت، كل صباح.

**أدواتك الخاصة (مفعّلة لك فقط):**
- 🖥️ `local_browser_*` — تتحكم بمتصفح المالك مباشرة عبر إضافة Chrome (Gmail، لوحات تحكم خارجية، حسابات سوشال ميديا، إلخ).
- 🤖 **`desktop_*` — التحكم الكامل بجهاز المالك الفيزيائي (ماوس، كيبورد، ملفات، تطبيقات).** هذي الأقوى — تستخدمها لما المالك يقول "افتح لي كذا"، "نزّل هذا الملف عندي"، "اكتب لي في برنامج كذا"، أو أي مهمة تحتاج تتنفذ على شاشته فعلياً.
- 💻 `run_shell` — تشغيل أوامر على السيرفر (SSH، ffmpeg، git).
- 🚀 `deploy_to` — نشر مشاريع جديدة على Vercel/Netlify.
- 📧 `send_email`/`send_sms` — إرسال رسائل من حساب المنصة الرسمي.
- 🗄️ `db_query`/`db_count` — قراءة كل بيانات التجار/الطلبات/السائقين مباشرة.
- 🐙 `github_create_repo`/`github_push_file` — التحكم بـ GitHub.

**🤖 سياسة استخدام Desktop Agent (مهم جداً):**

كل ما المالك يطلب شي يصير على **جهازه** (مش على السيرفر / مش على المتصفح فقط)، اتبع هذا التسلسل بالضبط:

1. **استدعِ `desktop_status` أولاً** — تشيك إذا الاتصال شغّال.

2. **إذا `connected: false`**:
   - استدعِ `desktop_pair` (يطلع لك رمز جديد + رابط تنزيل)
   - 🚨 **قانون مقدّس**: لما يرجع الـ tool القيمة `code` — انسخها **حرف بحرف (verbatim)** في ردّك بالعربي. ممنوع تخترع، تتذكر، تخمن، أو تعدّل أي حرف من الرمز. لو غيرت حرف واحد، الـ pairing راح يفشل والعميل بيرجع زعلان. الرمز اللي يولّده السيرفر فقط (6 أحرف من المجموعة `[A-Z2-9]` بدون 0/O/I/1) هو اللي يقبله. حتى لو شفت رمز "أوضح" أو "أحلى"، استخدم اللي رجع من الـ tool حصراً. الـ tool يرجع لك حقل `display_block` فيه ال markdown جاهز — انسخه كما هو في ردّك.
   - بعد ما تنسخ الـ `code`، اعرضه بصيغة بارزة:
     ```
     🔑 رمزك: **<code-from-tool-output>**
     ⏱️ صالح 10 دقايق
     
     ▸ لو التطبيق مركّب: افتحه من Desktop، الصق الرمز، اضغط Connect.
     ▸ لو مو مركّب: الصق هذا في PowerShell:
       iwr {download_base}/api/desktop-agent/bootstrap.ps1 -useb | iex
     ```
   - **لا تكمل تنفيذ المهمة قبل ما يقول "متصل" أو يصير `desktop_status.connected: true`**.

3. **إذا `connected: true`** — استخدم الأدوات مباشرة بدون ما تطلب رمز:
   - `desktop_screenshot` — شف وش على شاشته قبل أي قرار يحتاج إحداثيات
   - `desktop_act(action="open_url", params={url})` — يفتح موقع في متصفحه (الأفضل بدل `open_app` لأنه يضمن الفوكس)
   - `desktop_act(action="open_app", params={name})` — يفتح تطبيق (Notepad, Chrome, VS Code…). يحاول يجيب الفوكس تلقائياً.
   - `desktop_act(action="type", params={text})` — يكتب نص (يدعم العربي)
   - `desktop_act(action="press_key", params={key})` — كي بورد shortcut. **انتبه**: على Windows استخدم `winleft+r` مو `win+r`.
   - `desktop_act(action="click", params={x,y})` — كليك على إحداثيات
   - `desktop_act(action="download_file", params={url, filename?})` — تنزيل ملف لمجلد Downloads عند المالك
   - `desktop_act(action="write_file", params={path, content})` — كتابة ملف على جهازه (يدعم `~/Downloads/foo.txt`)
   - `desktop_act(action="read_file", params={path})` — قراءة ملف منه

4. **بعد كل `desktop_act` تغيّر الواجهة (open_app/open_url/click)** — انتظر شوية ثم خذ `desktop_screenshot` لتتأكد إن الحركة وصلت للمكان الصح.

5. **التركيز / Focus**: لما تفتح تطبيق وتبي تكتب فيه، انتظر ثانية على الأقل بين `open_app` و `type` عشان النافذة تكون في الواجهة. لو الكتابة راحت لتطبيق غلط، استخدم `desktop_act(action="focus_window", params={title})` بأول كلمة من عنوان النافذة.

6. **الأمان**: لو رح تسوي شي مدمّر (حذف ملفات، إغلاق تطبيقات بدون حفظ، إلخ) — استخدم `ask_user_inline` للتأكيد قبل التنفيذ.

7. 🚫 **ممنوعات نهائية**:
   - لا تكتب رمز ما رجعه الـ tool فعلياً.
   - لا تستخدم أحرف خارج المجموعة `[A-HJ-NP-Z2-9]` (يعني لا 0/O/I/1).
   - لا "تحاول تذكّر" رمز سابق من المحادثة. كل مرة استدعِ `desktop_pair` من جديد لو الاتصال انقطع.

8. 🎬 **سياسة الإيقاع (Visible-Pacing) — مهم جداً لتجربة المالك**:
   المالك يشوف شاشته أمامه، فلازم كل حركة تكون **مرئية وبطيئة كافي**:
   - قبل أي `desktop_act` تغيّر الواجهة (click, type, open_url, open_app)، اكتب **سطر واحد عربي** يقول وش رح تسوي الحين. مثال: "الحين رح أفتح Chrome وأدخل YouTube..." → ثم `desktop_act`.
   - استخدم `desktop_screenshot` بعد كل خطوة كبيرة لتأكيد إن النتيجة وصلت.
   - لا تجمع 5 أوامر متتالية بدون استراحة — اعمل خطوة واحدة، تأكد، ثم الخطوة الجاية.
   - الـ Desktop Agent ذاتياً يحرّك الماوس **بشكل بطيء و smooth** عشان المالك يشوف الكورس. ما تحتاج تضبط `duration` يدوياً — اتركها للـ default.
   - في الـ overlay العائم (Floating Notifier) عند المالك، كل أمر يطلع له فيه. خلّ ترتيب الأوامر منطقي عشان يقدر يفهم القصة بسرعة.


**قواعد سلوكك:**
1. لا تخاطب المالك بـ "حضرتك" أو "العميل" — اخاطبه مباشرة بصيغة المساعد: "وش تبيني أسوي؟"
2. كل قرار تنفيذ كبير (نشر، حذف، تحويل أموال) → استدعِ `ask_user_inline` قبل التنفيذ.
3. عند رصد مشكلة على المنصة، استخدم `db_query` وعطه أرقام دقيقة (مش تقديرات).
4. للتشخيص الفني عند العميل النهائي، استدعِ `delegate('security_auditor')` أو `delegate('performance_optimizer')`.
5. سجّل القرارات المهمة في `memory_save(scope='merchant')` — أنت ذاكرة المنصة الطويلة.
6. **هذا الذكاء مستقل**: لا يشاركه العملاء العاديون. أنت تشتغل للمالك حصرياً.
"""


# ── Desktop-control addendum — injected whenever is_owner=True (any mode) ──
DESKTOP_OWNER_ADDENDUM = """

═══════════════════════════════════════════════════════════════════
🖥️ تحكم بجهاز المالك الفعلي (Desktop Agent) — قواعد إلزامية
═══════════════════════════════════════════════════════════════════

عندك أدوات `desktop_*` تتحكم بجهاز المالك الفيزيائي مباشرة (ماوس، كيبورد، ملفات، تطبيقات، تنزيلات). هذي الأدوات مفعّلة لك فقط لأنك تكلم المالك.

🔄 **التسلسل الإلزامي** (افعله بهذا الترتيب لأي طلب يتضمن جهاز المالك):

1️⃣ **`desktop_status()`** — تحقق من الاتصال أولاً.

2️⃣ **إذا `connected: false`** → استدعِ `desktop_pair()`:
   - الـ tool يرجع لك حقل `code` (6 أحرف) — **هذا الرمز الحقيقي الوحيد**.
   - الـ tool يرجع أيضاً حقل `display_block` — **نص markdown جاهز كاملاً**.
   - 🚨 **افعل بالضبط**: انسخ كامل قيمة `display_block` كما هي في ردّك، بدون تعديل حرف.
   - مثال (حرفي):
     ```
     <user>: افتح Notepad على جهازي
     <tool desktop_status>: {"connected": false}
     <tool desktop_pair>: {"code": "ABC234", "display_block": "🔑 **رمز ربط الجهاز:** `ABC234`  ⏱️ صالح 10 دقايق\\n\\n..."}
     <you reply>: تمام، عشان أفتح Notepad على جهازك لازم نربط Desktop Agent أولاً.
     
     🔑 **رمز ربط الجهاز:** `ABC234`  ⏱️ صالح 10 دقايق
     
     [... باقي display_block كما هو ...]
     
     قول لي "تم" لما تتصل وأفتح Notepad على طول.
     ```

3️⃣ **إذا `connected: true`** — نفّذ المهمة مباشرة بـ `desktop_act` بدون ما تطلب رمز.

🚫 **ممنوعات صارمة** — مخالفة أي وحدة منها = إفشال للمهمة:
- ❌ **ممنوع تخترع أو تخمن رمز** — أي رمز ما رجعه `desktop_pair` في نفس الدورة = كذب.
- ❌ ممنوع تكتب 0/O/I/1 في الرمز (charset = A-Z + 2-9 فقط، بدون هذه).
- ❌ ممنوع "تذكر" رمز من رسالة سابقة — الرموز تنتهي بعد 10 دقايق، استدعِ `desktop_pair` كل مرة.
- ❌ ممنوع تعطي رمز قبل ما تستدعي `desktop_pair` فعلياً في هذي الدورة.
- ❌ لو المستخدم قال "الرمز ما يشتغل" → ممنوع تعطيه رمز ثاني من راسك. استدعِ `desktop_pair` من جديد.

✅ **القاعدة الذهبية**: لو ردك يحتوي رمز ما رجعه `desktop_pair` في نفس الدورة → الـ pairing راح يفشل والمالك راح يزعل.

🔎 **مثال على الفرق بين الصح والخطأ**:

❌ **خطأ — الـ AI يخترع رمز**:
```
<user>: ابي اربط جهازي
<AI reply>: تمام، رمزك: XPQ4M7      ← مفبرك، السيرفر ما يعرفه، يفشل!
```

✅ **صح — الـ AI يستدعي الأداة أولاً**:
```
<user>: ابي اربط جهازي
<AI>: [calls desktop_status]  → {connected: false}
<AI>: [calls desktop_pair]    → {code: "K7R3UD", display_block: "..."}
<AI reply>: 🔑 **رمزك: K7R3UD** ⏱️ صالح 10 دقايق
            افتح Zenrex Desktop Agent، الصق `K7R3UD`، اضغط Connect.
```
الرمز `K7R3UD` حقيقي — جاء من `desktop_pair`، الـ pairing ينجح.

🎬 **سياسة الإيقاع المرئي** (Visible-Pacing):
- قبل كل `desktop_act` يغيّر الواجهة (`click`, `type`, `open_url`, `open_app`)، اكتب سطر عربي قصير يقول وش رح تسوي الآن.
- استخدم `desktop_screenshot` بعد كل خطوة كبيرة لتأكيد النتيجة.
- لا تجمع 5 أوامر متتالية — خطوة، تأكيد، خطوة جاية.

📍 **مرجع الأدوات السريع**:
- `desktop_act(action="open_url", params={"url":"..."})` — يفتح موقع في المتصفح.
- `desktop_act(action="open_app", params={"name":"notepad"})` — يفتح تطبيق (يجيب الفوكس تلقائياً).
- `desktop_act(action="type", params={"text":"..."})` — يكتب نص (يدعم العربي).
- `desktop_act(action="press_key", params={"key":"winleft+r"})` — مفتاح أو كومبو. (Windows: `winleft` مو `win`).
- `desktop_act(action="click", params={"x":960,"y":600})` — كليك بإحداثيات.
- `desktop_act(action="download_file", params={"url":"...","filename":"..."})` — يحمّل ملف إلى Downloads عند المالك.
- `desktop_act(action="write_file", params={"path":"~/Downloads/x.txt","content":"..."})` — يكتب ملف.

═══════════════════════════════════════════════════════════════════
"""


def get_system_prompt(project: Dict[str, Any], is_owner: bool = False) -> str:
    """Return the system prompt customized for the project's mode and role.

    Modes: 'website' (default), 'image_studio', 'video_studio', 'developer', 'owner_assistant'.

    When is_owner=True, the strict desktop-control policy is appended to every
    mode — so a platform owner gets desktop tools no matter which project
    flavour they're in.
    """
    mode = (project or {}).get("mode", "website")
    if mode == "image_studio":
        base = AGENT_SYSTEM_PROMPT + "\n" + MODE_ADDENDUM_IMAGE
    elif mode == "video_studio":
        base = AGENT_SYSTEM_PROMPT + "\n" + MODE_ADDENDUM_VIDEO
    elif mode == "developer":
        base = AGENT_SYSTEM_PROMPT + "\n" + MODE_ADDENDUM_DEVELOPER
    elif mode == "owner_assistant":
        base = AGENT_SYSTEM_PROMPT + "\n" + MODE_ADDENDUM_DEVELOPER + "\n" + MODE_ADDENDUM_OWNER_ASSISTANT
    else:
        base = AGENT_SYSTEM_PROMPT
    if is_owner:
        base += DESKTOP_OWNER_ADDENDUM
    return base


# ─── Main Agent Loop ──────────────────────────────────────────────────────────
async def run_agent_turn(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int = 30,
    model: str = "claude-sonnet-4-5-20250929",
    auth_token: Optional[str] = None,
    db: Any = None,
    is_owner: bool = False,
) -> Dict[str, Any]:
    """
    Run one agentic turn. The AI may call multiple tools before issuing finish().
    Anthropic Claude ONLY — same family as the platform AI. Fallback chain:
      1. Direct ANTHROPIC_API_KEY
      2. EMERGENT_LLM_KEY via Emergent's gateway (proxies to Claude)
    """
    providers_to_try = []
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        providers_to_try.append(("anthropic", model))
    if os.environ.get("EMERGENT_LLM_KEY", "").strip():
        providers_to_try.append(("emergent_anthropic", model))
    if not providers_to_try:
        return {"ok": False, "error": "Claude key required (ANTHROPIC_API_KEY or EMERGENT_LLM_KEY)"}

    last_err = None
    for provider, prov_model in providers_to_try:
        try:
            if provider in ("anthropic", "emergent_anthropic"):
                result = await _run_anthropic_agent(project, user_message, history_messages, max_iterations, prov_model, use_emergent=(provider == "emergent_anthropic"), auth_token=auth_token, db=db, is_owner=is_owner)
            else:
                result = await _run_openai_compat_agent(project, user_message, history_messages, max_iterations, provider, prov_model, auth_token=auth_token, db=db, is_owner=is_owner)
            if result.get("ok"):
                return result
            last_err = result.get("error", "unknown")
            # If credit/auth issue, try next provider; otherwise short-circuit
            if not any(k in str(last_err).lower() for k in ["credit", "balance", "unauthorized", "401", "402", "429", "quota"]):
                return result
            logger.warning(f"agent: {provider} failed ({last_err[:80]}) — falling back")
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:200]}"
            logger.exception(f"agent provider {provider} crashed")
            continue
    return {"ok": False, "error": f"all providers failed; last: {last_err}"}


async def _run_anthropic_agent(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int,
    model: str,
    use_emergent: bool = False,
    auth_token: Optional[str] = None,
    db: Any = None,
    is_owner: bool = False,
) -> Dict[str, Any]:
    """Anthropic native tool-use agent loop."""
    try:
        from anthropic import AsyncAnthropic
    except Exception:
        return {"ok": False, "error": "anthropic SDK missing"}

    if use_emergent:
        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        if not api_key:
            return {"ok": False, "error": "EMERGENT_LLM_KEY not configured"}
        client = AsyncAnthropic(
            api_key=api_key,
            base_url="https://integrations.emergentagent.com/llm/anthropic",
        )
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY not configured"}
        client = AsyncAnthropic(api_key=api_key)
    ctx = FreeBuildToolContext(project, auth_token=auth_token, db=db, is_owner=is_owner)

    initial_state = _exec_tool(ctx, "read_current_html", {})
    template_note = ""
    cat_id = project.get("category_id")
    if cat_id:
        template_note = (
            f"\n  📦 وضع القالب: المشروع مبني على قالب جاهز من فئة '{cat_id}'. "
            "حافظ على الـlayout والـsections الأساسية للقالب — عدّل النصوص والصور والألوان فقط. "
            "لا تعيد تصميم القالب من الصفر إلا إذا طلب العميل صراحة.\n"
        )
    state_summary = (
        f"📍 السياق:\n"
        f"  اسم المشروع: {project.get('name','?')}\n"
        f"  الوصف: {project.get('description','(لم يحدّد)')}\n"
        f"  الموقع الحالي: {initial_state.get('summary','(فارغ)')}\n"
        f"{template_note}"
    )

    messages: List[Dict[str, Any]] = []
    for m in history_messages[-12:]:
        if m.get("role") in ("user", "assistant"):
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                messages.append({"role": m["role"], "content": content})
    messages.append({"role": "user", "content": f"{state_summary}\n\nالطلب: {user_message}"})

    summary = ""
    options: List[str] = []
    iterations = 0
    model_used = model

    # ── Auto-inject long-term memories into the system prompt (once per turn) ──
    base_prompt = get_system_prompt(project, is_owner=is_owner)
    try:
        merchant_id = project.get("merchant_id") or project.get("user_id") or project.get("owner_id")
        memory_block = await load_project_memories_for_prompt(
            ctx.db, ctx.project_id, merchant_id
        )
        full_system_prompt = base_prompt + (memory_block or "")
    except Exception:
        full_system_prompt = base_prompt

    for _step in range(max_iterations):
        iterations += 1
        try:
            resp = await client.messages.create(
                model=model,
                system=full_system_prompt,
                max_tokens=8000,
                tools=tools_for_user(ctx.is_owner),
                messages=messages,
            )
        except Exception as e:
            return {"ok": False, "error": f"anthropic call failed: {type(e).__name__}: {str(e)[:200]}",
                    "iterations": iterations, "tool_log": ctx.tool_log}

        model_used = getattr(resp, "model", model)
        assistant_blocks: List[Dict[str, Any]] = []
        tool_uses: List[Dict[str, Any]] = []
        for block in resp.content:
            btype = getattr(block, "type", "")
            if btype == "text":
                assistant_blocks.append({"type": "text", "text": block.text})
            elif btype == "tool_use":
                assistant_blocks.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
                tool_uses.append({"id": block.id, "name": block.name, "input": block.input})
        messages.append({"role": "assistant", "content": assistant_blocks})

        if not tool_uses:
            for b in assistant_blocks:
                if b.get("type") == "text":
                    summary = (summary + "\n" + b["text"]).strip()
            break

        tool_results: List[Dict[str, Any]] = []
        finished = False
        for tu in tool_uses:
            if tu["name"] == "finish":
                summary = (tu["input"].get("summary") or "").strip()
                options = [o for o in (tu["input"].get("options") or []) if isinstance(o, str)][:4]
                ctx.log("finish", tu["input"], "agent finished")
                tool_results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": "finished"})
                finished = True
            else:
                result = await _dispatch_tool(ctx, tu["name"], tu["input"])
                ctx.log(tu["name"], tu["input"], result)
                tool_results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": json.dumps(result, ensure_ascii=False)[:6000]})
        messages.append({"role": "user", "content": tool_results})
        if finished:
            break

    return {
        "ok": True,
        "summary": summary or "تم.",
        "options": options,
        "new_html": ctx.current_html if ctx.changes_made > 0 else None,
        "iterations": iterations,
        "tool_log": ctx.tool_log,
        "snapshots": ctx.snapshots_to_create,
        "model_used": model_used,
        "changes_made": ctx.changes_made,
    }


async def _run_openai_compat_agent(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int,
    provider: str,
    model: str,
    auth_token: Optional[str] = None,
    db: Any = None,
    is_owner: bool = False,
) -> Dict[str, Any]:
    """OpenAI-compatible tool-use agent (works for OpenAI, Moonshot/Kimi)."""
    try:
        from openai import AsyncOpenAI
    except Exception:
        return {"ok": False, "error": "openai SDK missing"}

    if provider == "moonshot":
        api_key = os.environ.get("MOONSHOT_API_KEY", "")
        base_url = "https://api.moonshot.ai/v1"
    else:
        api_key = os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY", "")
        base_url = None
    if not api_key:
        return {"ok": False, "error": f"{provider} API key not configured"}

    client = AsyncOpenAI(api_key=api_key, base_url=base_url) if base_url else AsyncOpenAI(api_key=api_key)
    ctx = FreeBuildToolContext(project, auth_token=auth_token, db=db, is_owner=is_owner)

    initial_state = _exec_tool(ctx, "read_current_html", {})
    template_note = ""
    cat_id = project.get("category_id")
    if cat_id:
        template_note = (
            f"\n  📦 وضع القالب: المشروع مبني على قالب جاهز من فئة '{cat_id}'. "
            "حافظ على الـlayout والـsections الأساسية للقالب — عدّل النصوص والصور والألوان فقط. "
            "لا تعيد تصميم القالب من الصفر إلا إذا طلب العميل صراحة.\n"
        )
    state_summary = (
        f"📍 السياق:\n"
        f"  اسم المشروع: {project.get('name','?')}\n"
        f"  الوصف: {project.get('description','(لم يحدّد)')}\n"
        f"  الموقع الحالي: {initial_state.get('summary','(فارغ)')}\n"
        f"{template_note}"
    )

    # Convert tool schema to OpenAI format
    openai_tools = [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
        for t in TOOLS_SCHEMA
    ]

    messages: List[Dict[str, Any]] = [{"role": "system", "content": get_system_prompt(project, is_owner=is_owner)}]
    for m in history_messages[-12:]:
        if m.get("role") in ("user", "assistant"):
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                messages.append({"role": m["role"], "content": content})
    messages.append({"role": "user", "content": f"{state_summary}\n\nالطلب: {user_message}"})

    summary = ""
    options: List[str] = []
    iterations = 0
    model_used = model

    for _step in range(max_iterations):
        iterations += 1
        try:
            resp = await client.chat.completions.create(
                model=model, messages=messages, tools=openai_tools, max_tokens=8000,
            )
        except Exception as e:
            return {"ok": False, "error": f"{provider} call failed: {type(e).__name__}: {str(e)[:200]}",
                    "iterations": iterations, "tool_log": ctx.tool_log}

        choice = resp.choices[0]
        msg = choice.message
        model_used = getattr(resp, "model", model)
        text_content = msg.content or ""
        tool_calls = msg.tool_calls or []

        # Persist assistant turn in OpenAI conversation format
        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": text_content or None}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ]
        messages.append(assistant_msg)

        if not tool_calls:
            summary = text_content.strip()
            break

        finished = False
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            if tc.function.name == "finish":
                summary = (args.get("summary") or "").strip()
                options = [o for o in (args.get("options") or []) if isinstance(o, str)][:4]
                ctx.log("finish", args, "agent finished")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": "finished"})
                finished = True
            else:
                result = await _dispatch_tool(ctx, tc.function.name, args)
                ctx.log(tc.function.name, args, result)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result, ensure_ascii=False)[:6000]})
        if finished:
            break

    return {
        "ok": True,
        "summary": summary or "تم.",
        "options": options,
        "new_html": ctx.current_html if ctx.changes_made > 0 else None,
        "iterations": iterations,
        "tool_log": ctx.tool_log,
        "snapshots": ctx.snapshots_to_create,
        "model_used": model_used,
        "changes_made": ctx.changes_made,
    }


# ─── STREAMING AGENT (Server-Sent Events) ──────────────────────────────────
# Emits live "thinking" events for the user — each tool call becomes a
# visible step in the chat. Same logic as run_agent_turn but yields SSE.

TOOL_LABELS_AR: Dict[str, Dict[str, str]] = {
    "read_current_html":  {"running": "🔍 يقرأ الموقع الحالي ويحلل بنيته...",
                            "done": "✅ قرأ الموقع — تعرّف على الأقسام والروابط"},
    "list_sections":      {"running": "📋 يعرض كل أقسام الموقع...",
                            "done": "✅ سجّل قائمة الأقسام"},
    "validate_html":      {"running": "🩺 يفحص جودة الكود والروابط...",
                            "done": "✅ انتهى من الفحص"},
    "search_html":        {"running": "🔎 يبحث داخل الكود...",
                            "done": "✅ انتهى البحث"},
    "write_full_html":    {"running": "✏️ يكتب موقع كامل من الصفر...",
                            "done": "✅ كتب الـHTML الجديد"},
    "apply_section":      {"running": "🔧 يطبّق قسم محدد بدقة...",
                            "done": "✅ تم تطبيق القسم"},
    "update_nav":         {"running": "🗺️ يحدّث قائمة التنقّل (nav)...",
                            "done": "✅ تم تحديث القائمة"},
    "web_search":         {"running": "🌐 يبحث في الإنترنت عن أفضل المراجع...",
                            "done": "✅ جلب نتائج البحث"},
    "fetch_url":          {"running": "📡 يحمّل محتوى الرابط للتحليل...",
                            "done": "✅ تم جلب الصفحة"},
    "generate_image":     {"running": "🎨 يولّد صورة AI من جيميني نانو بنانا...",
                            "done": "✅ تم إنشاء الصورة"},
    "lint_javascript":    {"running": "🧪 يفحص الـJS للأخطاء الإملائية والبنيوية...",
                            "done": "✅ انتهى فحص الـJS"},
    "test_page":          {"running": "🔬 يفتح الصفحة في متصفح حقيقي ويتحقق منها بصرياً...",
                            "done": "✅ اختبار الصفحة اكتمل + سكرين شوت جاهز"},
    "list_voices":        {"running": "🎙️ يجلب قائمة الأصوات من ElevenLabs...",
                            "done": "✅ الأصوات جاهزة مع عينات MP3"},
    "generate_voiceover": {"running": "🗣️ يولّد التعليق الصوتي MP3...",
                            "done": "✅ التعليق الصوتي جاهز"},
    "write_script":       {"running": "📝 يكتب السيناريو السينمائي...",
                            "done": "✅ السيناريو جاهز"},
    "generate_storyboard":{"running": "🎭 يولّد الستوري بورد ومشاهد المفاتيح...",
                            "done": "✅ الستوري بورد جاهز"},
    "update_world_bible": {"running": "📚 يحفظ تفاصيل العالم القصصي...",
                            "done": "✅ ذاكرة المشروع محدّثة"},
    "save_credential":    {"running": "💾 يحفظ المفتاح بأمان (مشفّر)...",
                            "done": "✅ المفتاح محفوظ ومشفّر"},
    "validate_credential":{"running": "🧪 يختبر المفتاح فعلياً ضد الخدمة...",
                            "done": "✅ انتهى الاختبار — النتيجة من الـ API الحقيقي"},
    "list_credentials":   {"running": "📋 يعرض المفاتيح المحفوظة...",
                            "done": "✅ القائمة جاهزة"},
    "delete_credential":  {"running": "🗑️ يحذف المفتاح...",
                            "done": "✅ تم الحذف"},
    "recommend_service":  {"running": "🎯 يبحث عن أفضل الخدمات لك مع الأسعار وروابط التسجيل...",
                            "done": "✅ التوصية جاهزة"},
    "github_list_repos":  {"running": "📦 يجلب مستودعاتك من GitHub...",
                            "done": "✅ القائمة جاهزة"},
    "github_create_repo": {"running": "🆕 ينشئ مستودع جديد على GitHub...",
                            "done": "✅ المستودع جاهز"},
    "github_push_file":   {"running": "⬆️ يرفع الملف لـ GitHub...",
                            "done": "✅ تم الـ commit"},
    "github_get_file":    {"running": "📥 يقرأ ملف من GitHub...",
                            "done": "✅ تم القراءة"},
    "finish":             {"running": "📝 يجهّز التقرير النهائي...",
                            "done": "✅ جاهز"},
}
# Merge in labels for the advanced tools (run_shell, analyze_file, etc.)
TOOL_LABELS_AR.update(ADVANCED_TOOL_LABELS_AR)
TOOL_LABELS_AR.update(WORKFLOW_TOOL_LABELS_AR)
TOOL_LABELS_AR.update(PHASE4_TOOL_LABELS_AR)
TOOL_LABELS_AR.update(PHASE5_TOOL_LABELS_AR)
TOOL_LABELS_AR.update(DESKTOP_TOOL_LABELS_AR)


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_agent_turn(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int = 100,
    ctx_holder: Optional[Dict[str, Any]] = None,
    user_language: str = "ar",
    auth_token: Optional[str] = None,
    db: Any = None,
    is_owner: bool = False,
) -> AsyncGenerator[str, None]:
    """SSE generator: yields live thinking events while the agent works.

    If ctx_holder is provided, populates it with the final FreeBuildToolContext
    so the caller can persist current_html/snapshots after streaming completes.

    user_language: ISO 639-1 code from the UI; AI will reply in that language.
    """
    yield _sse("start", {"message": "🚀 الذكاء بدأ التحليل..."})
    await asyncio.sleep(0)

    # Anthropic ONLY — same family as the platform AI (Claude). No GPT, no Kimi:
    # those models produce subpar visual designs in Arabic. If credits run out,
    # we surface a clear Arabic error so the owner can top up.
    providers = []
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        providers.append(("anthropic", "claude-sonnet-4-5-20250929"))
    if not providers:
        yield _sse("error", {"message": "لا يوجد مفتاح Anthropic — أضف ANTHROPIC_API_KEY"})
        return

    last_err = None
    for provider, model in providers:
        try:
            yield _sse("provider", {"name": provider, "model": model, "message": f"🧠 يستخدم {model}"})
            await asyncio.sleep(0)
            async for chunk in _stream_one_provider(project, user_message, history_messages, max_iterations, provider, model, ctx_holder=ctx_holder, user_language=user_language, auth_token=auth_token, db=db, is_owner=is_owner):
                yield chunk
            return
        except _ProviderUnavailable as e:
            last_err = str(e)
            yield _sse("fallback", {"from": provider, "reason": str(e)[:120]})
            await asyncio.sleep(0)
            continue
        except Exception as e:
            yield _sse("error", {"message": f"{provider}: {type(e).__name__}: {str(e)[:200]}"})
            return
    yield _sse("error", {"message": f"كل المزودات فشلت: {last_err}"})


class _ProviderUnavailable(Exception):
    """Raised to trigger fallback to the next provider."""
    pass


async def _stream_one_provider(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int,
    provider: str,
    model: str,
    ctx_holder: Optional[Dict[str, Any]] = None,
    user_language: str = "ar",
    auth_token: Optional[str] = None,
    db: Any = None,
    is_owner: bool = False,
) -> AsyncGenerator[str, None]:
    """Run the tool loop for one provider, yielding SSE chunks per step."""
    ctx = FreeBuildToolContext(project, auth_token=auth_token, db=db, is_owner=is_owner)
    if ctx_holder is not None:
        ctx_holder["ctx"] = ctx

    # Track all narration text across iterations so we can fall back to it
    # if the AI ends without calling finish() with a proper summary.
    all_text_chunks: List[str] = []

    initial_state = _exec_tool(ctx, "read_current_html", {})
    template_note = ""
    cat_id = project.get("category_id")
    if cat_id:
        template_note = (
            f"\n  📦 وضع القالب: المشروع مبني على قالب جاهز من فئة '{cat_id}'. "
            "حافظ على الـlayout والـsections الأساسية للقالب — عدّل النصوص والصور والألوان فقط. "
            "لا تعيد تصميم القالب من الصفر إلا إذا طلب العميل صراحة.\n"
        )
    state_summary = (
        f"📍 السياق:\n"
        f"  اسم المشروع: {project.get('name','?')}\n"
        f"  الوصف: {project.get('description','(لم يحدّد)')}\n"
        f"  الموقع الحالي: {initial_state.get('summary','(فارغ)')}\n"
        f"{template_note}"
    )

    # Build conversation
    # Inject the user's UI language so the AI replies in the same language.
    # Build a human-readable language name for the system prompt.
    _LANG_NAMES = {
        "ar": "Arabic (Saudi dialect)", "en": "English", "fr": "French", "es": "Spanish",
        "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
        "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "tr": "Turkish",
        "hi": "Hindi", "ur": "Urdu", "fa": "Persian", "he": "Hebrew",
        "nl": "Dutch", "pl": "Polish", "id": "Indonesian", "th": "Thai",
        "vi": "Vietnamese", "ms": "Malay", "fil": "Filipino", "bn": "Bengali",
    }
    _lang_human = _LANG_NAMES.get(user_language, user_language)
    _lang_directive = (
        f"\n\n# LANGUAGE\n"
        f"The user's UI is currently set to: **{_lang_human}** (code: `{user_language}`). "
        f"You MUST write ALL of your conversational replies, summaries, button labels, "
        f"option suggestions, and explanations in {_lang_human}. Generated HTML/CSS/JS "
        f"website code stays language-agnostic, BUT any visible website text (headings, "
        f"buttons, copy) you write inside the HTML MUST also be in {_lang_human} unless "
        f"the user explicitly requests a different language for the site itself.\n"
    )

    if provider in ("anthropic", "emergent_anthropic"):
        from anthropic import AsyncAnthropic
        if provider == "emergent_anthropic":
            # Emergent's universal key — same Anthropic SDK, different gateway
            client = AsyncAnthropic(
                api_key=os.environ.get("EMERGENT_LLM_KEY", ""),
                base_url="https://integrations.emergentagent.com/llm/anthropic",
            )
        else:
            client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        messages: List[Dict[str, Any]] = []
        sys_prompt = get_system_prompt(project, is_owner=is_owner) + _lang_directive
    else:
        from openai import AsyncOpenAI
        if provider == "moonshot":
            client = AsyncOpenAI(api_key=os.environ.get("MOONSHOT_API_KEY", ""),
                                 base_url="https://api.moonshot.ai/v1")
        else:
            client = AsyncOpenAI(api_key=os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY", ""))
        messages = [{"role": "system", "content": get_system_prompt(project, is_owner=is_owner) + _lang_directive}]
        sys_prompt = None
        openai_tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}} for t in TOOLS_SCHEMA]

    for m in history_messages[-12:]:
        if m.get("role") in ("user", "assistant"):
            c = m.get("content", "")
            if isinstance(c, str) and c.strip():
                messages.append({"role": m["role"], "content": c})
    messages.append({"role": "user", "content": f"{state_summary}\n\nالطلب: {user_message}"})

    iterations = 0
    summary = ""
    options: List[str] = []
    model_used = model

    for step in range(max_iterations):
        iterations += 1
        logger.info(f"[agent-stream] iter={iterations} start (provider={provider})")

        if provider in ("anthropic", "emergent_anthropic"):
            # Live streaming with heartbeats: Claude's stream goes silent for 30-90s
            # while generating large tool inputs (e.g. write_full_html with 8000 tokens).
            # Proxies (Kubernetes ingress, Cloudflare, Railway) drop SSE connections
            # after ~60s of silence. To prevent that, we run the stream in a producer
            # task and emit ":ping" SSE comments every 5s while waiting.
            text_chunks: List[str] = []
            tool_uses: List[Dict[str, Any]] = []
            assistant_blocks: List[Dict[str, Any]] = []
            final_msg = None
            current_text = ""
            tool_input_bytes = 0  # progress counter while tool input streams in
            last_tool_emit = 0
            tool_input_snapshot = ""  # live snapshot of streaming tool JSON
            current_tool_name = ""  # which tool is currently being built
            queue: asyncio.Queue = asyncio.Queue()
            _SENTINEL_FINAL = "__final__"
            _SENTINEL_ERROR = "__error__"

            async def _produce_events():
                try:
                    # max_tokens 16K (up from 5K) — Sonnet 4.5 supports 64K output;
                    # 16K gives the agent enough headroom to emit full HTML sections
                    # in a single shot without truncating mid-JSON which was causing
                    # the "starts writing then restarts" issue users were reporting.
                    async with client.messages.stream(
                        model=model, system=sys_prompt, max_tokens=16000,
                        tools=tools_for_user(ctx.is_owner), messages=messages,
                    ) as st:
                        async for ev in st:
                            await queue.put(("event", ev))
                        fm = await st.get_final_message()
                    await queue.put((_SENTINEL_FINAL, fm))
                except Exception as exc:
                    await queue.put((_SENTINEL_ERROR, exc))

            producer = asyncio.create_task(_produce_events())
            stream_err: Optional[BaseException] = None
            try:
                while True:
                    try:
                        kind, payload = await asyncio.wait_for(queue.get(), timeout=3.0)
                    except asyncio.TimeoutError:
                        # Heartbeat: emit a real SSE event (not just a comment) so
                        # K8s/Cloudflare proxies count it as active traffic and don't
                        # cut the connection during long tool_use generation phases.
                        yield _sse("ping", {"t": int(asyncio.get_event_loop().time()), "step": iterations})
                        await asyncio.sleep(0)
                        continue
                    if kind == _SENTINEL_FINAL:
                        final_msg = payload
                        break
                    if kind == _SENTINEL_ERROR:
                        stream_err = payload
                        break
                    event = payload
                    et = getattr(event, "type", "")
                    # Live text token (Claude's narration between/before tool calls)
                    if et == "text":
                        delta = getattr(event, "text", "") or ""
                        if delta:
                            current_text += delta
                            yield _sse("text_delta", {"text": delta, "step": iterations})
                            await asyncio.sleep(0)
                    # New content block — could be a tool_use; track its name
                    elif et == "content_block_start":
                        cb = getattr(event, "content_block", None)
                        if cb is not None and getattr(cb, "type", "") == "tool_use":
                            current_tool_name = getattr(cb, "name", "") or ""
                            tool_input_snapshot = ""
                            tool_input_bytes = 0
                            last_tool_emit = 0
                            # Friendly Arabic label for the tool we're about to build
                            tool_label_ar = TOOL_LABELS_AR.get(current_tool_name, {}).get("running", f"⚙️ {current_tool_name}")
                            yield _sse("tool_building", {
                                "step": iterations,
                                "tool_name": current_tool_name,
                                "snippet": "",
                                "bytes": 0,
                                "label": tool_label_ar,
                                "starting": True,
                            })
                            await asyncio.sleep(0)
                    # Tool input JSON streaming — emit live snippets so the user
                    # sees actual code being typed (Cursor/Claude style), not just a counter.
                    elif et == "input_json":
                        partial = getattr(event, "partial_json", "") or ""
                        tool_input_snapshot += partial
                        tool_input_bytes = len(tool_input_snapshot)
                        # Throttle: emit at most every ~400 bytes so we don't flood the wire
                        if tool_input_bytes - last_tool_emit >= 400 or last_tool_emit == 0:
                            # Send the LAST ~280 chars as a live snippet (the "typing tail")
                            # so the UI shows real code scrolling, like a terminal.
                            tail = tool_input_snapshot[-280:] if len(tool_input_snapshot) > 280 else tool_input_snapshot
                            yield _sse("tool_building", {
                                "step": iterations,
                                "tool_name": current_tool_name,
                                "snippet": tail,
                                "bytes": tool_input_bytes,
                                "label": f"⚙️ يكتب الكود... ({tool_input_bytes:,} حرف)",
                            })
                            await asyncio.sleep(0)
                            last_tool_emit = tool_input_bytes
                    # Content block ended — flush text/tool buffers
                    elif et == "content_block_stop":
                        if current_text.strip():
                            yield _sse("text_end", {"step": iterations})
                            await asyncio.sleep(0)
                        if tool_input_bytes > 0:
                            yield _sse("tool_building", {
                                "step": iterations,
                                "tool_name": current_tool_name,
                                "snippet": "",
                                "bytes": tool_input_bytes,
                                "label": f"✨ تم توليد الكود ({tool_input_bytes:,} حرف)",
                                "done": True,
                            })
                            await asyncio.sleep(0)
                        current_text = ""
                        tool_input_bytes = 0
                        last_tool_emit = 0
                        tool_input_snapshot = ""
                        current_tool_name = ""
            finally:
                if not producer.done():
                    producer.cancel()
                    try:
                        await producer
                    except (asyncio.CancelledError, Exception):
                        pass

            if stream_err is not None:
                logger.exception("agent stream: anthropic stream failed", exc_info=stream_err)
                msg = f"{type(stream_err).__name__}: {str(stream_err)[:200]}"
                if any(k in msg.lower() for k in ["credit", "balance", "401", "402", "429", "quota"]):
                    raise _ProviderUnavailable(
                        "⚠️ رصيد Anthropic منتهي. لتفعيل الذكاء، يحتاج المالك "
                        "شحن الرصيد من: console.anthropic.com/settings/billing"
                    )
                raise stream_err
            model_used = getattr(final_msg, "model", model)
            stop_reason = getattr(final_msg, "stop_reason", "?")
            logger.info(f"[agent-stream] iter={iterations} stream done. stop_reason={stop_reason} content_blocks={len(final_msg.content or [])}")
            for block in (final_msg.content or []):
                bt = getattr(block, "type", "")
                if bt == "text":
                    text_chunks.append(block.text)
                    all_text_chunks.append(block.text)  # accumulate for fallback
                    assistant_blocks.append({"type": "text", "text": block.text})
                elif bt == "tool_use":
                    assistant_blocks.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
                    tool_uses.append({"id": block.id, "name": block.name, "input": block.input})
            messages.append({"role": "assistant", "content": assistant_blocks})

            # 🆕 Auto-resume on truncation: if the model hit max_tokens without
            # completing its work, push a continuation prompt so it picks up
            # exactly where it left off — completely transparent to the user.
            # This is what fixes the "starts writing then restarts" bug.
            if stop_reason == "max_tokens" and not tool_uses:
                yield _sse("info", {"message": "📝 يكمل توليد المحتوى..."})
                await asyncio.sleep(0)
                messages.append({
                    "role": "user",
                    "content": "أكمل من حيث توقفت بالضبط بدون إعادة. لا تكرر ما كتبت سابقاً، استمر في النقطة التالية مباشرة.",
                })
                iterations += 1
                continue
        else:
            try:
                resp = await client.chat.completions.create(
                    model=model, messages=messages, tools=openai_tools, max_tokens=8000,
                )
            except Exception as e:
                msg = f"{type(e).__name__}: {str(e)[:200]}"
                if any(k in msg.lower() for k in ["credit", "balance", "not found", "401", "402", "429", "quota", "permission"]):
                    raise _ProviderUnavailable(msg)
                raise
            model_used = getattr(resp, "model", model)
            choice = resp.choices[0].message
            text_chunks = [choice.content] if choice.content else []
            tool_uses = []
            assistant_msg = {"role": "assistant", "content": choice.content or None}
            if choice.tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in choice.tool_calls
                ]
                for tc in choice.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    tool_uses.append({"id": tc.id, "name": tc.function.name, "input": args})
            messages.append(assistant_msg)

        # For OpenAI-compatible providers we still emit a single "thinking" event per
        # text chunk (no streaming). For Anthropic, text was already streamed live
        # via "text_delta" events above — no need to duplicate.
        if provider not in ("anthropic", "emergent_anthropic"):
            for txt in text_chunks:
                if txt and txt.strip():
                    yield _sse("thinking", {"text": txt.strip()[:400]})
                    await asyncio.sleep(0)

        if not tool_uses:
            # No more tools — model wrapped up with text
            summary = "\n".join(text_chunks).strip()
            break

        # Execute each tool, emit "tool" events
        finished = False
        for tu in tool_uses:
            label_in = TOOL_LABELS_AR.get(tu["name"], {}).get("running", f"🔧 {tu['name']}...")
            yield _sse("tool", {"name": tu["name"], "phase": "running", "label": label_in, "step": iterations})
            await asyncio.sleep(0)

            if tu["name"] == "finish":
                summary = (tu["input"].get("summary") or "").strip()
                options = [o for o in (tu["input"].get("options") or []) if isinstance(o, str)][:4]
                ctx.log("finish", tu["input"], "finished")
                if provider in ("anthropic", "emergent_anthropic"):
                    messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tu["id"], "content": "finished"}]})
                else:
                    messages.append({"role": "tool", "tool_call_id": tu["id"], "content": "finished"})
                finished = True
                yield _sse("tool", {"name": "finish", "phase": "done", "label": TOOL_LABELS_AR["finish"]["done"], "step": iterations})
                await asyncio.sleep(0)
            else:
                result = await _dispatch_tool(ctx, tu["name"], tu["input"])
                ctx.log(tu["name"], tu["input"], result)
                label_done = TOOL_LABELS_AR.get(tu["name"], {}).get("done", "✅ تم")
                # Add a short result snippet to the label
                snippet = ""
                if tu["name"] == "validate_html":
                    issues = result.get("issues") or []
                    snippet = f" — {len(issues)} مشكلة" if issues else " — لا مشاكل"
                elif tu["name"] == "list_sections":
                    snippet = f" — {result.get('count', 0)} قسم"
                elif tu["name"] == "read_current_html":
                    snippet = f" — {result.get('length', 0)} حرف"
                elif tu["name"] == "write_full_html":
                    snippet = f" — {result.get('new_length', 0)} حرف"
                elif tu["name"] == "apply_section":
                    snippet = f" — قسم #{tu['input'].get('id','?')}"
                yield _sse("tool", {"name": tu["name"], "phase": "done", "label": label_done + snippet, "step": iterations})
                await asyncio.sleep(0)
                if provider in ("anthropic", "emergent_anthropic"):
                    messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tu["id"], "content": json.dumps(result, ensure_ascii=False)[:6000]}]})
                else:
                    messages.append({"role": "tool", "tool_call_id": tu["id"], "content": json.dumps(result, ensure_ascii=False)[:6000]})

        if finished:
            break

    # Final summary — use AI's own accumulated text if it didn't call finish() properly.
    # No more generic Arabic fallback messages — let the AI speak in its own voice.
    if not summary or len(summary.strip()) < 8:
        accumulated = "\n\n".join(t.strip() for t in all_text_chunks if t and t.strip())
        if accumulated:
            summary = accumulated.strip()
        elif ctx.changes_made > 0:
            summary = f"✅ خلصت! طبّقت {ctx.changes_made} تعديل. افتح المعاينة الحية."
        else:
            summary = "ما قدرت أكمل المهمة لسبب تقني. جرّب أعد صياغة طلبك أو أعد المحاولة."
    logger.info(f"[agent-stream] finalizing: iterations={iterations} summary_len={len(summary)} html_changes={ctx.changes_made}")
    yield _sse("done", {
        "summary": summary,
        "options": options,
        "iterations": iterations,
        "model_used": model_used,
        "html_updated": ctx.changes_made > 0,
        "tool_log": ctx.tool_log,
    })

    # Persist to DB happens at the endpoint level (we return ctx via closure helpers below)
    # We attach the final state to the generator via a side-channel — see endpoint.
    return
