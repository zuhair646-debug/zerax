# Zenrex — Multi-tenant AI Commerce Platform (PRD)

## Original Problem Statement
Build "Zenrex" — a multi-tenant Saudi/Arab AI commerce platform with:
1. Conversational FreeBuild chat interface for building sites/apps from scratch
2. Smart Orchestrator unifying AI models (Anthropic Claude)
3. Ready Sites module (template-first)
4. Integrated Video Studio for AI-generated promo videos
5. Driver App + Delivery management (Haversine + dynamic pricing)
6. Global & local payment gateway catalog
7. Standalone professional Admin Dashboard with real-time KPIs and AI workspace

## Financial Model (Confirmed by User — Feb 2026)
**Tech-partner only, NO commission on sales.** Revenue from:
- 💳 Monthly subscriptions (99-299 SAR/month tiers)
- ⚡ AI point packs (1000/2000/5000/10000)
- 🚚 Delivery service fees (from drivers' withdrawals, not merchants)
- 🛠️ One-time add-ons: domain, custom email, premium template, mobile app

## Current State (Feb 2026)


### 🔧 Feb 13 2026 — AutoCoder Desktop Tools Parity Fix

**Problem:** `/admin/autocoder` chat was missing the `desktop_*` tools (only FreeBuild had them).
The AI kept hallucinating fake 6-char pairing codes that the server rejected.

**Root cause:** AutoCoder's `_stream_direct_anthropic` uses its own `ANTHROPIC_TOOLS`
list + `execute_autocoder_tool` dispatcher (separate code path from FreeBuild's
`run_agent_turn`). The desktop tools were registered only on FreeBuild's side.

**Fix in `/app/backend/modules/autocoder/__init__.py`:**
1. Imported `DESKTOP_TOOL_SCHEMAS`, `DESKTOP_TOOL_NAMES`, `dispatch_desktop` from
   `..freebuild.desktop_agent_tools` and `DESKTOP_OWNER_ADDENDUM` from `..freebuild.freebuild_agent`.
2. Added a `_AUTOCODER_CONV_ID_VAR` ContextVar (set inside `/chat` `gen()`) so the
   desktop dispatcher knows which pairing slot to use — the AutoCoder `conv_id`
   doubles as the desktop `project_id`.
3. Appended `DESKTOP_TOOL_SCHEMAS` to `ANTHROPIC_TOOLS`.
4. Registered async wrapper handlers in `TOOL_HANDLERS` for each of the 4 desktop
   tools that build a `_DesktopCtx(project_id=conv_id)` on the fly.
5. Injected `DESKTOP_OWNER_ADDENDUM` (strict verbatim-code rules + visible-pacing
   policy) into both `sys_prompt_full` (alt providers) and `sys_prompt_text`
   (Anthropic direct stream).

**Verified end-to-end:** `python3 /tmp/test_autocoder_desktop.py` →

### 🔧 Feb 13 2026 (later) — Production deploy + 3 root-cause fixes

**Root cause discovered**: Production `zenrex.ai` Desktop Agent failure was a chain of issues, NOT a single bug:

1. **AutoCoder missing desktop tools** (fixed earlier) — wire `desktop_*` into ANTHROPIC_TOOLS.
2. **Git push blocked 92 commits** — leaked `ghp_FhBF...` token in old commit `b697af6/memory/test_credentials.md:75` triggered GitHub secret-scanning. Used `git filter-repo --replace-text` to scrub the secret across all history, then force-pushed.
3. **VPS deploy missed desktop_agent dir** — `/opt/zerax/desktop_agent/` exists on host but wasn't mounted into Docker container; added two volume mounts (`/desktop_agent` + `/app/../desktop_agent`).
4. **`BACKEND_URL` pointed at preview** — production's `.env` had `BACKEND_URL=https://ai-cinematic-hub-2.preview.emergentagent.com` so the AI's `desktop_pair` tool generated codes in production's DB but pointed users to download from PREVIEW. Updated to `https://zenrex.ai` and force-recreated the container.

**Plus 2 quality-of-life fixes** in `/app/desktop_agent/zenrex_gui.pyw` (v0.5.2):
- Tight reconnect loop after clean server close → now respects backoff + breaks on server-error.
- Server-side TTL: `PAIRING_TTL_SECONDS = 24h` (was 10 min). Once WS pairs successfully, pairing extended to 30 days.

**Verified E2E on production**: AutoCoder chat → `desktop_status` → `desktop_pair` → returns code `W6EMP7` valid 24h in MongoDB → reply contains `iwr https://zenrex.ai/api/desktop-agent/bootstrap.ps1 -useb | iex` ✅


- AI calls `desktop_status` → `desktop_pair` in correct order.
- Real code `NSLBBZ` appeared verbatim in the assistant reply.
- Full `display_block` (PowerShell command + download URL) reproduced exactly.

### 🔧 Feb 13 2026 (final batch) — UX wins + Trading visible + Desktop Code Bar

**1. Trading tile in Admin Dashboard**
`AdminDashboard.js` `quickActions` was missing a tile for `/admin/my-trading`.
Added "تداولي الذكي 📈" (TrendingUp icon, green gradient).

**2. Frontend was never rebuilt on prod VPS**
The VPS had source pulled (`MyTradingDashboard.js` present) but
`/opt/zerax/frontend/build/` was stale (Jun 11). Now I build locally with
`REACT_APP_BACKEND_URL=https://zenrex.ai yarn build` and rsync to VPS:
```
rsync -avz --delete /app/frontend/build/  root@…:/opt/zerax/frontend/build/
ssh … 'systemctl reload nginx'
```
Bundle hash `main.9f9d2584.js` confirmed on production.

**3. Always-visible Desktop Pairing Code widget**
The owner asked: "show me the code in the chat itself, don't make me ask the AI
every time". Built `DesktopCodeBar` React component in `AdminAutoCoder.js`:
- Top of the chat area, shows the current 6-char code in monospace
- Click-to-copy with toast
- Status dot (amber → emerald pulse when WS connects)
- Refresh button mints a new code on demand
- Polls `/api/autocoder/desktop-code` every 8s for live status

Backend endpoint `GET /api/autocoder/desktop-code` (owner-only,
`X-AutoCoder-Token`) uses a fixed `project_id = "owner-autocoder-desktop"` —
the same slot the AI uses (`_desktop_wrapper` updated to bind to the same
project_id). So a code copied from the bar is identical to whatever the AI
would generate, and `desktop_act` from chat works the moment the user pairs.


- No 0/O/I/1 characters; charset matches `[A-HJ-NP-Z2-9]`.


### 🔧 Feb 13 2026 (FINAL ROOT CAUSE) — Nginx WebSocket proxy fix

**The smoking gun**: Even with the AI generating real codes and the Desktop
Agent .exe being correct, every pairing attempt returned `HTTP 404` on the
WebSocket upgrade. Nginx was treating `wss://zenrex.ai/api/desktop-agent/ws`
as plain HTTP because the WebSocket upgrade headers were never wired.

**Fix in `/etc/nginx/sites-enabled/zenrex` (also copied to `sites-available/`)**:
Added a NEW `location ~ ^/api/(desktop-agent/ws|local-browser/ws|.*/ws($|/))` block
BEFORE the generic `location /api/` with:
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_read_timeout 86400s;
proxy_buffering off;
```

**E2E verified**: external `wss://zenrex.ai/api/desktop-agent/ws?code=TFZPJZ`
returns `{"type":"paired","project_id":"owner-autocoder-desktop","message":"✅
Connected to Zenrex (Desktop Agent)"}`. Owner can now pair the .exe from
zenrex.ai successfully.

**Companion frontend hardening (commit `bf1984a`)**:
The `DesktopCodeBar` previously flipped `loading=true` on every 8s background
poll. If any poll failed silently (e.g. JWT race condition between tabs), the
code visually reset to "......". Refactored to keep last-known code and
short-circuit `loading` on background polls. Status dot also surfaces error
messages via tooltip.




### 🖥️ Jun 12 2026 — Phase 9: Desktop Agent (Native OS Control) — 68 total tools

**Problem:** Chrome Extension only controls browser tabs. User explicitly asked the AI
to control their physical laptop — move mouse, type, open apps, save files to Downloads.

**Shipped:**
- 📦 **Downloadable Desktop Agent** (`/api/desktop-agent/download` → `ZenrexDesktopAgent.zip`).
  Backend generates ZIP on-the-fly with `config.json` auto-baked with the right WebSocket URL.
- 🛠 Cross-platform installer scripts: `install.sh`/`run.sh` (Mac/Linux) and `install.bat`/`run.bat` (Windows).
  Creates an isolated `.venv` so the agent doesn't pollute system Python.
- 🔌 **WebSocket relay** `/api/desktop-agent/ws?code=...` — pairs the running script
  to a project, routes commands both ways, with proper timeout / disconnect handling.
- 🤖 **4 new AI tools (OWNER-only):**
  - `desktop_pair` — issues a 6-char code + ZIP download URL.
  - `desktop_status` — checks live connection.
  - `desktop_screenshot` — JPEG of owner's primary display (down-scaled to 1600px).
  - `desktop_act(action, params)` — executes a single OS action.
- 🖱 **Supported actions** in `zenrex_agent.py`:
  `move_mouse`, `click`/`double_click`/`right_click`, `type` (Unicode via clipboard fallback),
  `press_key`, `scroll`, `download_file`, `open_app`, `open_url`,
  `cursor_position`, `screen_size`, `list_dir`, `read_file`, `write_file`,
  `make_dir`, `run_shell` (gated by `--allow-shell`).
- 🛡 Safety: PyAutoGUI FAILSAFE (corner-mouse abort), shell disabled by default,
  pairing codes expire in 10 min, only one connection per project, all traffic over `wss://`.
- ✅ 10 unit tests in `test_desktop_agent_relay.py` all green
  (pairing, round-trip with fake WS, timeout handling, owner-only enforcement, tool layer).

**Files:**
- `/app/desktop_agent/zenrex_agent.py` — the main agent script (~430 lines).
- `/app/desktop_agent/install.{sh,bat}`, `run.{sh,bat}`, `requirements.txt`, `README.md`.
- `/app/backend/modules/freebuild/local_browser_relay.py` — extended with desktop endpoints.
- `/app/backend/modules/freebuild/desktop_agent_tools.py` — new tool implementations.
- `/app/backend/modules/freebuild/freebuild_agent.py` — schema + dispatcher + OWNER_ONLY wiring.
- `/app/backend/tests/test_desktop_agent_relay.py` — 10 tests, all passing.


### 📤 Jun 12 2026 — Phase 8: File Sharing + Phase 7: Owner-only Permissions (64 total tools)

**Phase 8 (file sharing):** User reported the AI couldn't deliver a file to him. Investigation
showed this was the AI being honest about a real gap — there was no tool to push files from
the server workspace to the user's device. Shipped:
- 📤 `share_file_with_user(path, label, ttl_hours)` — copies workspace file to a tokenized public
  endpoint and returns a download URL the chat renders as a clickable link.
- New route `GET /api/freebuild-chat/shared/{token}` serves the file with proper filename.
- Tracked in `freebuild_shared_files` collection. Tokens via `secrets.token_urlsafe(16)`.
- Chrome Extension `.zip` published at `https://zenrex.ai/static/downloads/zenrex-extension.zip`.

**Phase 7 (owner-only permissions):**
- 11 high-risk tools (`local_browser_*`, `run_shell`, `db_query/count`, `send_email/sms`, `deploy_to`,
  `github_create_repo/push_file`) restricted to platform owner (role=owner/admin/superuser).
- `tools_for_user(is_owner)` filters the schema sent to Claude. Owner = 64, customer = 53.
- Double-safety: `_dispatch_tool` rejects owner-only tool calls with `permission_denied:true`.
- New `MODE_ADDENDUM_OWNER_ASSISTANT` persona — addresses the owner directly, manages the whole
  platform (merchants/orders/drivers), produces daily reports.
- Route hookup: `freebuild_chat.py` reads `user.role`, passes `is_owner=True` only for admins.

### 🖥️ Jun 12 2026 — Phase 6: Unified Developer Mode + Local Browser Control (63 total tools)

User mandate: "وحّد AutoCoder مع FreeBuild + أضف تحكم الشاشة الفعلي (يدخل لابتوبي ويسوي امامي)".

**Two big shifts shipped:**

#### A. AutoCoder → FreeBuild Unification
- Added `MODE_ADDENDUM_DEVELOPER` to `freebuild_agent.py` — when `project.mode == "developer"`, the system prompt gains a "senior software engineer" addendum that focuses on programming + DevOps.
- New routes in `App.js`:
  - `/admin/zenrex-coder` → redirects to `/freebuild/chat?mode=developer`
  - `/dev` → same shortcut
- The user can now do ALL programming via the unified 63-tool engine instead of the old AutoCoder (multi-LLM, ~15 tools, no browser use, no audit).
- Old `autocoder` module left in place for backward compat with admin tooling (status, key-unlock, etc.) but the chat path is now FreeBuild.

#### B. Local Browser Control (Chrome Extension)
The AI can now drive the **user's own Chrome** — operating on his REAL signed-in tabs (Gmail, social media, dashboards, GitHub, ad managers) — and the user watches it happen LIVE on his actual screen.

**New backend module:** `/app/backend/modules/freebuild/local_browser_relay.py` (~170 lines).
- `POST /api/local-browser/pair` → generates a 6-char pairing code, valid 10 min.
- `GET  /api/local-browser/status?project_id=...` → connection check.
- `WS   /api/local-browser/ws?code=...` → extension connects here; bound to project_id.
- Helpers `send_command_to_extension(project_id, action, params)` for the AI tools to use.
- `_PENDING_RESPONSES` futures map → request_id-based async response routing.
- Registered in `server.py` as a top-level FastAPI router.

**New AI tools (in `browser_use_tools.py`):**
- 📱 `local_browser_pair()` — returns 6-char code + Arabic instructions.
- 🔌 `local_browser_status()` — checks WS connection.
- 🖥️ `local_browser_act(action, params)` — sends a command to the extension. Actions: `navigate`, `open_tab`, `list_tabs`, `get_url`, `screenshot`, `click`, `type`, `scroll`, `eval`.

**New Chrome Extension (`/app/chrome_extension/`):**
- `manifest.json` — Manifest V3, permissions: tabs, scripting, activeTab, storage, notifications, `<all_urls>`.
- `background.js` (~190 lines) — persistent WS connection with auto-reconnect; dispatches AI commands to active tab via `chrome.scripting.executeScript`; click/type/scroll/eval handlers inside page context.
- `popup.html` + `popup.js` — RTL Arabic UI: paste pairing code → 'ربط' → status panel (✅ connected / ❌ disconnected); unpair button.
- Generated 16/48/128px gold-on-black "Z" icons.
- `README.md` with install instructions (Developer mode → Load unpacked).

**Privacy model:**
- Extension reads no cookies/passwords; only sees the rendered DOM.
- Sessions stay on the user's machine.
- Disconnect anytime via popup → unpair.
- One pairing per project.

**Deployed:** `https://zenrex.ai/api/local-browser/pair` returns valid codes in production. Backend running.

**What's NOT shipped (next iteration):**
- Chrome Web Store listing (requires $5 developer account + review).
- Live screencast / video stream of the AI's actions (currently shows command-by-command log; user watches the actual browser).
- E2E test suite for extension (Playwright Extension testing is complex).

### 🌐 Jun 12 2026 — Phase 5: Browser Use — Vision-guided autonomous browsing (60 total tools)

User mandate: "نقدر نخلي الذكاء يستخدم الجهاز مباشرة + يدير حساباتي". Shipped a
complete browser-automation suite where the AI uses Playwright + Claude Vision
to log into the user's accounts and perform tasks on their behalf.

**New module:** `/app/backend/modules/freebuild/browser_use_tools.py` (~480 lines).

**Tools added:**
- 🌐 `browser_start(account_label?, headless?)` — opens a real Playwright Chromium session. If `account_label` matches a previously-saved login, the session loads ALREADY-signed-in via encrypted storage_state. Returns `session_id`.
- ↗️ `browser_goto(session_id, url, wait_seconds?)` — navigates + returns screenshot + title + final URL.
- 🧠 `browser_act(session_id, instruction, max_steps?)` — **the autonomy loop.** Up to 8 cycles of: take screenshot → send to Claude Vision with structured JSON-action system prompt → parse decision {action: click|type|press|scroll|goto|wait|done|give_up} → execute on Playwright page → repeat. Returns full step log + final screenshot.
- 📸 `browser_screenshot(session_id, full_page?)` — manual capture.
- 💾 `browser_save_session(session_id, account_label)` — persists cookies + localStorage **Fernet-encrypted** to `freebuild_browser_sessions` collection. Next `browser_start` with same label = instant signed-in.
- 📋 `browser_list_accounts()` — list saved browser logins for this project.
- 🛑 `browser_close(session_id)` — cleanup.

**Architecture:**
- Module-level `_SESSIONS` dict keyed by `session_id` (in-memory).
- 30-min idle timeout with auto-cleanup.
- All sessions strictly scoped to `project_id` (cross-project access rejected).
- Storage state encrypted at rest using existing Fernet key.

**Vision system prompt** (in `_BROWSER_ACT_SYSTEM_PROMPT`): forces Claude to reply with ONLY a JSON object per step, supports text-based + CSS selectors, refuses destructive actions without explicit user confirmation.

**Tests:** 14 new pytest cases at `/app/backend/tests/test_browser_use_tools.py` — including real-browser tests that visit example.com, save/reload storage state encryption round-trip, cross-project isolation. **79/79 total advanced-tool tests passing.**

**Infrastructure:** Playwright chromium-headless-shell v1217 installed on the VPS at `/pw-browsers/`.

**Deployed:** Synced to `zenrex.ai` VPS, backend restarted.

### 🧠 Jun 12 2026 — Phase 4: Real Plan Tracking + Persistent Memory + Comprehensive Audit (53 total tools)

User mandate: "ربط الخطة بالحقيقة + ذاكرة مستديمة + تدقيق شامل من الصفر إلى الإنتاج".
Shipped 6 new tools + frontend cards that close 3 critical gaps:

**New module:** `/app/backend/modules/freebuild/memory_audit_tools.py` (~430 lines).

**Tools added:**

🔄 **Plan Tracking (real progress):**
- `update_plan_step(plan_id, step_index, status, note?)` — AI marks each step `in_progress` / `done` / `failed` as it works through a plan. The `PlanTaskCard` in the UI now reads these REAL events instead of the previous timer-based animation. Steps show actual completion + notes.

🧠 **Persistent Memory (across sessions):**
- `memory_save(key, value, scope)` — scope=`project` (this project) or `merchant` (all merchant's projects).
- `memory_recall(key)`, `memory_list()`, `memory_delete(key)`.
- **Auto-injection:** `freebuild_agent.py` now calls `load_project_memories_for_prompt()` once at the start of every turn and PREPENDS the formatted memory block to the system prompt. So the AI literally cannot forget customer preferences/brand facts/decisions.
- Storage: new `freebuild_memories` collection. Max 1000 chars per value, snake_case keys.

🔍 **Comprehensive Audit:**
- `audit_project(include_visual_test?, include_specialists?, live_url?)` — runs in this order: HTML validation → JS lint → live Playwright test (test_page) → 4 PARALLEL specialist reviews (security_auditor, performance_optimizer, seo_strategist, accessibility_auditor) via the existing `delegate` tool. Returns scored report per category + overall grade (🟢 ممتاز / 🟡 جيد جداً / 🟠 يحتاج تحسين / 🔴 ضعيف). 30-60s total. Persisted to `freebuild_audits`.

**Frontend (`FreeBuildChat.js`):**
- `PlanTaskCard` rewritten: now reads `updates[]` prop derived from `liveSteps` of all `update_plan_step` events matching the same `plan_id`. Shows real status per step, in-progress ring animation, failure cross icon, per-step notes.
- New `AuditReportCard` component: header with overall grade + score, expandable per-category cards (HTML / JS / Visual / Security / Performance / SEO / Accessibility), color-coded scores (🟢 >90, 🟡 75-90, 🟠 60-75, 🟠 40-60, 🔴 <40).
- `update_plan_step` tool calls are hidden from the live steps panel (they silently update the card).

**System prompt:** New section "تتبّع الخطط + الذاكرة الطويلة + التدقيق الشامل" with explicit usage rules.

**Tests:** 14 new pytest cases in `/app/backend/tests/test_memory_audit_tools.py`. **65/65 total advanced-tool tests passing** across Phase 1-4.

**Deployed:** Synced to `zenrex.ai` VPS, backend restarted, frontend build pushed.

### 🧠 Jun 12 2026 — Phase 3: Smart Workflow Tools (47 total tools)
Following user mandate to make Zenrex AI surpass E1 (the dev agent), shipped
3 high-leverage tools that close the gap with senior human engineering:

**New module:** `/app/backend/modules/freebuild/workflow_tools.py` (~280 lines).

**Tools added:**
- 🔌 `ask_user_inline(question, options[2-6], allow_free_text, context)` — Pauses the agent mid-turn and emits a sentinel that the frontend `InlineChoiceModal` detects → user clicks an option (or types free text) → user's choice becomes their next chat message → agent resumes. **HUGE upgrade** vs burying questions in prose.
- 📋 `plan_task(title, steps[2-12], estimated_minutes)` — Announces a structured roadmap BEFORE multi-step tasks. Persisted to `freebuild_plans` collection so the UI can re-render and track per-step status. Forces transparency.
- 🧠 `delegate(role, task, context)` — Spawns a focused Claude Haiku 4.5 call with a role-tuned system prompt. 7 specialist roles: `designer`, `copywriter`, `security_auditor`, `performance_optimizer`, `data_analyst`, `seo_strategist`, `accessibility_auditor`. Returns the specialist's analysis for the main flow to incorporate.

**Frontend (`/app/frontend/src/pages/FreeBuildChat.js`):**
- Added `InlineChoiceModal` component (cyan-themed, RTL, options as buttons + optional free text input + Enter-to-submit).
- SSE `tool` event handler now detects the `ask_user_inline` sentinel (kind=`choice` + `pending_user_input`) → pops the Modal automatically.
- Picked option is pre-filled in the chat input — user reviews and hits send to continue.

**System prompt:** New "Smart Workflow" section with the 3 tools and explicit usage rules (e.g. "after `ask_user_inline` STOP calling other tools this turn").

**Tests:** 13 new pytest cases at `/app/backend/tests/test_workflow_tools.py` covering wiring + each tool's contract + persistence + a REAL Anthropic delegate call. **13/13 passing.** Combined with Phase 1 + Phase 2, **51/51 total advanced-tool tests passing.**

**Deployed:** Synced to `zenrex.ai` VPS, backend restarted.

### 🚀 Jun 12 2026 — Phase 2: Software Engineer Mode (14 advanced tools)
Following user mandate "أبي الذكاء يكون أفضل من أي شيء — أضف كل الأدوات بلا حدود",
shipped a second wave of 14 capability tools that transform Zenrex AI from a
"single-page HTML builder" into a full-stack software engineer:

**New module:** `/app/backend/modules/freebuild/advanced_tools.py` (700 lines, isolated from `freebuild_agent.py`).

**Tools added (now 44 total in TOOLS_SCHEMA):**
- 🔥 `run_shell(command, timeout, cwd)` — Sandboxed bash per-project at `/tmp/zenrex_ws/{project_id}/`. Network on, 120s max, 100KB output cap. Forbidden patterns: `rm -rf /`, `sudo`, fork bombs, `/etc/passwd` etc.
- 👁️ `analyze_file(file, question)` — Vision/Audio AI via Emergent LLM Key. Routes by extension: images → Claude vision; PDFs → DocumentContent (with `pdftoppm` fallback); audio → OpenAI Whisper transcribe → Claude answer; text → Claude.
- 📁 `read_file / write_file / list_files / delete_file / move_file` — Multi-file workspace per project (5MB cap, 200 files cap).
- 🗄️ `db_query / db_count` — Read-only MongoDB access scoped to project's `merchant_id`. Whitelist: products, store_products, orders, delivery_orders, customers, drivers, deliveries, freebuild_chat_projects.
- 🚀 `deploy_to(provider, project_name)` — Deploy to Vercel/Netlify via their APIs (with `vercel_token`/`netlify_token` from saved credentials or env). Cloudflare Pages and GitHub Pages routed via existing tools.
- 🧪 `run_e2e_test(base_url, steps[])` — Playwright multi-step flow runner. Actions: goto, click, fill, wait, assert_text, screenshot. Returns per-step pass/fail + final screenshot.
- 📧 `send_email(to, subject, html, from)` — Resend API.
- 📱 `send_sms(to, message)` — Twilio REST API.
- 🎬 `generate_video(prompt, model, duration, aspect_ratio, image_url)` — fal.ai video generation. Supports Hailuo / Kling / Luma Dream Machine.

**Env-var aliases:** `_get_cred()` now auto-resolves multiple common env var names (e.g. `RESEND_API_KEY` → `resend_key`), so already-configured keys in `/app/backend/.env` work without re-saving.

**Pre-configured keys discovered in `.env`:**
- `FAL_KEY` ✅ — video generation works out of the box.
- `VERCEL_TOKEN` ✅ — Vercel deploys work.
- `RESEND_API_KEY` ✅ — email sending works.

**Tests:** 25 new pytest cases at `/app/backend/tests/test_advanced_tools.py` covering wiring (schemas + labels + sentinel), shell sandbox safety, file system CRUD, path traversal blocking, size limits, DB whitelist enforcement, and "needs_credential" branches for all third-party tools. **25/25 passing.**

**System Prompt:** Added a new "Software Engineer Mode" section listing all 14 advanced tools with usage hints in Arabic.

**Deployed:** Synced to `zenrex.ai` VPS via `/app/deploy/deploy.sh` + `docker compose restart backend`.

### 🆕 Jun 12 2026 — AI Brain Limitlessness (Anti-Hallucination + Universal Capability)
The user complained the AI was repeatedly lying about API keys ("this key doesn't work")
even when the keys were perfectly valid. Root cause: AI had NO tool for GitHub, NO way to
actually test a credential, and the prompt didn't forbid hallucinated key-status claims.

**Fix shipped (`/app/backend/modules/freebuild/freebuild_agent.py`):**
- **9 new tools** added to the unified Zenrex AI Brain (total now: 30 tools):
  - `save_credential(service, value, label)` — encrypted-at-rest storage
  - `validate_credential(service)` — **real HTTP** test against GitHub / ElevenLabs / OpenAI / Anthropic / Stripe / fal.ai / Tavily
  - `list_credentials()` / `delete_credential(service)`
  - `recommend_service(category, requirements, region)` — built-in catalog of 16 categories × 3 services (hosting, payments, email, sms, storage, auth, database, analytics, cdn, domain, image_ai, video_ai, voice_ai, llm, monitoring, backup) with pricing + signup URL + step-by-step Arabic instructions to obtain the API key
  - `github_list_repos()` / `github_create_repo()` / `github_push_file()` / `github_get_file()` — full GitHub Contents API
- **System prompt hardened** with a "Sacred Credential Rule": AI MUST call `validate_credential` before claiming any key is broken — hallucinating key status now constitutes "betrayal of the customer".
- **Frontend modal** (`/app/frontend/src/pages/FreeBuildChat.js`): the `request_credential` sentinel now triggers a secure password-input modal with show/hide toggle and `data-testid` markers.
- **GitHub PAT** saved as default env var (`GITHUB_PAT` in `/app/backend/.env`) — auto-used by all `github_*` tools when no per-project credential exists.
- **13 pytest regression tests** at `/app/backend/tests/test_freebuild_credentials_and_github.py` — all passing, including REAL API calls against GitHub + a deliberately-fake-key test that asserts HTTP 401 (proving no hallucination).
- Deployed to VPS `zenrex.ai` via `/app/deploy/deploy.sh`.

### ✅ COMPLETED in admin.html (Merchant Control Panel)
- **Dashboard**: Live KPIs (clickable), interactive SVG chart with hover tooltips,
  Top Products clickable, recent orders, **AI Weekly Report card** (dismissible)
- **Products + Product Studio** (3 tabs, fullscreen toggle):
  + **Stock management** (Feb 2026): SKU, low-stock threshold alert, out-of-stock badges
  + **Expiry tracking** (Feb 2026): manufacturing date, expiry date, "ينتهي خلال X يوم" warning, color-coded badges on cards
- **PDF Reports** (Feb 2026, NEW):
  + 6 report types: Sales, Products, Customers, Inventory, ZATCA, Monthly Summary
  + Real PDF generation via jsPDF (downloadable A4)
  + WhatsApp share button (wa.me with formatted summary text)
  + Email share button (mailto: prefilled)
- **ZATCA Phase 2 E-Invoice** (Feb 2026, NEW, mock):
  + Merchant config: VAT (15-digit), CR, name (ar/en), address
  + CSR generation + CSID upload UI
  + Environment switch (Sandbox / Production)
  + Sample invoice generator with valid UBL 2.1 XML structure
  + Real TLV QR code (tags 1-5) rendered via qrcode.js
  + PDF/A-3 download (with embedded XML reference)
- **Campaign Builder** (Feb 2026, NEW):
  + 5-step wizard modal (basic info → audience → message → channels → budget)
  + Audience targeting: segments (VIP/new/inactive/repeat/all), interests (7 categories), age range, gender
  + 6 send channels (WhatsApp/SMS/Email/Push/Instagram/Snapchat) with per-channel cost
  + Live audience + cost estimation
  + Coupon attachment, preview button, scheduled launch
- **Original Product Studio** (kept):
  1. Basic Info — image upload, name, price, stock, category
  2. Creative Studio — 5 types (product/logo/banner/section/animated) +
     bg-color/frame-color/aspect pickers
  3. Deep AI Analysis — 12 sections: title, what's new, comparison, features,
     benefits, usage steps, side effects, specs, colors, sizes, warranty, official URL
- **Video Studio** (5 tabs, fullscreen, dark Zenrex theme):
  1. Script (Gemini storyboard with 44 dialects + 12 voices)
  2. Scenes (editable storyboard, approve per scene)
  3. Images (Gemini Nano Banana, approve per image, 8pts each)
  4. Voice (Zenrex TTS, preview before approve, 5pts)
  5. Final Video (ffmpeg merge, 30pts on click only)
  + Working mic (Web Speech API, dialect-aware)
  + Voice preview button
  + Real-time cost estimator
- **Delivery** with auto-dispatch:
  - Master toggle + per-order auto-assign button
  - Settings: radius, grouping, max orders/driver, priority, withdraw fee
  - Driver pay model per driver (commission % or monthly salary + bonus)
  - 5 payout methods (bank/STC Pay/urpay/PayPal/cash)
- **Smart Management**:
  - Auto-post to 7 social platforms (Instagram, TikTok, X, Snapchat, FB, WhatsApp, Telegram)
  - Customizable post template with variables
  - 5 timing options (immediate/+15min/+1hr/peak/manual)
  - Smart Replies: 2 modes (canned free / AI 1pt per reply)
  - Personality config, daily limit, auto-handoff to human
- **Services Catalog** (7 services with auto-activation):
  1. Custom domain (99 SAR/year)
  2. Branded email (49 SAR/year)
  3. Premium template (199 SAR one-time)
  4. iOS/Android app (999 SAR one-time)
  5. Smart delivery (79 SAR/month)
  6. VIP support (99 SAR/month)
  7. AI Premium Claude Opus (149 SAR/month)
- **Social Media** page (8 platforms with connect/disconnect + recent posts)
- **Recharge modal** (4 packages: 1k/2k/5k/10k)
- **Wallet** default 5000 points + auto-boost on low balance
- **Notifications & user dropdown menus**
- **Global search** filters products

### ✅ COMPLETED in app_mode_full.html (Customer Storefront)
- Rich product detail page with deep AI analysis renderer (`buildRichAnalysisClientHTML`)
- Light-themed cards matching customer-facing aesthetic
- 8 dynamic sections rendered when analysis exists
- Falls back to legacy info.html for old products
- **P1 Customer Features (Feb 2026)**:
  - ❤ Wishlist: heart toggle on every product card, dedicated wishlist page + bnav tab, badge in header
  - 🔐 OTP Login modal: phone-based auth (demo OTP `1234`), session persisted in localStorage, account-page shows logged-in state + logout
  - ⭐ Product Reviews: per-product reviews with 5-star picker + text, requires login, avg rating displayed, stored per product key
  - 🎟️ Coupons: 3 codes seeded (`WELCOME10` 10%, `SAVE50` flat 50, `FREESHIP` flat 25) with live cart total recalc including tax-on-discounted-base
  - 🔗 Share Wishlist (NEW): `?wl=p1,p5,...` URL deep-link, WhatsApp/native share, clipboard fallback, auto-import on visit
  - Fixed pre-existing `pdJump()` orphan code that was breaking the page

### ✅ MongoDB + JWT Integration Phase 1 (Feb 2026)
- New router `/app/backend/routers/store_router.py` (registered in server.py):
  - `GET /api/store/health`
  - `POST /api/store/customer/request-otp` · `POST /api/store/customer/verify-otp` · `GET /api/store/customer/me`
  - `GET/POST/PUT/DELETE /api/store/products` (merchant-scoped via JWT)
  - `GET/POST /api/store/wishlist` (per-customer)
  - `GET /api/store/reviews/{pid}` · `POST /api/store/reviews`
- `admin.html`: real `/api/auth/login` flow, JWT stored in localStorage, all products CRUD goes through API
- `app_mode_full.html`: real customer OTP via backend, wishlist + reviews sync to MongoDB when logged in
- Mongo collections used: `users` (existing), `store_products`, `customers`, `customer_otps`, `customer_wishlists`, `product_reviews`
- Test creds: `owner@zenrex.ai` / `owner123` (admin), any phone + OTP `1234` (customer)

### 🟡 MOCKED (functional UI, no live backend)
- admin.html login uses localStorage (no JWT)
- Products + orders use seed data (no MongoDB sync between admin/customer)
- Social OAuth not implemented (toggles save to localStorage)
- Service activations are localStorage flags only
- Auto-dispatch endpoint /api/delivery/auto-assign falls back to simulation

### 🟢 LATEST (Feb 10, 2026 · Dark Theme + Sandbox Wave — LAUNCH-READY)
- **🌙 Zenrex Unified Dark Theme** (`/mockups/zenrex-theme.css`):
  - Single source of truth via CSS variables (`--zx-*`)
  - Deep navy-black bg (`#0a0a14`), elegant violet/amber accents, subtle borders
  - Injected into `admin.html`, `app_mode_full.html`, `driver_app.html`
  - Onboarding modal redesigned dark with radial gradient hero + per-step accent tints
  - Custom themed scrollbars · luxurious shadows · `.zx-btn-primary/.zx-card/.zx-input` utilities
- **🎨 Theme Router** (`/api/theme/*`):
  - `GET /defaults` — platform default dark theme
  - `GET /merchant/me` + `PUT /merchant/me` — per-merchant theme override (colors/fonts/radius/buttons)
  - `GET /by-merchant/{id}` — public; customer storefront + driver app fetch merchant theme automatically
  - `POST /merchant/reset` — restore platform default
- **🏖️ Sandbox Router** (`/api/sandbox/*`): Full end-to-end test mode for ALL checkout
  - 10 Payment Gateways (Tabby/Tamara/Mada/STC Pay/HyperPay/Moyasar/Stripe/PayPal/ApplePay/COD)
  - 6 Shipping Providers (Aramex/SMSA/Naqel/DHL/J&T/Zenrex Fleet)
  - Beautiful PSP-branded checkout pages (Tabby green, Tamara purple, etc.)
  - Smoke-tested end-to-end: Tabby payment → Aramex label → 5-event delivery timeline

### 🔴 PENDING (Priority Order)

**P1 — CRITICAL NEXT**
- Zenrex Landing Page (marketing site) — promised next
- MongoDB persistence for admin.html ↔ app_mode_full.html sync
- JWT real auth on admin.html

**P2**
- Real OAuth (Meta/Google/X) for social connections
- Backend: /api/delivery/auto-assign with Haversine + nearest driver logic
- Backend: /api/social/auto-post (Meta Graph, TikTok Business, Twitter API)
- Backend: /api/replies/smart (Gemini-powered DM responder)
- Tabby/Tamara live payment execution
- ZATCA Phase 2 (XML + PDF/A-3 + QR)

**P3**
- ElevenLabs voice integration (cinematic quality)
- claude_core orchestrator for unified AI agents
- LiveKit voice agent / call-center AI
- Voice/Video section on main marketing site

## Tech Stack
FastAPI + MongoDB · Vanilla HTML/JS mockups + React main app ·
**Direct-SDK LLM (Jun 2026)**: Anthropic Claude Sonnet 4.5/4.6 · Google Gemini 2.5/3.1 (text + Nano Banana image gen) · OpenAI GPT-4o/5 · OpenAI Whisper · ElevenLabs Arabic TTS · ffmpeg · Web Speech API ·
**Bypass shim**: `backend/direct_llm_shim.py` transparently replaces `emergentintegrations.llm.chat` when `USE_DIRECT_LLM=1`, making the platform 100% independent of Emergent's platform.

## Production Deployment (Hetzner VPS — Jun 11 2026)
- **IP**: `91.98.154.148`
- **Stack**: Docker (`docker-compose.yml`) + Nginx (gzip + caching + uploads)
- **DB**: ⭐ **MongoDB Atlas M2** (`cluster0.1tkzj4x.mongodb.net`) DB=`zerax_prod` — migrated Jun 11 2026 (146 docs). Local `zerax-mongo-1` kept as fallback backup.
- **Backend**: Uvicorn inside `zerax-backend-1` (auto-pip-install on start)
- **JWT_SECRET**: Fixed via `.env` (no token loss on restart)
- **AI**: Fully working via direct provider keys (Claude/Gemini/OpenAI/FAL.ai 1.5s)
- **Image serving**: `/static/uploads/` → `/opt/zenrex/data/uploads/` (persistent volume)
- **Gzip**: HTML/CSS/JS compressed 4-5x (admin.html 506 KB → 123 KB)
- **All keys**: ANTHROPIC, GEMINI, OPENAI, ELEVENLABS, FAL — all active

## Driver Experience v2 (Jun 11 2026) — MAJOR REWRITE
**Backend** (`backend/routers/driver_config_router.py`):
- `GET/PUT /api/delivery/config` — per-merchant feature toggles + branding (42 features in 9 sections)
- `POST /api/delivery/config/reset` — restore defaults
- `GET/POST/PATCH/DELETE /api/delivery/config/branches[/{id}]` — full branches CRUD with map coords + capacity status
- `GET /api/delivery/config/public` — driver-facing config (no merchant secrets)
- Mongo collection: `driver_configs` (one doc per merchant)

**Frontend** — Driver app (`frontend/public/mockups/driver_app.html`):
- Sidebar with 9 sections: Map · Orders · Earnings · AI Coach · Achievements · Leaderboard · Profile · Settings · Support
- Live multi-branch Leaflet map with capacity colors (green=active, blue=available, amber=busy, gray=closed)
- Real-time Surge banner, heat alert toast, prayer pause overlay, driver pulse marker
- Earnings chart, instant pay, fuel calc, tip QR, weekly streak tracker
- AI Coach with rotating tips, voice command FAB, route memory
- 10 unlockable achievement badges, weekly leaderboard with gold/silver/bronze
- Floating SOS button, theme toggle, glance mode, PWA manifest
- All 42 features gated by merchant config flags

**Frontend** — Merchant config (`frontend/public/mockups/driver_manager.html`):
- 9 tabs: General · Earnings · Orders · AI · Saudi · Wellbeing · Gamification · Branches · Feature Order
- 42 toggles + numeric fields (streak amount/count, weekly challenge, surge multiplier, etc.)
- Branding picker (primary/accent colors, logo URL, app name)
- Branch map with click-to-add + capacity selector + delete
- Drag-and-drop section ordering
- SOS emergency contacts (up to 3 phones)
- Linked from admin.html → Delivery page → "إدارة تطبيق السائق" button

## Test Credentials
- Admin panel: `owner@zenrex.ai` / `owner123` (real JWT)
- Driver app: phone `0552222222` / OTP `1234`
- VPS SSH: `ssh -i /root/.ssh/zenrex_deploy root@91.98.154.148`


## 🚀 VPS Performance Fix — Jun 11 2026

**Issue**: Site reported as severely slow on Hetzner VPS deployment.

**Root Cause Identified**:
- Server resources were FINE (load 0.01, CPU 99% idle, 14GB RAM free, backend container 247MB, mongo 175MB).
- Bottleneck was 100% client-side: HTML mockups had **0 lazy-loaded images** while triggering 25+ visible `<img>` tags + 4 synchronous CDN scripts on every page load.
- Browser was fetching all images in parallel on first paint, choking the rendering pipeline.

**Fix Applied** (deployed to VPS):
1. Added `loading="lazy" decoding="async"` to **56 static `<img>` tags** across 6 mockup files.
2. Auto-applied to all dynamically-injected images (innerHTML templates) via browser default → now 254 images total are lazy.
3. Changed banner-video `preload="auto" autoplay` → `preload="none"` (no eager video download).
4. Added `defer` to 4 CDN scripts in `admin.html` (lucide, jspdf, html2canvas, qrcodejs) → non-blocking.

**Result** (measured from external network):
- `app_mode_full.html`: TTFB 235ms, total 567ms (110KB gzipped) — DOMContentLoaded in **0.07s** in browser.
- `admin.html`: TTFB 230ms, total 560ms — DOMContentLoaded in **0.06s**.
- No more 25+ parallel image fetches on initial render.


### 📦 Phase 2 — Inline JS Extraction (Jun 11 2026)

Extracted the single huge inline `<script>` block from each large mockup into an external `.js` file so the browser can cache it for 7 days (`Cache-Control: public, immutable, max-age=604800`).

**Files created**:
- `frontend/public/mockups/app_mode_full.js` — 263KB / 3842 lines (extracted from `app_mode_full.html`)
- `frontend/public/mockups/admin.js` — 273KB / 3441 lines (extracted from `admin.html`)

**HTML file size reduction (uncompressed)**:
- `app_mode_full.html`: 432KB → **161KB** (-63%)
- `admin.html`: 508KB → **235KB** (-54%)

**Cold-cache visit** (first time, both files downloaded in parallel + gzipped):
- HTML: 34KB gzipped in ~340ms
- JS: 76KB gzipped in ~450ms
- DOMContentLoaded: **0.05–0.09s** in headless Chromium.

**Warm-cache visit** (repeat visit):
- Only the HTML is fetched (~34KB gzipped). JS is loaded instantly from disk cache.
- Time to interactive: **~150ms** (essentially TTFB only).

**Verified**:
- All global JS functions (`getUser`, `translateReview`, etc.) still defined post-extraction.
- No JS console errors on either page.
- Visual layout identical (welcome modal, banner, categories, login form all rendering correctly).


## 🚀 Full React App Deployed to VPS — Jun 11 2026

**Discovery**: Until this point, the VPS at `91.98.154.148` was serving ONLY the static HTML mockups (admin, app_mode_full, driver_app). The actual standalone **React Zenrex platform** (FreeBuild, Smart Orchestrator, Ready Sites, AI Chat workspace, Image Studio, Video Studio, Auto-Coder) had never been deployed to VPS — it only lived on the Emergent preview URL.

**Fix Applied**:
1. Built React app with `REACT_APP_BACKEND_URL=http://91.98.154.148` so API calls go through VPS Nginx.
2. Stripped `.map` files (15MB savings).
3. rsynced `build/` (76MB) → `/opt/zenrex/frontend/build/` on VPS.
4. Rewrote Nginx config (`/etc/nginx/sites-available/zenrex`):
   - `root` switched from `frontend/public` → `frontend/build`
   - Added SPA fallback `try_files $uri $uri/ /index.html` for React Router
   - Kept `/api/` proxy → `127.0.0.1:8001`
   - Kept `/mockups/` location intact (admin.html, app_mode_full.html, driver_app.html still work)
   - Added 1-year `Cache-Control: public, immutable` for hashed CRA bundles in `/static/`
5. `nginx -t && systemctl reload nginx` → all green.

**Verified**:
- `http://91.98.154.148/` → React Zenrex homepage loads (DOMContentLoaded 0.09s), title "Zenrex | منصة الإبداع بالذكاء الاصطناعي", no JS errors.
- `http://91.98.154.148/api/store/health` → 200 in 234ms, payload `{"ok":true,"products":1,"customers":1,"reviews":0}`.
- `http://91.98.154.148/mockups/admin.html` → still 200 (mockups preserved).
- Main JS bundle (`main.2ea727e7.js`): cached 1 year + gzip + immutable.


## 🔑 Critical Env Fix — USE_DIRECT_LLM Activated on VPS (Jun 11 2026 04:44)

**Issue**: Although the .env file had `USE_DIRECT_LLM=1`, the running container was started before the value was injected — so the shim was NEVER active. All AI calls would silently fall back to the dead `EMERGENT_LLM_KEY` (restricted from VPS).

**Fix**:
1. Confirmed `USE_DIRECT_LLM=1` in `/opt/zenrex/backend/.env`.
2. Pinned it permanently in `docker-compose.yml` `environment:` block (survives `.env` rewrites).
3. `docker compose up -d --force-recreate backend` (90s rebuild with pip install).

**Verified live on VPS**:
- `POST /api/auth/login owner@zenrex.ai / owner123` → 200 + JWT (191 chars)
- `POST /api/ai/chat` → `{"content":"أهلاً","agent":"freebuild","model_used":"claude-opus-4-5","cost_estimate_usd":0.025065}`
- `POST /api/store/reviews/translate` → `{"ok":true,"translated":"هذا المنتج رائع"}` (Gemini direct)
- **VPS is now 100% independent from Emergent platform.** No Emergent network calls in any AI path.

### Login Credentials (user confusion noted)
The previous email `owner@zitex.com` (pre-rebrand) returns 401 — the correct email post-rebrand is `owner@zenrex.ai` / `owner123`.


## 🎨 Full Rebrand: Zerax → Zenrex (Jun 11 2026)

User purchased `zenrex.ai` from Porkbun (registered until Jun 11 2028) and asked for a global rebrand.

**Scope of rename**:
- **236 source files** updated via `rebrand.py` script (Pass 1: email/domain refs + whole-word "Zerax").
- **87 additional files** updated via `rebrand2.py` (Pass 2: compound identifiers — `ZeraxClient` → `ZenrexClient`, `ZERAX_CREDITS` → `ZENREX_CREDITS`, etc.).
- **10 source files renamed**: `ZeraxDuo.js` → `ZenrexDuo.js`, `ZeraxShowcase.js` → `ZenrexShowcase.js`, `zerax-logo.png` → `zenrex-logo.png`, 4 test files, etc.
- **2 directories renamed**: `backend/modules/zerax_ai` → `zenrex_ai`, `backend/static/zerax_logos` → `zenrex_logos`.
- **CSS theme** renamed: `zerax-theme.css` → `zenrex-theme.css`.
- **Nginx config** renamed: `nginx-zerax.conf` → `nginx-zenrex.conf`.
- **Database**: `users.email` migration — `owner@zerax.com` → `owner@zenrex.ai` (Mongo `updateMany` with `$replaceAll`).
- **All `@zerax.com` / `zerax.app` / `zerax.com` / etc. references** → `@zenrex.ai` / `zenrex.ai`.
- **Old `.zip` backups** removed (zerax-railway.zip, zerax-source-code.zip, zerax-independent.zip).

**React rebuild**: `REACT_APP_BACKEND_URL=https://zenrex.ai yarn build` — 32s, no errors.

**VPS deployment**:
- rsync'd new build + backend code to Hetzner.
- Updated Nginx config with `server_name zenrex.ai www.zenrex.ai _`.
- Restarted backend container — health check 200 OK.
- Verified frontend: page title `"Zenrex | منصة الإبداع بالذكاء الاصطناعي"`, all UI rebranded, no JS errors.

**Login verified**:
- ✅ `owner@zenrex.ai` / `owner123` → 200 OK + JWT (191 chars)
- ❌ `owner@zerax.com` → 401 Invalid credentials (as expected)

**New tooling**:
- Created `/app/deploy/deploy.sh` — one-command deploy script for future updates (`bash deploy.sh zenrex.ai`).

**Pending (user action required)**:
- ~~Add DNS A records in Porkbun~~ ✅ DONE (Jun 11 2026 12:35).
- ~~Provision Let's Encrypt SSL~~ ✅ DONE — `https://zenrex.ai` live with auto-renewal.

## 🔒 SSL/HTTPS Live (Jun 11 2026 12:50)

- **Certbot installed** on VPS and configured for Nginx.
- **Let's Encrypt certificate** issued for `zenrex.ai` + `www.zenrex.ai`, expires Sep 9 2026.
- **Auto-renewal** scheduled by certbot systemd timer (no manual work needed).
- **HTTP → HTTPS redirect** active (301 redirect on port 80).
- **Backend CORS** updated to allow `https://zenrex.ai` + `https://www.zenrex.ai`.
- **React rebuild** with final `REACT_APP_BACKEND_URL=https://zenrex.ai` deployed.

**Final verification**:
- `https://zenrex.ai` → 200 OK, title "Zenrex | منصة الإبداع بالذكاء الاصطناعي", green lock, no JS errors.
- `https://zenrex.ai/api/store/health` → 200 OK with `{"ok":true,...}`.
- Login: `owner@zenrex.ai` / `owner123` → JWT issued.

## 📧 Owner Email Forwarding (Porkbun → Gmail)
- All `@zenrex.ai` mail forwards to **`zenrex.ai@gmail.com`** via Porkbun Email Forwarding.

## 🎨 Creative Studio v2 (Jun 11 2026) — Conversational Wizard
**Full redesign per user feedback (3 iterations in one session):**

### Final architecture
- **Top-level sidebar nav item** "🎨 الاستوديو الإبداعي" (NOT inside product modal)
- **Fullscreen toggle**: hides app sidebar/topbar/onboarding; chat fills viewport (ESC to exit)
- **Conversational wizard** inside the chat (5 steps + section sub-step + summary):
  1. Type (banner/logo/section/general) — 4 interactive cards
  2. Idea — 4 type-specific suggestions + free text input
  3. Size — smart per-type recommendations with hints ("✅ Recommended for homepage hero", "⚠️ Too small")
  4. Color — 15 popular colors + "🎨 لون آخر" opens free-text input (Arabic/English/hex all valid)
  5. Style — 6 visual styles
  - Final summary card + Generate
- **STRICT color enforcement** in prompt: color name repeated 3× with "MUST be / DO NOT use other"
- **In-chat image grid** as bot message with 4 action buttons (اعتماد/حفظ ووضع/تحميل/ولّد أفضل)
- **Realistic placement preview** inline below approved images (mini hero/category-tile/promo mockup)
- **Fullscreen storefront preview** overlay: real mock of `zenrex.ai/store/...` with hero banner + categories grid; new images get golden "جديد" badge
- **Publish to storefront** button in fullscreen preview → saves `creative_library` to `merchant_themes` collection on MongoDB Atlas

### Files
- `frontend/public/mockups/admin.html` — new page (#creative-studio), wizard CSS, fullscreen styles
- `frontend/public/mockups/admin.js` — `CS_STATE`, `CS_WIZARD`, `csWizardStep*`, `csToggleFullscreen`, `csOpenFullscreenPreview`, `csPublishToStorefront`
## 🎨 Color System Overhaul (Jun 11 2026)
**Bug fix + major enhancement to Product Studio color picker.**

### Root cause of "hex → white image" bug
Previous code sent raw hex like `#000000` inside the Gemini prompt: `"isolated product shot on a #000000 background"`. Gemini AI cannot reliably parse hex codes in natural-language prompts → defaults to white.

### Fix + Enhancements
1. **Hex → English color name resolver** (`psHexToName()`): every hex is converted to a Gemini-friendly natural name (e.g., `#000000` → `"pure black"`, `#7c3aed` → `"vibrant purple"`). Falls back to brightness/RGB analysis for unknown hex (e.g., `"warm reddish tone"`).
2. **6 categorized color palettes** (~50 named colors):
   - ⚪ أساسي (basics: 6 colors)
   - 🔥 دافي (warm: 8 colors)
   - ❄️ بارد (cool: 8 colors)
   - 🌸 باستيل (pastels: 8 colors)
   - ⚡ نيون (vibrant: 8 colors)
   - 💎 فاخر (luxury: 8 colors)
3. **Custom Color Tool**: merchant adds their own brand colors via "+ أضف لون" modal (Arabic name + English name + hex). Hover preset to show name in tooltip; click ✕ to delete.
4. **Persistence**: custom palette saved to `localStorage.zx_custom_colors` AND synced to MongoDB via `PUT /api/theme/merchant/me` with `custom_palette: [{ar,en,hex},...]` field on `merchant_themes` doc.
5. **Cross-device sync**: `psHydrateCustomColorsFromServer()` pulls latest palette on every studio open.
6. **Customer-store integration**: storefront fetches merchant theme via `/api/theme/by-merchant/{merchant_id}` — custom_palette is now part of the public theme response.

### Files touched
- `frontend/public/mockups/admin.js` — color palette logic, hex→name resolver, custom color modal
- `frontend/public/mockups/admin.html` — CSS for categorized presets, custom color modal styling
- `backend/routers/theme_router.py` — added `custom_palette: Optional[list]` to `ThemeIn` model + save logic


## MongoDB Atlas Migration (Jun 11 2026) ⭐
- **Status**: ✅ COMPLETE & VERIFIED IN PRODUCTION
- **Cluster**: `cluster0.1tkzj4x.mongodb.net` (M2 Shared, Free tier eligible)
- **User**: `zenrex_admin`
- **DB**: `zerax_prod` (kept legacy name for backward-compat with code)
- **Migrated**: 146 documents across 24 collections (users, orders, products, pricing_plans, etc.)
- **IP Access**: `0.0.0.0/0` (allow all — can be tightened to `91.98.154.148/32` later)
- **Connection** via `docker-compose.yml` env: `MONGO_URL=mongodb+srv://zenrex_admin:***@cluster0.1tkzj4x.mongodb.net/...`
- **Verified**: Write test passed (created order from production frontend → confirmed in Atlas)
- **Fallback**: Local `zerax-mongo-1` container still running with snapshot in `/tmp/mongo_backup` and persistent volume `/opt/zerax/data/mongo` — can revert by editing docker-compose.
- **Compose backup**: `/opt/zerax/docker-compose.yml.bak.<timestamp>` (pre-migration version)

## Creative Studio — Loading Spinner & Post-Generation Conversational Refinement (Feb 11 2026) ⭐
- **Status**: ✅ COMPLETE & VERIFIED via screenshot
- **Files**: `/app/frontend/public/mockups/admin.html` (CSS additions), `/app/frontend/public/mockups/admin.js` (csGenerate + csSendChat)
- **What was built**:
  - **Spinning Zenrex logo loader**: Inline chat message with `.cs-logo-spin` (rotating gold-bordered Zenrex logo + glow pulse) while images are being generated. Cycles through 4 status messages every 1.8s.
  - **Status badge for refinements**: When user provides a tweak after first generation, the loader now shows a green `📝 مع تعديلاتك: ...` line indicating the refinement is being applied.
  - **Post-generation chat mode**: `CS_WIZARD.postGenChat = true` after the first batch — user can type any modification (e.g., "خلي الإضاءة أقوى"), the bot logs it, and emits an inline action banner with two buttons:
    - 🚀 **ولّد · 32 نقطة** → triggers `csGenerate()` again with the merged prompt (`finalConcept + refineInstructions`).
    - 🔄 **محادثة جديدة** → resets refineInstructions + exits postGenChat mode.
  - **Charge model**: 1 pt per chat message + n×8 pts per regeneration (4 images = 32 pts).
- **data-testid added**: `cs-regenerate-btn` for E2E.









