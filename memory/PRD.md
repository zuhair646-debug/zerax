# Zenrex Farm — PRD (Updated 2026-02 — Surgical Quality Fixes)

## Problem Statement
Arabic-first AI builder for websites/apps/images/videos with credits-based pricing, Stripe payments, background-task persistence, and exportable codebase. Deployed on Hetzner VPS (zenrex.ai).

## Current Status — Healthy, Production Live ✅
- Domain: https://zenrex.ai (HTTP 200 / api/health → healthy)
- Backend: Docker compose, MongoDB local (+ Atlas for prod data)
- Frontend: React PWA, Service Worker v9
- Stripe: Official `stripe` SDK with proxy support
- **Brain v2 + Architecture-Aware Build Protocol + Surgical-First Policy** are LIVE.


### 🔓 Blockers Relaxation (P0) — RESOLVED 2026-02 (LIVE on VPS)
**User Pain (verbatim):** "شيل التعقيدات عنا والموانع. يلا ضبط الامور فحص وضبط. ما يرجع له صفحات بيضاء. خلي شوي عنده امور — حطله قواعد ولا حطله قواعد انه ما يقدر يسوي شي."

**Root cause:** Five Python-level guards inside `freebuild_agent.py` were too aggressive — they returned tool_result errors and removed tools from the toolset BEFORE the AI ever got a chance to call them, even on legitimate first-design or surgical edits. The AI then reported "عندي blockers/constraints" back to the user.

**Fix:** Converted ALL five guards to log-only advisories — the dispatcher proceeds and the AI gets the result it expected. Essential rules KEPT (per "خلي قواعد أساسية"):

| Guard | Before | After |
|---|---|---|
| `DESIGN_LOCKED` | hard error on `write_full_html` | `logger.info` advisory, proceeds |
| `DESIGN_PRESERVATION` (>800 chars) | hard error with `use_apply_section_instead` suggestion | `logger.info`, proceeds |
| `INTENT_LOCK._blocked_tools` | tools removed from toolset | recommended-tool hint only |
| `DESIGN-DESTRUCTION GUARD` (replace + ratio > 4×) | hard block + continue | `design_destruction_advisory` log only |
| `SURGICAL-EDIT GUARD` (unrequested section append) | hard block + continue | `surgical_guard_advisory` log only |
| `SURGICAL-HARDBLOCK` | `write_full_html` removed from toolset | removed entirely |

**ESSENTIAL RULES KEPT (per user "خلي قواعد أساسية"):**
- `BLANK PAGE DETECTOR` — injects warning into AI message when page < 800 chars / ≤ 1 section.
- `PRE-FINISH GATE` — rejects `finish` call when any page is still blank; sets `force_tool_use_next_iter=True`.
- `LYING GUARD` — appends one-shot reminder when user requests an action but assistant returns zero tool_use.
- All tool-level argument validation (id required, html required, etc.)
- Post-write audit (dummy UI / JS handlers / nav graph).
- System prompt section 12 rewritten — removed "ممنوع منعاً باتاً" language, replaced with "يُفضَّل بشدة" advisory.

**Tests:** 64/64 pytest pass (`test_blockers_relaxed.py 8/8`, `test_surgical_fixes.py 27/27`, `test_surgical_fixes_v2.py 23/23`, `test_pre_finish_gate.py 6/6`). Testing agent (iteration_65.json) confirmed 107/107 across all 6 explicit files. Live VPS deployed and healthy (HTTP 200).

**Files changed:**
- `/app/backend/modules/freebuild/freebuild_agent.py` (5 sections + 1 system-prompt rewrite).
- `/app/backend/tests/test_blockers_relaxed.py` (new).
- `/app/backend/tests/test_surgical_fixes.py` (test_hardblock_logic_present_in_source updated).
- `/app/backend/tests/test_surgical_fixes_v2.py` (test_source_contains_guard_label_and_thresholds updated).


## Recent Fixes (Feb 2026)

### 🎛️ Hybrid AI Mode Toggle (P0) — RESOLVED 2026-02-XX (LIVE on VPS)
**User request:** "أبني توليفة: Claude للمحادثة + GPT للتصميم الإبداعي + Claude للتعديل الجراحي. توجل من لوحة Admin يبدّل بين الوضعين."

**Implementation:**
- ✅ New file `backend/modules/freebuild/ai_mode.py` — pure-Python phase classifier + provider picker. No magic numbers, all constants.
- ✅ Two modes: `claude_only` (default, all phases → Claude) and `hybrid` (first_design → GPT-5.5, surgical/edit/debug → Claude).
- ✅ Phase classifier (`classify_phase`): deterministic; first_design = empty project + build verbs, OR explicit rebuild markers (`من الصفر / rebuild`). Surgical = everything else on existing content.
- ✅ Provider picker (`pick_provider`): safe fallback — if `ai_mode=hybrid` but no `OPENAI_DIRECT_KEY`, falls back to Claude.
- ✅ MongoDB persistence via `platform_settings` collection, doc id `ai_mode`.
- ✅ Admin endpoints: `GET /api/admin/ai-mode`, `PUT /api/admin/ai-mode` (both `require_admin`).
- ✅ Admin UI: `AdminAIMode.js` page (route `/admin/ai-mode`) with two cards (Claude Only / Hybrid) and a Shield section listing the 7 guards that protect both modes.
- ✅ Dashboard tile: `admin-tile-ai-mode` in `AdminDashboard.js` for quick access.
- ✅ `_stream_one_provider` now handles `openai_direct` provider key alongside existing `anthropic` / `emergent_anthropic` / `moonshot`.

**Tests:** 77/77 pytest pass (19 ai_mode unit + 8 HTTP smoke + 26 surgical_fixes + 24 surgical_fixes_v2). Zero regression. Iteration_53.json.

**Live verification:** GET/PUT `/api/admin/ai-mode` on `https://zenrex.ai` succeeded end-to-end with admin token. All 5 phase routing combinations verified on the actual VPS container (claude_only/hybrid × first_design/surgical/rebuild).

### 🛡️ Surgical Quality Pack v2 (P0) — RESOLVED 2026-02-XX (LIVE on VPS)
**User Pain (verbatim):** "AI يضيف أقسام مكررة في أسفل الصفحة بدل ما يعدل الموجود، يكدّس كل شي في index.html رغم إن المشروع متعدد الصفحات، ويستخدم write_full_html ويدمّر التصميم."

**RCA (via troubleshoot_agent):**
1. `classify_user_intent` was too permissive — words like "كمّل/أكمل" classified as `new_build` → unlocked `write_full_html` → AI used it on existing projects, hallucinating template sections.
2. After every HTML mutation, Claude only saw `{"ok":true,"length":N}` — never saw the actual new HTML structure → could not detect its own duplicates → kept saying "تم" while page was broken.
3. Multi-page projects had no nudge — AI kept appending sections to `index.html` even when user wanted a separate page.
4. Guards were reactive (block AFTER tool was called, wasting tokens) instead of preventive.

**Fixes Applied (4):**
- ✅ **Fix #1 — Surgical-First Classifier** (`classify_user_intent` at freebuild_agent.py:8085): For any project with `has_existing_content=True`, defaults to `surgical` mode UNLESS user explicitly says rebuild markers (`من الصفر / rebuild / from scratch / احذف كل شي وابدأ`). Tested 12/12 + 26/26 pytest.
- ✅ **Fix #2 — SURGICAL-HARDBLOCK** (freebuild_agent.py:9119): When classifier=surgical AND project has > 500 chars, `write_full_html` is physically removed from the tool list before Claude sees it. Cannot be called even if AI wants to.
- ✅ **Fix #3 — Force Post-Write Verification** (freebuild_agent.py:9734): After every HTML-mutating tool (`apply_section`, `create_page`, `remove_section`, `write_full_html`, etc.), the server runs `list_sections` + Counter to detect duplicate `<section id='X'>` and near-duplicate headings, then injects a verification message into the conversation forcing the AI to fix duplicates via `remove_section` before saying "تم". Also flips `force_tool_use_next_iter=True`.
- ✅ **Fix #4 — Multi-Page Nudge** (freebuild_agent.py:9786 + SURGICAL_EDIT_MICRO_PROMPT): When project has > 1 page AND user mentions "صفحة / كمل" AND AI called `apply_section/op=append`, server suggests `create_page` instead. Multi-Page Awareness rule added to surgical micro-prompt.

**Bonus:** Fixed latent bug in `list_sections` _exec_tool — now honours `page=...` kwarg (previously silently dropped). freebuild_agent.py:2359.

**Verified:**
- Backend pytest: 26/26 pass (`/app/backend/tests/test_surgical_fixes.py`)
- VPS live test: 6/6 classifier cases pass on zenrex.ai
- testing_agent_v3_fork iteration_51 → 100% backend success, no critical issues

### 🔧 Template Trap (P0) — RESOLVED 2026-02 (Previous Session)
**Root cause:** Two pieces of the AI prompt forced a canned single-page template regardless of user intent:
1. `STRICT_PHASE_PROTOCOL_ADDENDUM` → "Progressive Build Protocol" forced Turn-1 to build `apply_section('hero')`+`apply_section('nav')` with `href="#section_id"` anchors PLUS placeholder sections via `apply_section` for every imagined section inside `index.html`.
2. `STRICT_PHASE_PROTOCOL_ADDENDUM` → Phase 2 step 3 mandated "ابنِ Hero + Navbar فقط" with `href="#..."` anchors.
3. `planner.py` had a broken `is_multi_page` detector (checked only for the literal phrase "صفحات متعددة" in `answers["site_structure"]`, but discovery is disabled so `answers` is empty — always defaulted to single-page).

**Fix applied (surgical, no new rules added):**
- ❌ Removed Progressive Build Protocol (placeholder template) from `STRICT_PHASE_PROTOCOL_ADDENDUM`
- ❌ Removed Phase 2 "Hero+Navbar with anchors" forced template
- ✅ Added a single **top-of-prompt "القاعدة العليا"** that overrides everything below: "If user mentioned page names → use `create_page` for separate `.html` files, NOT `apply_section` placeholders"
- ✅ Added new "Architecture-Aware Build Protocol" with explicit Multi-Page vs Single-Page branching
- ✅ Rewrote `planner.py` with `_detect_multi_page_intent()` + `_extract_requested_pages()` — detects from user goal text (Arabic + English), maps to filenames (movies→movies.html, مسلسلات→series.html, etc.)
- ✅ Multi-page plans now emit `create_page(filename)` steps before any `apply_section`
- ✅ 3 new regression tests in `tests/test_brain_v2.py` (all passing — 29/29 total)

**Verified live on zenrex.ai:**
```
Multi-page detected for "صفحة أفلام وصفحة مسلسلات": True
create_page filenames: ['movies.html', 'series.html']
```

## Pricing (USD)
| Package | Price | Credits | Type |
|---|---|---|---|
| Free signup | $0 | 200 | one-time bonus |
| **Ready Sites Trial** | **$9** | **500** | one-off (7 days) |
| **Ready Sites Purchase** | **$79** | **5,000** | one-off (full ownership) |
| Project Pack | $49 | 5,000 | one-off |
| Starter | $19/mo | 2,000 | subscription |
| Pro | $69/mo | 8,000 | subscription |
| Studio | $199/mo | 25,000 | subscription |

**Service costs (`SERVICE_COSTS`):** Image 100 / Video 10s 1,200 / Text 1k tokens 30 / Chat msg 10

## Architecture
### Triple-Layer Credit Guard
1. **Per-endpoint:** `pricing.credits.charge_user(service_key)` atomic deduction + ledger
2. **Backend Middleware:** `credits_guard.py` returns 402 on AI endpoints if `users.credits == 0`
3. **Frontend Global Toast:** `<GlobalCreditsGuard />` calm bottom-right pill on all AI/chat routes

### Stripe Integration (Independent)
- New shim: `/app/backend/modules/billing/stripe_shim.py` uses official `stripe==14.4.0` SDK
- Removed dependency on `emergentintegrations.payments.stripe`
- Auto-routes through Emergent's Stripe proxy if key starts with `sk_test_emergent`
- Works with real Stripe keys (sk_test_xxx or sk_live_xxx) for full independence

### Ready Sites Pay-First Flow (NEW)
1. User picks category → `/ready-sites/preview/{id}`
2. Clicks "Continue" → `/ready-sites/purchase?category=X`
3. Chooses Trial ($9) or Purchase ($79)
4. **Redirected to Stripe Checkout** (USD)
5. After payment → success URL `/billing/success?session_id=…`
6. Billing webhook AUTO-CREATES the FreeBuild project with category context
7. BillingSuccess page polls status, gets `project_id` field, redirects to `/freebuild/chat/{id}?source=ready-sites`
8. User lands in chat with AI greeting asking for store name + logo

## Recent Completed Work (2026-06-20 → 2026-06-21 session)
- Hero Z logo removed | `/pricing` loads PricingV2 | Stripe import made lazy
- **Credits pivot:** PACKAGES simplified, deduction unified, `/generate/video` fixed
- **3-layer guard:** middleware + per-endpoint charge + global toast

## 2026-06-22 Session — "AI Generates Dummy UI" Ultimatum Fix ✅
Root cause: Multiple silent bugs let the AI claim work without doing it:
1. **Intent classifier (`action_pricing.classify_intent`)** missed common Arabic
   spellings (`تنشئ`, `انشئ`, `اضف` without hamza) → preemptive `tool_choice=any`
   never fired → AI responded with text only → counted as "chat" → user charged
   floor with zero work. **Fixed** by hamza-normalization + expanded patterns
   covering colloquial prefixes (تـ/بـ/راح/ننـ).
2. **Lie detector markers** missed celebration phrases like "تم بنجاح",
   "جاهز بالكامل", "ما تم إنجازه". **Fixed** by expanding `FAKE_ACHIEVEMENT_MARKERS`.
3. **In-Turn Dummy Detector (new):** After every `write_full_html`/
   `apply_section`/`create_page`, the server scans the resulting HTML for
   dead buttons (no onclick AND no JS wiring), forms missing onsubmit,
   nav links with `href="#"`, and broken anchors. If found, attaches the
   audit to the tool result AND forces `tool_choice=any` on the next
   iteration so the AI MUST call a repair tool before being allowed to
   write a "تم بنجاح" summary. Function: `_scan_for_dummy_ui()`.
4. **Anchor-to-Page rewriting (new):** `_rewrite_anchors_to_real_pages()`
   runs after every HTML mutation. If `about.html` exists in `ctx.pages`
   and the HTML has `<a href="#about">` with no matching `<section id="about">`,
   the link is auto-rewritten to `<a href="about.html">`. Also handles
   `#home`/`#homepage`/`#main`/`#top` → `index.html`. This is what
   guarantees TRUE multi-page navigation works regardless of what the AI
   writes.
5. **create_page Auto-Wire (improved):** Now ALSO rewrites existing
   `<a href="#stem">` anchor links across every page to point to the new
   file (when no `<section id="stem">` exists locally). Stops the
   "half-wired navbar" pattern where the new page links worked but the
   original index.html still pointed to anchors.
6. **<base href> Injection (new):** Published sites served at
   `/api/.../published-sites/{slug}` (no trailing slash) had broken
   multi-page nav because the browser resolved `about.html` relative to
   the parent URL. Now `_inject_base_href()` injects
   `<base href="/api/freebuild-chat/published-sites/{slug}/">` so all
   relative links resolve correctly in BOTH preview and production.

**Live test results (post-fix):**
- Built portfolio site "تك سعد" with 3 real .html pages.
- Confirmed in headless browser: clicking "من نحن" navigates to
  `/.../teksaad-test/about.html` (real page load).
- Contact form submission triggers HTML5 validation + success message.
- Cart test on "زهور النور" flower shop: 4 add-to-cart buttons all fire
  real `addToCart()`, badge updates 0→2, modal opens with items + total
  (55 ريال computed correctly), localStorage persists.
- 39/39 unit tests pass (11 new dummy detector tests added).

**Files touched:**
- `/app/backend/modules/freebuild/action_pricing.py` (classifier hardening)
- `/app/backend/modules/freebuild/freebuild_agent.py` (Dummy Detector
  + Anchor rewriter + Lie marker expansion + create_page auto-rewrite)
- `/app/backend/modules/freebuild/freebuild_chat.py` (base href injection)
- `/app/backend/tests/test_dummy_detector.py` (NEW — 11 unit tests)

- **Calm UI banners:** smaller pill-style, single tap to /pricing
- **Ready Sites paywall:** PayPal + LemonSqueezy (Stripe fully removed)
- **End-to-end verified:** signup→200 credits, Ready Sites checkout returns real PayPal URL on prod
- **FreeBuild streaming agent now deducts credits per turn** — fixed root cause of "credits not deducting"
- **Removed all role-based credit bypasses** — owner/admin/super_admin no longer skip credit deduction
- **🆕 8 LemonSqueezy variants live + connected on VPS** (1817088 → 1817151)
- **🆕 Custom amount: tiered bonus** — $5–$10K range with progressive gifts up to +500K @ $10K
- **🆕 Pricing UI: strikethrough base + green new total + bonus pill** for cross-cultural clarity
- **🆕 Float credits killed** — backend rounds to int + DB normalized + UI displays integers only
- **🆕 Dashboard/Navbar jitter fixed** — single source `useCreditsGuard`, removed promo top-transition, removed duplicate `/auth/me` fetch
- **🆕 2026-06-21 — UNIVERSAL 50-credit gate enforced across ALL AI chat surfaces (NO role bypass, even owners pay):**
  - `/api/freebuild-chat/project/{pid}/agent-chat-stream` → 402 if balance < 50 (admin bypass removed)
  - `/api/freebuild-chat/project/{pid}/chat` (non-streaming) → 402 if balance < 50 (gate added)
  - `/api/video-studio/chat` → 402 if balance < 50 (gate added)
  - `/api/video-studio/production/producer-chat` → 402 if balance < 50 (gate added)
  - `/api/games/project/{pid}/chat` → 402 with structured detail, owner bypass removed
  - Floor charge `MIN_TURN_CHARGE_TOKENS=1500` on all 3 freebuild agent code paths so credits ALWAYS deduct, even when provider returns zero token counts (root cause of "AI generates for free" bug)
- **🆕 2026-06-21 — PHASES_BY_MODE fix:** `FreeBuildChat.js` sidebar now uses `getPhases(project?.mode)` instead of hardcoded website phases, so APP projects show app phases (تدفق الشاشات / هوية التطبيق / بناء الشاشات / محاكي الجوال) — verified by testing agent

## 🆕 Storage Subscription System (2026-06-21)

Unified storage billing — separated from AI credits. One MB pool across every surface (websites/apps/games/images/videos).

### Plans (monthly recurring via LemonSqueezy)
| Tier | Price | Storage |
|---|---|---|
| Free | $0 | 250 MB |
| Starter | $7/mo | 3 GB |
| Plus ⭐ | $14/mo | 15 GB |
| Pro | $29/mo | 75 GB |
| Studio | $59/mo | 300 GB |

### Grace Period & Recovery
- Payment fail → 10-day grace (email reminders at day 1/5/8 via Resend)
- After grace → files moved to `archived` status (kept on server)
- Archive retention: 6 months → eligible for purge
- Recovery fees: $5 (<1GB) / $15 (1-10GB) / $35 (10-50GB) / $79 (+50GB)
- User must pay recovery fee + renew subscription to regain access

### Implementation
- New module: `/app/backend/modules/storage_billing/__init__.py`
- New collection: `storage_subscriptions` ({user_id, plan_id, status, lemon_subscription_id, current_period_end, grace_started_at, archived_at, archived_size_mb})
- Background loop: hourly check for past_due → archive after 10 days
- New endpoints:
  - `GET /api/storage/plans` — list plans + recovery tiers
  - `GET /api/storage/subscription` — current sub status
  - `POST /api/storage/checkout` — start subscription checkout
  - `POST /api/storage/recovery/checkout` — start one-time recovery
  - `POST /api/storage/webhook` — LemonSqueezy events (subscription_created, payment_failed, cancelled, recovery order)
- Updated `/api/freebuild-chat/storage/usage`:
  - Removed project count limit (unified GB-based quota)
  - Added subscription_status, grace_days_left, archived fields
  - Single helper `_user_total_bytes()` for accurate measurement
- New frontend page: `/billing/storage` with full plan comparison + recovery flow
- Updated `StorageIndicator.js`: context-aware warnings (no more false "تجاوزت الحد" when only over project count)

### Required Owner Action
Create 8 LemonSqueezy Variants and add to `/app/backend/.env`:
- `LEMONSQUEEZY_STORAGE_STARTER` / `_PLUS` / `_PRO` / `_STUDIO` (Subscription products)
- `LEMONSQUEEZY_RECOVERY_SMALL` / `_MEDIUM` / `_LARGE` / `_XL` (One-time products)

## 🆕 Support Tickets System (2026-06-21)

Fully internal ticket system — no WhatsApp, no external email. Telegram-style threaded conversations between user / AI / admin.

### Flow
1. User opens `/support` → "تذكرة جديدة"
2. Claude **auto-triages** on submission:
   - **Refund/استرداد:** AI auto-declines politely per ToS terms, ticket marked `auto_resolved`, **NOT sent to admin** (saves your time)
   - **Technical/Billing:** AI thanks user, asks for screenshots/video if missing, escalates to admin with a 1-line summary
   - **Suggestions/Other:** AI acknowledges politely, escalates to admin
3. User can attach images/videos/PDFs (max 25MB each, max 5 per upload)
4. Admin replies from `/admin/support` — sees the audit snapshot inline:
   - Credits balance, role, storage tier
   - Project count
   - Last 10 transactions
   - Last 10 usage events
   - Storage subscription status
5. Bell notification + unread badge on user's dashboard when admin replies

### Endpoints
- `POST /api/support/tickets` — create + auto-triage
- `GET /api/support/tickets/me` — my tickets
- `GET /api/support/tickets/{id}` — thread
- `POST /api/support/tickets/{id}/messages` — reply
- `POST /api/support/tickets/{id}/upload` — attach files
- `GET /api/support/attachment/{filename}` — serve attachment
- `GET /api/support/unread-count` — badge count
- `GET /api/admin/support/tickets?status=...` — admin list
- `GET /api/admin/support/tickets/{id}` — admin view with audit_snapshot
- `POST /api/admin/support/tickets/{id}/reply` — admin reply (with status change)
- `POST /api/support/ai-quick-answer` — instant FAQ + Claude answer

### Pages
- `/support` — user ticket list + new-ticket form
- `/support/tickets/:id` — threaded conversation (telegram-style)
- `/admin/support` — admin inbox with audit panel + per-user analytics

### Removed
- ❌ Floating `UsageIndicator` ⚡ pill (was duplicating the credits display, confused users)
- ❌ WhatsApp support button → now routes to `/support`
- **🆕 Floating language picker + support widget removed** — cleaner pages
- **🆕 Mobile chat overhaul:** PhaseHeaderPill (animated on phase change), credits + storage popovers visible on mobile, send button always visible, attach supports all file types
- **🆕 Hard credit gate (50 credits min) before any AI turn** in `/agent-chat-stream` + `PendingResumeBanner` ("إكمل ➜") that resumes the user's saved message after recharge
- **🆕 Markdown rendering — mobile-safe:** tables overflow-x-auto, links break-all, words wrap, lists fully styled
- **🆕 Storage popover opens from left on mobile** (was off-screen)
- **🆕 Strict Phase Protocol + Completeness Rule** added to system prompt: AI must complete sentences before tool calls, cannot skip phases, must use competitor research with URLs in Discovery
- **🆕 Apps Builder cleaned + unified:** 3 options (Flutter ⭐ recommended, React Native, Native Swift/Kotlin). Removed "تطبيق قابل للإكمال" (lives in its own /projects/continue section). On selection, creates a FreeBuild project with `mode='app'` and redirects to `/freebuild/chat/<pid>` — SAME chat UX as websites.

## Pending — P1
- 🍋 **LemonSqueezy variant IDs** — user needs to create 2 products in LemonSqueezy dashboard:
  1. "Ready Sites Trial" — $9 USD (one-time)
  2. "Ready Sites Purchase" — $79 USD (one-time)
  Then set `LEMONSQUEEZY_VARIANT_TRIAL` + `LEMONSQUEEZY_VARIANT_PURCHASE` in prod `.env`
- 🍋 **LemonSqueezy webhook endpoint** must be registered in their dashboard:
  `https://zenrex.ai/api/ready-sites/lemonsqueezy/webhook` (events: order_created)
- 🪙 Top-up credits packs (1,000 credits for $9 etc.)
- 💸 Refund credits if external API (OpenAI/Sora) fails after deduction
- 🟢 File upload UI red→green indicator in FreeBuildChat
- 📧 Email Verification on Registration (Resend)
- 🔄 Chat Session Reconnection (SSE re-attach)
- 📱 Wire `CreditsBlockedBanner` inline in other chat pages

## Pending — P2
- Sticky in-page section navigator
- Multi-page generated sites (`/about`, `/contact`)
- Visual Guardian (Vision LLM)
- CI/CD pipeline
- Backfill existing free users to 200 credits

## Refactoring Backlog
- Split FreeBuildChat.js (4500+ lines)
- Split FreeBuild backend chat module (now 6702 lines — urgent)
- Split freebuild_agent.py (5650 lines)
- Consolidate POINTS_CONFIG (server.py)
- Extract shared `require_min_credits(db, user, min)` helper (duplicated in 5 endpoints)

## 🆕 2026-02 — Genius Engineer + Memory + Reality Check + DELETE + Multi-Page
- ✅ NEW `/app/backend/modules/freebuild/global_knowledge.py` — cross-user RAG learning
  - `add_best_practice()` with de-dup by (category, sector, normalised problem)
  - `load_global_knowledge_for_prompt()` injects top-8 practices ranked by success_count + tag overlap
  - `save_learning` tool exposed to AI (87 tools total now)
  - New MongoDB collection `ai_global_knowledge`
- ✅ Genius Engineer Protocol added to STRICT_PHASE_PROTOCOL_ADDENDUM:
  - Zero-Assumptions inspection mandate (read_html_section before any fix)
  - Originality Mandate (8 forbidden template patterns + alternative layouts)
  - Sectoral Mastery (e-commerce / restaurant / health / education / services feature maps)
  - Diagnose-Before-Fix (get_html → audit → test_page → classify → fix → verify)
  - Golden Idea Rule (every meaningful reply ends with 💎 proactive suggestion)
  - Granular Sectioning (5-12 sections per project, each a separate turn)
  - Live Memory feedback loop (memory_save + save_learning hooks)
  - Cost transparency rule
- ✅ Per-operation image charging: `generate_image` now deducts `image_nano_banana` (75c)
  via `charge_user` so images don't hide inside the text token bill
- ✅ **Reality Check Block** (CRITICAL FIX): `_build_reality_check_block(html)` now
  runs at the start of EVERY agent turn (all 3 paths: anthropic, openai-compat,
  stream). Injects ground-truth into the user message: section IDs + headings,
  every existing CTA/button text, inline audit (placeholders/dead-buttons/broken
  anchors), and 5 mandatory rules ("don't suggest existing features", "inspect
  before fix", etc.). FIXES the user-reported bug where AI suggested CTAs that
  already existed and couldn't see/fix real issues in the project.
- ✅ Pytest: 5/5 in test_global_knowledge.py + 9/9 in test_genius_engineer_global_knowledge.py
- ✅ Backend testing agent (iteration_50): 14/14 PASS, no critical/minor blockers
- ✅ Live PROD verified: AI now opens reply with "🔍 قرأت الواقع الفعلي للموقع"
  and correctly identifies when a suggested feature already exists.
- ✅ **Real DELETE capability**: `apply_section` extended with `op='delete'` + NEW
  dedicated `remove_section(ids=[...])` tool. Removes the entire `<section>`
  block AND any matching `<nav>` link. Returns `removed_ids` + `bytes_freed`.
  FIXES user-reported bug: AI claimed "حذفت" without actually deleting.
- ✅ **Multi-page architecture**: NEW project field `pages: {filename: html}` + 
  `active_page` + 4 new tools: `list_pages`, `create_page(filename, title)`,
  `switch_page(filename)`, `delete_page(filename)`. Each page is independently
  edited; `apply_section` operates on the active page only. `index.html`
  cannot be deleted. The agent now creates real `<a href="about.html">`
  multi-page navigation instead of forcing everything into one giant `#anchor`
  scroll page.
- ✅ **Published multi-page serving**: `publish_project` now uploads ALL pages,
  served via:
    `/s/{slug}` → `index.html`
    `/s/{slug}/about.html` → `about.html` etc.
  Nginx rule added on VPS for `^/s/([slug])/([file].html)$`.
- ✅ **Anti-Hallucination Lie Detector (Server Guard)**: NEW post-turn check —
  if assistant says "تم الإنشاء/الحذف" but `changes_made==0`, flags the project
  with `_lie_detected_at` and injects a stinging correction prompt at the
  start of the next user turn forcing the AI to actually call the tool.
- ✅ Updated `STRICT_PHASE_PROTOCOL_ADDENDUM` rules 9 & 10:
  - Rule 9: Zero Lying on Delete (must call `remove_section`, prove via output)
  - Rule 10: Tool-Action Mandate (intent → tool mapping table; any
    completion-claim without tool call = documented lie)
- ✅ **Auto-Republish on Edits (live URL sync)**: After any successful agent
  turn (`changes_made > 0`), if `project.published_slug` exists, the server
  automatically syncs `current_html` + `pages` to `freebuild_published_sites`.
  No need to manually re-publish. FIXES user-reported bug: AI sent old
  published URL after making edits → user saw stale broken version.
- ✅ **PROJECT RAILS block** appended to every system prompt — clearly
  explains the difference between "Editor Preview" (real-time current_html)
  and "Live Published URL" (/s/{slug} auto-synced). Lists exact multi-page
  URLs (`/s/{slug}/about.html` etc) so the AI never guesses or sends stale
  links from memory.
- ✅ **Cache-busting**: `serve_published_site` + `serve_published_subpage`
  now send `Cache-Control: no-store, max-age=0, must-revalidate`. Updated
  VPS nginx `/s/{slug}` rule to remove the 60s edge cache override —
  edits are visible on the live URL instantly (Ctrl+F5 no longer needed).

## 🆕 2026-02 — Strict Credit Deduction (Floor + Ceiling + Iteration Cap)
- 🛡️ **Per-turn hard CEILING**: `MAX_TURN_CREDITS = 500` (≤ $0.50/turn). Even
  if a runaway turn would consume 100k tokens, billing is scaled down so the
  user is never surprised by a 4000-credit drop. SSE response includes
  `credits_capped: bool` + `credits_cap: 500` for full UI transparency.
- 🛡️ **Per-turn FLOOR**: `MIN_TURN_CHARGE_TOKENS = 1500` (~38 credits) fires
  when provider token capture fails — guarantees AI usage can never escape
  billing.
- 🛡️ **Iteration cap**: `max_iterations` reduced from 30/40 → **12** in both
  `run_agent_turn` and `stream_agent_turn`. Prevents runaway loops where
  the AI calls 20+ tools in one turn, each re-sending the full system
  prompt (5K tokens) → 100K total → 2500 credits.
- 🛡️ **Atomic ledger ops**: Verified `deduct_credits` uses MongoDB
  `find_one_and_update` with `{"credits": {"$gte": amount}}` — fully atomic,
  cannot overdraw, every charge logged in `credit_transactions`.
- ✅ Real curl test confirmed: 5814 tokens × 25/1k = **145 credits charged
  exactly** (no surprises). `credits_capped=false`, `credits_cap=500` shown.
- ✅ 4/4 pytest cases in `/app/backend/tests/test_strict_credit_deduction.py`

## 🆕 2026-02 — Action-Based Pricing (Pre-Flight Gate + Op Floors + Cost Preview)
- 🛡️ **New module** `/app/backend/modules/freebuild/action_pricing.py`:
  - `ACTION_COSTS` catalog: 9 action types each with (min, max, recommended_plan)
  - `classify_intent(message)` — regex-based intent extractor (Arabic + English)
  - `preflight_check(balance, message)` — returns 402 payload when balance < action min
  - `compute_op_floor(tool_log)` — picks max op-floor from tools executed this turn
  - `TOOL_OP_FLOORS` mapping tools → minimum credit charge
- 🚪 **Pre-Flight Credit Gate** in `agent-chat-stream` endpoint:
  - Classifies intent BEFORE streaming
  - Returns 402 with rich details (balance, needed, intent, recommended plan,
    recharge_url, and smart Arabic message: "اشحن Indie لتنفيذ 100+ عملية مثل هذه")
  - NO mid-stream credit exhaustion. NO surprises.
- 💎 **Cost Preview SSE event** (fires when max_cost ≥ 200):
  - `event: cost_preview` with `{intent, min_cost, max_cost, current_balance,
    message_ar}` — UI can render a "🎯 هذه العملية ~N-M شعلة" toast
- 💰 **Per-Op Floor enforcement** in deduction:
  - After token-based bill computed, if `compute_op_floor(tool_log) > token_credits`,
    bump effective tokens so floor wins (page_creation always ≥ 200 credits)
  - Prevents AI from running high-value ops cheaply via cached tokens
- ✅ Action cost table (min–max in credits):
  - chat 25–80, inspection 15–50, edit 80–250, section_add 120–350,
    page_creation 200–500, full_site 300–800, deletion 25–60, repair 60–200,
    media +75 per image / +220 per video
## 🆕 2026-02 — Anti-Lazy-Stop: In-Turn Auto-Recovery + Forced Tool Use
- 🚫 **Anti Announce-and-Stop**: New Rule 11 in system prompt — explicitly
  forbids text-only completions when user requested an action. Lists 12+
  Arabic + English "promise" markers (سأبدأ، سأصلح، يبدأ الآن، Let me, etc.).
- 🔄 **In-Turn Stall Recovery (Anthropic only)**: When the AI emits text
  ending with "..." or containing a promise marker but calls NO tool, the
  agent automatically injects a nudge AND retries WITHIN THE SAME TURN (no
  extra billing). Recovery counter `stall_recovery_used` allows up to **2**
  retries per turn.
- 🛡️ **Fake-Achievement Detector**: Catches the worse case — AI claims
  "أصلحت / +3.6 KB محتوى حقيقي" but `ctx.changes_made == 0`. Same in-turn
  recovery cycle, but with a stronger nudge demanding tool calls + audit.
- ⚡ **Forced Tool Use** (`tool_choice={"type": "any"}`): After a stall is
  detected, the **next Anthropic API call** is forced to use a tool. This
  is Anthropic's native server-side constraint — the AI literally cannot
  reply with text-only on the recovery iteration.
- 🔒 **Iteration-scoped flag** (`_force_tools_this_iter`): Snapshot of the
  force flag taken before the producer task runs, so flag mutations in
  the outer loop don't leak into the next iteration. Auto-resets each turn.
- ✅ Verified flow on preview env (logs):
  - `FAKE-achievement (recovery #1) — changes_made=0 but claimed success`
  - `forcing tool_choice=any for this iteration (recovery)`
  - Result: AI emits `event: tool_building` with `write_full_html` →
    real changes happen → user is charged once for the FULL completed
    turn instead of paying twice for promise + fake-claim + finally-real.

## 🆕 2026-02 — IRON-CLAD Anti-Lazy: Preemptive Force + Auto-Refund
- 🔒 **Preemptive Tool Forcing**: When `classify_intent(user_message)` returns
  any action intent (repair/section_add/page_creation/deletion/edit/full_site),
  the **first Anthropic API call is already forced** with `tool_choice={"type":"any"}`.
  The AI literally cannot reply with text-only on iteration #1. Stops the
  "apology + promise + stop" pattern dead in its tracks. Logs:
  `[agent-stream] PREEMPTIVE force_tool_use enabled (intent=repair)`
- 💸 **Auto-Refund on Zero-Change Action Turns**: After the agent loop ends,
  if intent was an action AND `ctx.changes_made == 0`, the system **skips all
  credit deduction entirely**. User pays $0 for failed action attempts.
  Surface field `auto_refunded: true` in SSE `done` payload so the UI can
  show "✋ تم استرداد النقاط — العملية لم تنجح".
- ✅ Verified on preview env: "أصلح المشاكل" intent → PREEMPTIVE fires →
  AI calls `write_full_html` from iteration 1 → no stall → 6 iterations
  later: `html_changes=2`. Real work, no waste.

## 🆕 2026-02 — Design Preservation (Anti-Destructive Rebuild)
- 🎨 **Server-Side Block** on `write_full_html` when `current_html >= 800 chars`
  AND `allow_full_rewrite` flag is not explicitly true. Returns
  `DESIGN_PRESERVATION` error with a friendly Arabic message redirecting
  the AI to use `apply_section`/`create_page`/`remove_section` instead.
- 🔓 **Escape hatch**: `write_full_html(html=..., allow_full_rewrite=True)`
  works when user explicitly asked for "إعادة بناء من الصفر".
- 🎨 **New Rule 12** in `STRICT_PHASE_PROTOCOL_ADDENDUM` — Design Preservation
  Sacred Rule. Explains the destructive-rebuild bug ("AI replaced approved
  design with empty colored boxes when asked to ADD a chat") and lists the
  correct preserving alternatives.
- ✅ Verified: 1,180-char HTML + `write_full_html` → BLOCKED with rich
  error. Same call with `allow_full_rewrite=true` → succeeds. Deployed.

## 🆕 2026-02 — Unified Site Integration (Auto-Wiring + Rule 13)
- 🔗 **Auto-Wiring on `create_page`**: when a new page is created, the
  server automatically injects a `<a href="filename.html">` link inside
  the existing `<nav>` of `index.html`. If no nav exists, it builds a
  minimal one with the new page link + a "🏠 الرئيسية" homelink. Idempotent
  (won't duplicate links). Returns `nav_link_auto_wired: bool` in the
  response so the AI can confirm to the user.
- 🔗 **NEW Rule 13** (Unified Site Integration Mandate) — the longest +
  most explicit rule in `STRICT_PHASE_PROTOCOL_ADDENDUM`. Lists 5 destructive
  patterns ("orphan chat page", "settings without nav link", "buttons
  without onclick") and 5 correct patterns (chat as a `<section>` in main
  page, every button with real `onclick`/`href`, audit_html before claiming
  done). Includes concrete code examples for AI chat widget, button wiring,
  and form submission.
- ✅ Verified end-to-end: 3 scenarios passed
  - Scenario A: existing nav → link injected inside it
  - Scenario B: no nav → minimal nav built with home + new link
  - Scenario C: multiple pages → 1 link each, no duplication

## Test Credentials
- Admin: admin@zenrex.ai / Zenrex@2026 (PROD DB only)
- Prod Test User: test_zenrex_2026@example.com / Test@Pass2026!

## Deployment
`bash /app/deploy/deploy.sh zenrex.ai` — backend recreate ~3 min for pip install.

## Verified End-to-End (curl on production zenrex.ai)
- ✅ Fresh signup → 200 credits hadyya
- ✅ /api/billing/packages → 6 packages (Trial + Purchase + Project + Starter + Pro + Studio)
- ✅ Ready Sites Trial checkout → real PayPal URL
- ✅ Ready Sites Purchase checkout → real PayPal URL
- ✅ Credits=0 → 402 across all AI endpoints
- ✅ `charge_user` now deducts from admin/owner accounts too (10100 → 10085 confirmed)
- ✅ FreeBuild streaming agent now tracks input/output tokens via `final_msg.usage`
- ✅ Auth endpoints unaffected
- ✅ NEW: Global knowledge module retrieves seeded restaurant/ecommerce practices and
  injects them into every chat turn's system prompt
