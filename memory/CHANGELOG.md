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
