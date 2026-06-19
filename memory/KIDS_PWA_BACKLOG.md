# Zenrex Kids (`/play`) — Saved State + Future Backlog
> Frozen at: 2026-06-19. Live & working at https://zenrex.ai/play
> Resume work from this file when returning to the Kids PWA project.

## ✅ Current Production State (DO NOT BREAK)
- URL: `https://zenrex.ai/play` (legacy `/kids` redirects here)
- Source files: `/app/zenrex_play/` (index.html, app.js, sw.js, manifest.webmanifest, icons)
- Deploy: `bash /app/deploy/deploy.sh zenrex.ai` (auto-syncs `/app/zenrex_play/` → `/var/www/pwa_play/`)
- SW version: `zenrex-play-v4-antifraud-review`
- Script cache-bust: `<script src="/play/app.js?v=v4-antifraud-review">`
- Test credentials in `/app/memory/test_credentials.md`

## ✅ Shipped Features
- 5 tabs: 🏠 الرئيسية · 📿 الدين · 📖 القرآن · 🎯 المهام · 👤 حسابي
- Parent dashboard with 9 sub-tabs incl. 🏆 weekly challenge, 📹 recordings review
- Full Quran (114 surahs) with 11 reciters + Tasmee'/Test mode + Mushaf page viewer (604 pages, alquran.cloud)
- Memorization map + parent-assigned plans
- Weekly challenge (manual/random surahs, 1-30 days, live leaderboard, winner badge)
- View-as-User toggle for parent (no separate account)
- Cryptographically-random video shuffle on every load + manual 🎲 button
- 24h cooldown on task completions (anti-cheat)
- Parent approval required before points for tasks/dhikr (auto-approve only prayers)
- Notification badges 🔴 on parent dashboard (pending recordings + Quran)
- Internal video modal player (no popup blockers)
- Before/After task camera proofs

## 🐛 Known Pitfalls (read before re-touching)
1. **NEVER remove `--exclude="uploads/"`** from deploy.sh's rsync — it WILL wipe all uploaded videos.
2. **Mushaf surah→page array** is verified against Madinah Mushaf. If editing, validate against a known reference.
3. **SW caches `/play/app.js`** — bump version in BOTH `sw.js` (SW_VERSION) AND `index.html` (?v=) when shipping major JS changes.
4. **MEDIA_DIR** is `/app/backend/uploads/freebuild_media` inside container → `/opt/zerax/backend/backend/uploads/freebuild_media/` on host (nested path).
5. **Playwright Chromium does not support H.264 playback** — ignore "no supported sources" errors in screenshots.

## 🎯 Gamification Backlog (Organized by impact)

### P0 — Highest user-value, ready to build
- **Persistent badges system**
  - بطل الأسبوع 🏆 (auto-granted on challenge win)
  - أسطورة الشهر 🌟 (2 consecutive challenge wins)
  - حافظ المبتدئ 📖 (10 short surahs completed)
  - حافظ السبع الطوال 🕋 (any of the 7 longest surahs approved)
  - Storage: `kids_badges` collection `{child_email, badge_type, earned_at, meta}`
  - UI: Profile screen → badge wall

- **Monthly PDF report for parent**
  - Per-child: points trend, top surahs approved, missed days, prayer streak
  - Library: ReportLab or weasyprint
  - Endpoint: `GET /kids/report/monthly/{child_email}?month=YYYY-MM` → PDF stream

- **Daily progress bar**
  - Visible on Profile + Home: "اليوم: 3/5 مهام · 2/5 صلوات"
  - Auto-resets at local midnight (parent's timezone)

### P1 — Strong engagement boosts
- **Comeback challenge for losing sibling**
  - On weekly challenge end → auto-create a 3-day "تحدي تعويضي" for runner-up with shorter surahs and 50% point bonus
  - Backend: extension of `kids_weekly_challenges` with `parent_challenge_id` link

- **Younger-child fairness multiplier**
  - Parent sets `age_years` on kid account → backend applies `×(1 + (age_gap × 0.1))` to points when difference ≥ 3 years
  - Configurable in parent dashboard kids tab

- **Push notifications (PWA Web Push)**
  - On: challenge start, parent approval, badge earned, sibling beat your record
  - Endpoint: `POST /kids/push/subscribe` + `POST /kids/push/test`
  - VAPID keys needed (or use Firebase Cloud Messaging)

- **Celebration sound + confetti** on approval
  - Pure JS confetti library (`canvas-confetti`) + Audio API for "تكبير" sound

### P2 — Insights & analytics
- **"Best time to memorize" analytics**
  - Backend aggregation: avg approval-to-attempt ratio by hour-of-day per child
  - Surface in parent dashboard "📊 الإحصائيات" tab

- **"Difficult surahs" suggestions**
  - Track rejections per surah. Surface top-3 with parent recommendations
  - Optional: AI tip via Claude ("نصيحة لتيسير سورة X")

### P3 — Beyond Quran
- **Dhikr challenge** (weekly: who keeps morning/evening adhkar streak)
- **Prayer challenge** (5 daily prayers on time + sunnah bonus)
- **Household tasks challenge** (cooperative — siblings team up vs daily-target)

### P4 — Father's personal space (deeper customization)
- **Personal Quran folder**: favorite reciters, bookmarked ayahs, tadabbur notes
- **Word-by-word highlight**: while playing audio, highlight the current word in mushaf
- **Privacy**: father's recordings NEVER appear in any child's view

## 🛠 Other Pending Tasks
- TikTok/YouTube channel bulk importer (yt-dlp playlist) — parent provides channel URL, server pulls all videos
- "Clone Template" SaaS exporter (strip prayer/points → general TikTok-style PWA for other parents)
- Backblaze B2 backup for kids_recordings (cheap cold storage)
- Automated Travian account registration via 2captcha

## 📊 Mongo Collections Used by Kids PWA
- `kids_accounts` — `{email, parent_id, name, pin, role, is_owner, age_years?}`
- `kids_parent_tasks` — `{id, parent_id, title, icon, points, needs_camera, needs_before_after, order, is_active}`
- `kids_dhikr` — `{id, parent_id, title, icon, target, points, is_active}`
- `kids_recordings` — `{id, child_email, rec_type, task_id, task_title, phase?, status, proposed_points, awarded_points, path, created_at}`
- `kids_quran_submissions` — `{id, child_email, surah_num, ayah_from, ayah_to, audio_path, status, transcript?, awarded_points, reviewed_at}`
- `kids_quran_plans` — `{child_email, surah_number, target_points, created_at}`
- `kids_points` — `{id, child_email, kind, value, meta, created_at}` (ledger)
- `kids_weekly_challenges` — `{id, parent_id, surah_nums[], days, start_at, end_at, mode, status, winner_email}`
- `freebuild_media_assets` — `{id, user_id, url, approved, category, title, source_url, thumbnail_url}` (shared with main app)
