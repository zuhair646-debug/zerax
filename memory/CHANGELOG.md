# Zitex Changelog


## 2026-06-05T09:49:30 — 🆕 Jun 5 2026 — AutoCoder Superpowers wired ✅

الـ7 أدوات (project_context, screenshot_url, plan_*, update_prd, project_health) صارت متاحة للـAutoCoder. screenshot_url يربط Vision passthrough تلقائياً.

## 2026-06-05T10:13:23 — 🔥 Jun 5 2026 — AutoCoder LIVE TEST: fixed /games/web routing autonomously

- Owner reported: clicking Games button on Landing → blank page
- Main agent acted as owner, sent task via /api/autocoder/chat as owner
- AutoCoder used 9 tools autonomously: screenshot_url (saw 'No routes matched /games/web' in console errors), read_file App.js + LandingPage.js, identified mismatch (button=/games/web vs route=/dashboard/games/web), edit_file App.js (added redirect route), git_status, git_add+commit+push
- Fix: Lines 127-128 in App.js — Route path /games/web with Navigate to /dashboard/games/web (if user) else /register; same for /games/mobile
- Verified live: /games/web now redirects to /register for guests (no more blank)
- Commit: 2f23385 (AutoCoder authored)

Bug Fixes shipped this session:
- Ghost Chat: asyncio.shield() around _persist_assistant_turn — partial saves now survive client disconnects (proven: conv a69204ba saved 18 tool_events from cut stream)
- screenshot_url: networkidle + 5s wait + 45s nav timeout — React SPAs render before capture
- Tool preview handlers: clean summaries (no base64 floods chat)


## 2026-02-08 — 🌐 FreeBuild Conversational Chat (Game-Studio-style) ✅

- Backend `/app/backend/modules/freebuild/freebuild_chat.py`:
  - 8 endpoints: `GET /types`, `POST /project`, `GET /projects`, `GET /project/{id}`, `POST /project/{id}/chat`, `POST /project/{id}/asset/{aid}/approve`, `POST /project/{id}/compile`, `DELETE /project/{id}`
  - `TAG_RE` parses `<<HERO|SECTION_BG|LOGO|PRODUCT|ICON|BANNER_AR|GALLERY: prompt>>` from AI response
  - `_extract_html` pulls `<!DOCTYPE html>...</html>` from ```html``` code blocks into `current_html`
  - `_strip_tags` removes tags from chat text + collapses blank lines
  - `_generate_assets_bg` background task: spawns `generate_flux_pro` (Fal.ai/OpenAI) per tag, updates asset status via `arrayFilters` (fixed messages.0.pending_assets path bug)
  - `extra_context` includes approved asset URLs so AI can reuse them in HTML
- Frontend `/app/frontend/src/pages/FreeBuildChat.js`:
  - 3 modes: `ProjectList` (no id), `TypePicker` (id=='new'), `ChatWorkspace` (id=uuid)
  - 3-pane layout: **Assets sidebar | Chat | Live Preview iframe** with desktop/mobile toggle and show/hide preview
  - Polls project every 4s for async asset generation status
  - `data-testid` on every interactive element (new-project-btn, type-{id}, create-project-btn, chat-input, chat-send-btn, approve-asset-{id}, preview-iframe, …)
- AI agent ("freebuild" in `zitex_ai`) instructs Claude Sonnet to consult first then emit tags then HTML
- Tested: 16/16 backend pytest pass, frontend smoke ✅ (`/app/test_reports/iteration_37.json`)
- Pytest regression: `/app/backend/tests/test_freebuild_chat.py` (~60s, hits live Claude+Fal)
- Pushed to `main` → Railway auto-redeploys
