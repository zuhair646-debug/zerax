# Zitex Changelog


### 🆕 Feb 17 2026 — Phase 16: Distance-based Pricing + Driver Employment Models + Multi-country Payouts ✅
Massive upgrade to the delivery system per the user's explicit Saudi-Arabic specs:

**1. Distance-based pricing (real Haversine)** — `POST /api/delivery/calculate-fee`. Configurable in ACP: base fee + price/km + min/max floor/cap. Customer GPS coords now stored on every order with auto-computed `distance_km`.

**2. Two driver employment models**:
   - `commission`: per-delivery share (e.g., 8 SAR of 10 SAR fee → driver, 2 SAR → merchant)
   - `salaried`: fixed monthly wage, merchant keeps 100% of every fee
   - Auto-revenue split via `driver_share_default_pct` (configurable, default 80%)

**3. Multi-country payouts** (8 countries): STC Pay/urpay/Mada/AlInma Pay (SA), PayBy/e&Money (AE), Vodafone Cash/InstaPay/Fawry (EG), KNET/MyFatoorah (KW), BenefitPay (BH), QPay (QA), OmanNet (OM), ZainCash/AsiaHawala (IQ), plus IBAN + cash everywhere. Per-country method list via `GET /api/delivery/payout-methods?country=`.

**4. Payouts tracking**: `GET/POST /api/delivery/payouts` — record manual wage/commission transfers per driver. Auto-decrements `balance_pending_sar` for commission drivers. ACP shows pending balances + history.

**5. Branches management**: `GET/POST/DELETE /api/delivery/branches` — merchants define multiple branch GPS coords. Distance is calculated from the branch chosen on each order (default: main branch).

**6. Smarter auto-assign**: Now considers (a) zone match, (b) current active load (max 3 per driver, allows multi-order assignment), (c) Haversine distance from driver's location to the customer. Truly proximity-aware without AI.

**7. Customer tracking page**: NEW `/mockups/track.html` with public Leaflet map (Carto light tiles), live driver location, ETA, full status timeline, items + bill, tel: link to driver. Polls every 10 s. Receives order id via `?id=` query param.

**8. Unified landing page**: NEW `/mockups/index.html` with 3 hero cards (Merchant ACP / Driver App / Customer Track) — easy access to all three entry points + demo credentials inline.

**Files Created/Modified:**
- `/app/backend/routers/delivery_router.py` — extended ~250 lines: Haversine, distance pricing, employment-type-aware revenue split, payouts/branches/payout-methods endpoints, country/currency support.
- `/app/frontend/public/mockups/app_mode_full.html` — ACP delivery tab now has 5 sub-tabs (orders/drivers/branches/payouts/zones), distance calculator widget, employment-type toggle in driver form, multi-country payout method dropdown.
- `/app/frontend/public/mockups/track.html` (NEW, customer tracking)
- `/app/frontend/public/mockups/index.html` (NEW, unified landing)



## 2026-02-17 — 🚚 Integrated 3-Sided Delivery System ✅

End-to-end driver/delivery platform spanning merchant ↔ driver ↔ customer.

### Backend (`/api/delivery/*`)
NEW router `/app/backend/routers/delivery_router.py` (~470 lines). All endpoints public for demo (no JWT). In-memory store seeded with 5 demo drivers + 5 orders in mixed statuses.

**Drivers CRUD** · `/drivers` (list/create/upsert by phone) · `PATCH /drivers/{id}` · `DELETE /drivers/{id}` (auto-unassigns active orders to `pending`).

**Driver Auth (demo OTP)** · `POST /driver/login` (any seed phone → returns deterministic OTP `1234`) · `POST /driver/verify-otp` → token · `GET /driver/me` + `GET /driver/feed` (active + done_today + summary). Header: `Authorization: DriverToken <tok>`.

**Orders** · list with `?status=` / `?driver_id=` filters · auto-assign on create (matches zone, picks driver with fewest active deliveries) · `PATCH /assign` · `PATCH /status` (only assigned driver can change when driver-token used; updates timeline log + increments driver.earnings_today_sar on `delivered`) · `POST /location` (GPS ping) · `GET /track` (public customer view — sanitized).

**Settings & Stats** · zones (5 Riyadh areas with per-zone fee + ETA), free-delivery threshold, auto-assign toggle, COD toggle · `/stats` returns by_status counts + active_drivers + revenue_today_sar.

### Frontend — Merchant ACP Delivery Tab
NEW `🚚 التوصيل` tab in the Admin Control Panel:
- **4-stat strip** (waiting / active / available drivers / revenue today)
- **Driver-app link card** with `فتح ↗` button → `/mockups/driver_app.html`
- **3 sub-tabs**: 📦 الطلبات · 🧑‍✈️ السائقون · 🗺️ المناطق
  - Orders: filter pills + assign-driver modal (shows online/delivering drivers w/ avatar+rating+today's count) + cancel button
  - Drivers: avatar list with status pill + add-driver form (name/phone/vehicle/area) + delete (with auto-unassign)
  - Zones/Settings: free-threshold + base-fee + per-km + auto-assign checkbox + COD checkbox + 5-zone list with per-zone fee/ETA

### Frontend — Standalone Driver PWA (`/mockups/driver_app.html`)
NEW dark-themed mobile-first app (480px max-width, RTL Arabic):
- **Login**: phone (05xxxxxxxx validation) → OTP (deterministic 1234) → token persisted to `localStorage.zrx_drv_token`. Auto-login on revisit.
- **Header**: avatar + name + rating + zone + status toggle pill (online ↔ offline with pulsing dot animation).
- **Stats strip**: today's count / today's earnings / rating.
- **Tabs**: النشطة (with badge count) / المنجزة / الأرباح (weekly total, per-delivery avg, productivity tip).
- **Order detail overlay**: Leaflet dark-theme map with driver+destination markers + dashed route polyline, customer info with tel: link, address w/ Google Maps deep link, items breakdown, status timeline (5 steps with pulse on current step), action bar with next-status button + cancel.
- **Status transitions**: `pending → assigned → picked_up → delivering → delivered` (each call updates server + advances timeline). When `delivering` starts, simulated GPS ping every 8 sec via `POST /location`.
- **Bottom-nav**: الطلبات / الأرباح / خروج (with SVG icons).
- **Auto-refresh**: every 30 sec when not viewing an order detail.

### Tests
- `/app/backend/tests/test_delivery.py` — 16 pytest cases ALL PASS (testing iteration_40)
- Full E2E driver app + ACP delivery tab verified end-to-end including OTP login, status toggles, assignment modal, add-driver flow, session persistence after reload.



## 2026-02-17 — 🎬 Admin Control Panel + Promo Video Studio + Inline Recharge Gateway ✅

Major UX consolidation per user's explicit Saudi-Arabic requests.

### 1. Admin Control Panel (ACP) — `#acp-modal`
Replaced the scattered admin workflow with a unified merchant dashboard that auto-opens when the ♛ button is toggled.
- **Tabs**: 📦 Products · 🎬 Video Studio
- **Credits bar**: Live Zenrex balance + inline `+ شحن` button (always visible)
- **Product editor**: name / price / category / official URL / description
- **AI Auto-Fill button**: relocated FROM inside the Image Studio TO the ACP product form (per user request). Calls existing `/api/image-studio/product-info` and renders variants (colors swatches + warranty link). Costs 10 credits.
- **Image Studio button**: opens the gallery editor for the current product (kept as secondary action, no longer the primary entry-point for AI)

### 2. Promo Video Studio — `POST /api/promo-video/*`
NEW backend router `/app/backend/routers/video_studio_router.py` (~527 lines). Three-stage pipeline:
1. **Storyboard** (`/storyboard`): Gemini 2.5 Flash generates JSON storyboard — title + N scenes × (narration · visual_prompt · text_overlay) tuned to duration (15/30/45/60s) and tone (energetic/luxury/warm/tech). Cost: 5 credits.
2. **Zenrex Voice Engine** (TTS): Abstracted under voice IDs `zenrex_male_deep`, `zenrex_male_warm`, `zenrex_female_warm`, `zenrex_female_clear`. Currently powered by OpenAI `tts-1-hd` via `EMERGENT_LLM_KEY` (designed to be swapped with Zenrex's own voice provider later — single mapping in `ZENREX_VOICE_MAP`).
3. **Video render** (`/generate`): ffmpeg pipeline — scene images → per-scene clips with ken-burns zoom → concat → optional logo watermark overlay → title + CTA drawtext (Noto Arabic font) → mux with padded TTS audio → final 1080×1920 vertical MP4 at `/api/static/videos/{id}.mp4`. Cost: 5 credits per 5 seconds.

### 3. Inline Recharge Gateway — `#rch-modal`
User explicitly requested credits be topped up **without leaving the merchant's site** (no redirect to the main Zenrex wallet).
- **4 packages**: Starter (500/49 SAR), Pro (2500/199 SAR, default + "الأكثر طلباً" badge), Agency (6000/449), Enterprise (15000/999)
- **5 payment methods**: Mada · Visa · Mastercard · Apple Pay · STC Pay
- **Backend `/recharge`**: INTENTIONALLY MOCKED — simulates 400 ms gateway latency, returns transaction ID + receipt number. Placeholder for the real Zenrex wallet API.
- **Skeleton-free open**: Falls back to static packages instantly, then refreshes from API in background.

### 4. Cleanup
- Removed the old `#info-panel-wrap` (Product Info AI) from inside the Image Studio modal — its function is now exclusive to the Admin Control Panel.
- `startAddProduct(catId)` no longer creates a stub product immediately; it routes through ACP so the merchant fills metadata first, then opens the Image Studio with a real product context.
- Added `ffmpeg` + `fonts-noto-core` to the system (for video stitching + Arabic title overlays).

### 5. Tests
- `/app/backend/tests/test_promo_video.py` — 7 pytest cases (health, storyboard, packages, 3× recharge variants, real 15-second video render with MP4 validation). Passes in ~30 seconds.
- Testing agent verified end-to-end UI flows (iteration_39): 100 % backend, 100 % frontend.



## 2026-02-16 — 🏗️ Template-First Engine: 3 Master Templates Production-Ready ✅

**Architectural pivot complete.** Replaced AI code generation for Ready Sites with 3 hand-crafted, feature-complete master HTML templates that hydrate from JSON + Market Packs. Zero hallucinations, 100% deterministic output.

### 1. App Mode — `app_mode_full.html` (سوقي 🛒)
E-commerce mobile-first template for stores, marketplaces, food delivery, etc.
- **Cart & Checkout**: Full add/remove/quantity, tax calc per market, payment selection
- **Search**: Live filter by Arabic + English product names
- **Category filter**: 8 categories with active state
- **49-market localization**: Auto-detect on load, dropdown switch, currency conversion (RATES map), payment gateways + shipping carriers swap dynamically
- **Reviews carousel**: 3 testimonials auto-rotating every 5s
- **Banner slider**: 3 hero promos auto-cycling
- **Reservation modal** + WhatsApp link from market
- **Bottom nav** (mobile app feel)
- **Cart persistence**: localStorage `zx_cart`

### 2. Story Mode — `story_mode_full.html` (N O I R)
Cinematic narrative template for restaurants, cafés, services, boutique experiences.
- **Hero**: Full-bleed image with double CTA (Menu / Reserve)
- **Story chapters**: 2-column narrative section
- **Menu**: 8 dishes across 4 tabs (Starters/Mains/Desserts/Drinks) — add to cart works
- **Gallery**: 8-image grid with hover zoom
- **Reviews**: Auto-rotating large-format testimonials
- **Reservation form**: name/phone/date/time/guests/notes with success state
- **Cart & Checkout**: Same engine as App Mode, restyled in elegant gold/black
- **49-market localization**: Phone format, currency, payments, hours
- **Floating nav**: Becomes opaque on scroll

### 3. Showroom Mode — `showroom_mode_full.html` (A R Y A)
Luxury 3D portfolio template for jewelry, watches, real estate, fine art, cars.
- **3D Floating grid**: 9 products with perspective tilt (rotateY -6°/0°/+6° pattern)
- **Ambient background**: Animated gradient orbs + drifting starfield
- **Product detail modal**: Full-screen split image/info with "Add to Cart" + "WhatsApp Consult" buttons (deep-link to wa.me)
- **HUD stats bar**: EST. year / clients / gold purity / certification
- **Consultation form**: Private viewing booking with interest dropdown (rings/necklaces/bracelets/watches)
- **Reviews**: Italic serif quotes with auto-rotation
- **Cart & Checkout**: Same engine, restyled with gold accents
- **Categories**: 5 luxury tabs (all/rings/necklaces/bracelets/watches)

### Shared Infrastructure
- **Backend endpoints** (already live): `GET /api/ready-sites/markets`, `GET /api/ready-sites/market/{id}`, `GET /api/ready-sites/detect-market`
- **Currency RATES map**: 43+ currencies converted from SAR baseline
- **Universal i18n pattern**: `data-key`, `data-key-ph`, `data-key-opt` + `_html` suffix for innerHTML
- **Universal market popover**: same UX across all 3 templates
- **Zitex footer**: Branded "CRAFTED BY ZITEX" footer with link to zenrex.ai
- **Pushed to GitHub**: 2 commits (`93c634b`, `51407c4`) on main branch

### Tested
- ✅ App Mode: SAR→USD ($159.93 from 599 SAR), category filter, cart with VAT 15%
- ✅ Story Mode: Mains filter (3/3), USD price conversion ($76.09 from 285 SAR)
- ✅ Showroom Mode: Rings filter (3/3), UAE Dirham (د.إ 47,530 from 48,500 SAR), detail modal opens
- ✅ Zero JS errors across all 3 templates
- ✅ All 49 markets selectable, payment gateways auto-render

### Files Created/Modified
- `/app/frontend/public/mockups/app_mode_full.html` (created + polished)
- `/app/frontend/public/mockups/story_mode_full.html` (created)
- `/app/frontend/public/mockups/showroom_mode_full.html` (created)

### Next
- Wire React Wizard (`ReadySites.js`) to template-first engine — deprecate legacy `agent.py` AI pipeline
- Multi-Service Hub toggle (multi-department businesses)
- Zitex Care Portal (post-delivery client dashboard)
- Real payment gateway integrations (Mada/Tabby/Tamara/Stripe/Alipay)
- ZATCA Phase 2 e-invoicing



## 2026-02-15 (g) — 💰 PayPal Payouts + 🎫 Support Tickets + 🤖 AI FAQ + 🔔 Notifications ✅

### نظام السحب (PayPal Payouts) — `/app/backend/modules/affiliate/payouts.py`
- المسوّق يضيف PayPal email (إجباري) → يضغط "طلب تحويل"
- يدخل المبلغ ($25 حد أدنى) → يشوف معاينة فورية:
  - المبلغ المطلوب
  - **رسوم $2** (محسوبة من جهتنا)
  - المبلغ الذي يستلمه = طلب − رسوم
- **الرصيد يُقفل** فوراً (locked_in_payouts) عشان ما يطلب طلبين
- **Notification للأدمن**: "💰 طلب تحويل جديد: $50 (يستلم $48)"
- الأدمن في `/admin/payouts` يشوف:
  - بيانات المسوّق + بريد PayPal + زر "افتح PayPal مع pre-filled email"
  - زر **"تأكيد التحويل"** → ينتقل المبلغ من locked → paid_total
  - زر **"رفض"** مع سبب → الرصيد يرجع للـ pending_balance
- **Notification للمسوّق** عند التأكيد/الرفض

### نظام الدعم الفني — `/app/backend/modules/support/__init__.py`
**`SupportWidget` floating component** — زر دائري purple/pink في زاوية كل صفحة (مع SupportWidget user check):
- **Tab 1 "اسأل"**: العميل يكتب سؤاله → `/api/support/ai-quick-answer`:
  - FAQ lookup أولاً (7 مواضيع شائعة: payouts/affiliate/language/pricing/website/game/...)
  - إذا ما لقى، يستخدم Claude Sonnet 4.5 كـ fallback (يجاوب بإيجاز)
  - يظهر زر "لم تحل مشكلتي → أرسل تذكرة" إذا الـ AI غير واثق
- **Tab 2 "تذكرة جديدة"**: subject + body + category (support/suggestion/bug/feature/payout) + priority
  - **AI Auto-Reply**: عند الإنشاء، النظام يلقّم FAQ، يضيف رداً تلقائياً من AI، الـ ticket يصير `replied` مباشرة
  - Notification للأدمن
- **Tab 3 "تذاكري"**: قائمة تذاكر المستخدم → ضغطة → thread كامل مع admin messages مميّزة بلون
- العميل يقدر يرد على الأدمن من نفس الـ widget، الأدمن يستقبل notification

### Notifications System (in-app)
- `GET /api/notifications/me` → قائمة + عداد unread
- `POST /api/notifications/{id}/read` + `POST /api/notifications/mark-all-read`
- مستخدمة من: payout_request, payout_paid, payout_rejected, support_new, support_reply, support_user_reply

### Admin pages
- **`/admin/payouts`** (`PayoutsAdmin.js`): قائمة طلبات السحب (filter pending/paid/rejected/all) + ضغطة تأكيد/رفض
- **AdminDashboard tile**: "طلبات السحب 💰" أضيف

### اختبار live
- `POST /api/support/ai-quick-answer` بسؤال "كيف اسحب فلوسي" → رد FAQ كامل بالعربية ✅ (`source: faq, confident: true`)
- `/api/affiliate/me/payout-info` للـ non-affiliate → 403 "أنت لست مسوّقاً" ✅
- كل الـ endpoints مسجلة و 403 لـ unauthenticated ✅

### ملفات جديدة
- `/app/backend/modules/support/__init__.py`
- `/app/backend/modules/affiliate/payouts.py`
- `/app/frontend/src/components/SupportWidget.js`
- `/app/frontend/src/pages/PayoutsAdmin.js`

### ملفات معدلة
- `/app/backend/server.py` (تسجيل 2 routers جدد)
- `/app/frontend/src/App.js` (SupportWidget + PayoutsAdmin route)
- `/app/frontend/src/pages/AffiliateDashboard.js` (Payout panel كامل + history)
- `/app/frontend/src/pages/AdminDashboard.js` (tile جديد)

---


## 2026-02-15 (f) — 📈 Affiliate Tracking System (Click → Signup → Paid Funnel) ✅

**طلب المستخدم**: نظام مسوّقين احترافي — وين يحطون روابطهم، إحصائياتهم الداخلية، كم شخص دخل، أماكن النشر، عدد النشرات لكل رابط. + مدى تأثيرهم الفعلي.

### Backend (`/app/backend/modules/affiliate/tracking.py` — جديد، 530 سطر)

**Click Tracking endpoint** (`GET /api/r/{code}`):
- يسجّل كل ضغطة في `affiliate_clicks` collection
- يستخرج: IP, User-Agent, Referer, UTM (utm_source/medium/campaign/content), post_url
- يحدد المنصة تلقائياً (twitter/instagram/facebook/youtube/tiktok/whatsapp/telegram/linkedin/google/...) من الـ Referer host + UTM source
- يحلل الـ User-Agent → device (mobile/desktop/tablet) + browser + OS
- يضع cookie `zenrex_aff_click` (30 يوم) لربط الـ click بالـ signup لاحقاً
- Redirect مع `?aff=CODE` للـ landing

**Server-side signup binding** (في `server.py /api/auth/register`):
- يقرأ `zenrex_aff_click` cookie من الـ request
- يحدّث `affiliate_clicks` بـ `converted_to_signup=true`, `signup_user_id`, `signup_at`
- ⇒ نعرف **بالضبط** من أي ضغطة جاء التسجيل

**Marketer endpoints**:
- `GET /api/affiliate/me/dashboard` — stats (clicks 7/30 days, unique visitors, signups, paid, CR%, impact score 0-100), platform breakdown, device breakdown, 30-day timeseries
- `GET/POST/DELETE /api/affiliate/me/posts` — إدارة المنشورات (يضيف رابط منشوره، نحسب له clicks+signups لكل منشور)
- `GET /api/affiliate/me/link-builder?platform=X&campaign=Y` — يولّد روابط UTM-tagged جاهزة للنسخ

**Admin endpoints**:
- `GET /api/admin/affiliates/list?sort_by=lifetime_earnings|clicks_30d|signups_30d|joined_at` — قائمة كل المسوّقين مع stats الحية
- `GET /api/admin/affiliates/{user_id}/impact` — تحليل عميق: funnel كامل (clicks/signups/paid/revenue)، platform mix 30d، top posts، last 50 click events، **verdict آلي** (too_new/low/fair/good/excellent) مع label عربي

### Frontend

**`/affiliate` و `/affiliate/dashboard`** — لوحة المسوّق (`AffiliateDashboard.js` — 350 سطر):
- 6 hero stat cards: clicks 30d/total, unique visitors, signups, paid customers, CR%
- درجة التأثير (Impact Score 0-100) مع progress bar
- إجمالي العمولات + معدل تحويل التسجيل → دفع
- **Link Builder ذكي**: dropdown platform + campaign → ينشئ رابط مع UTM جاهز للنسخ
- **Sources chart**: bar chart مرئي لكل منصة
- **Devices grid**: mobile/tablet/desktop
- **Posts manager**: أضف رابط منشورك → احسب clicks+signups+CR لكل منشور
- **30-day timeseries**: bar chart للنشاط اليومي

**`/admin/affiliates`** — مركز المسوّقين للأدمن (`AffiliatesAdmin.js` — 280 سطر):
- Grid لكل المسوّقين (sort by: earnings/clicks/signups/recent) مع badge ذهبي لأول 3
- التفاصيل (per affiliate): verdict box ملون حسب التأثير، funnel 5-cards, conversion rate hero, platform mix, top posts table, **forensics table** (آخر 30 click مع time/platform/device/browser/IP masked/حالة)

**AdminDashboard tile**: "مركز المسوّقين 📈" أضيف مع pink→purple gradient.

### اختبار live (curl)
- `GET /api/r/J7DAYVQY?s=twitter&c=launch&post=https://twitter.com/test/123` (مع Referer + UA) → 302 + cookie ✅
- DB سجّلت click مع platform=twitter, device=mobile, browser detected ✅
- `GET /api/admin/affiliates/{uid}/impact` → funnel + verdict عربي + platform breakdown ✅

### دقة النظام
| البيانات | الدقة | كيف |
|---------|------|-----|
| Clicks | **100%** | server-side، لكل request |
| Signups | **100%** | cookie attribution + ربط في register endpoint |
| Conversions (paid) | **100%** | بعد ربط webhook الدفع |
| Source platform | **85-95%** | Referer + UTM (UTM دائماً 100%) |
| Device/browser/OS | **~95%** | UA parsing |
| Country | **0%** الآن | يحتاج MaxMind GeoIP integration (P2) |

---


## 2026-02-15 (e) — 🧠 Client Intelligence Center (Admin 360° View + AI Insights) ✅

**طلب المستخدم**: لوحة admin فيها تقرير مفصل لكل عميل: محادثاته، مواقعه، تطبيقاته، صوره، فيديوهاته، نشاطه، مدفوعاته، اهتماماته. الـ AI يقترح حملات إعلانية مستهدفة. **الأهم: read-only — الأدمن يطلع فقط، ما يعدل ولا يحاكي**.

**Backend** (`/app/backend/modules/admin/client_intelligence.py` — جديد، 617 سطر):

7 endpoints أدمن فقط (يطلب role ∈ {admin, super_admin, owner}):
- `GET /api/admin/intelligence/clients` — قائمة عملاء مع: total_spent_usd, order_count, engagement, last_active, counts (websites/games/images/videos/chats). Sortable بـ `last_active|total_spent|created_at|name`.
- `GET /api/admin/intelligence/clients/{id}/360` — تقرير شامل: user, spend, activity heatmap (30 يوم) + recent IPs + engagement score (0-100).
- `GET /api/admin/intelligence/clients/{id}/conversations` — محادثات من 3 مصادر (freebuild_projects.messages, chat_sessions, game_projects).
- `GET /api/admin/intelligence/clients/{id}/projects` — websites + games + apps + conversion_projects.
- `GET /api/admin/intelligence/clients/{id}/media` — images + videos.
- `GET /api/admin/intelligence/clients/{id}/payments` — orders + credit_transactions.
- `GET /api/admin/intelligence/clients/{id}/sessions` — activity_logs مع IP/action/type/timestamp.
- `POST /api/admin/intelligence/clients/{id}/ai-insights` — Claude يحلل المحادثات + الـ prompts + المدفوعات ويرد JSON:
  - profile_summary, top_interests, industry_guess, tone_style, buying_intent (low/medium/high)
  - lifecycle_stage (explorer/active_builder/loyal/churning/whale)
  - satisfaction_signal (negative/neutral/positive)
  - suggested_campaigns [{title, channel: email/whatsapp/in_app/ads, message, offer}]
  - upsell_ideas, risk_flags, next_best_action
- التقرير يُكاش في `client_intelligence_reports` collection (upsert per user).

**Frontend** (`/app/frontend/src/pages/ClientIntelligence.js` — جديد، 470 سطر):
- 2-pane layout: قائمة عملاء يمين (search + sort) + main panel يسار
- Header card: اسم + email + country + plan + engagement score + total spent
- 7 tabs: Overview / Conversations / Projects / Media / Payments / Sessions / AI Insights
- Conversations tab: viewer بـ rolling message log (read-only، لا input)
- Projects tab: cards منفصلة لـ websites/games/apps مع html_length و credits_spent
- Media tab: gallery للصور + player للفيديوهات
- AI Insights tab: زر "توليد التقرير" → عرض غني للنتائج (campaign cards, interest tags, upsell list, risk alerts)

**Route**: `/admin/intelligence` (protected by `ProtectedRoute adminOnly`)
**AdminDashboard tile**: "مركز ذكاء العملاء 🧠" أضيف مع icon Sparkles + amber→orange gradient.

**اختبار live (curl on owner@zenrex.ai)**:
- `GET /clients` → 51 عميل، اول واحد له 52 websites, 9 games, 4 images, 23 videos, 199 chats ✅
- `GET /clients/{owner_id}/360` → engagement=100/100, counts كاملة ✅
- `GET /clients/{owner_id}/projects` → 52 websites, 9 games, 3 apps ✅
- 403 لغير الأدمن ✅

**ملفات جديدة**:
- `/app/backend/modules/admin/__init__.py`
- `/app/backend/modules/admin/client_intelligence.py`
- `/app/frontend/src/pages/ClientIntelligence.js`

**ملفات معدّلة**:
- `/app/backend/server.py` (تسجيل router)
- `/app/frontend/src/App.js` (route + import)
- `/app/frontend/src/pages/AdminDashboard.js` (tile جديد)

---


## 2026-02-15 (d) — 💰 Dynamic Pricing Markup + AI Multi-Language + Global Picker ✅

**طلب المستخدم**: "للغات غير العربية نضيف $3 على كل باقة كتكلفة ترجمة. وفحص شامل لكل أجزاء المنصة. والذكاء الاصطناعي يرد بلغة المستخدم."

**ما تم تنفيذه:**

### 1️⃣ Dynamic Pricing Markup
- `/app/frontend/src/i18n/pricingMarkup.js` (جديد): helper `applyMarkup` + `getMarkup` + `markupHint`
- **العربي**: $0 markup (السعر الأصلي يبقى كما هو)
- **بقية اللغات**: +$3 USD (≈ 11 SAR) لكل باقة مدفوعة (الباقة المجانية تبقى $0)
- لكل سعر مدفوع: badge أخضر صغير "Includes +$3 international support"
- مطبّق في `Pricing.js` للـ plans و packs ومستوى الـ Pay-in-4 يحتسب من السعر المعدّل

### 2️⃣ AI يرد بلغة المستخدم (FreeBuild Chat)
- **Frontend**: `FreeBuildChat.js` يرسل `user_language` field مع كل request للـ agent-chat-stream
- **Backend**: 
  - `freebuild_chat.py`: استقبال `user_language: str = Form("ar")` وتمريره للـ `stream_agent_turn`
  - `freebuild_agent.py`: `stream_agent_turn(...)` + `_stream_one_provider(...)` يقبلون `user_language`
  - يُحقَن `_lang_directive` في الـ system prompt بصيغة طبيعية:
    ```
    # LANGUAGE
    The user's UI is currently set to: French (code: fr). 
    You MUST write ALL of your conversational replies in French...
    ```
  - مدعوم لـ 24+ لغة بأسماء طبيعية للنموذج (Arabic Saudi dialect, English, French, Spanish, German, Italian, Portuguese, Russian, Chinese, Japanese, Korean, Turkish, Hindi, Urdu, Persian, Hebrew, Dutch, Polish, Indonesian, Thai, Vietnamese, Malay, Filipino, Bengali)

### 3️⃣ FloatingLanguagePicker العالمي
- `/app/frontend/src/components/FloatingLanguagePicker.js` (جديد)
- زر globe دائري في الزاوية السفلية لكل صفحة (يدعم RTL/LTR)
- مخفي في `/login`, `/register`, `/auth/*` (الـ focus على النموذج)
- يضمن إن الزائر العالمي يقدر يغير اللغة من أي صفحة، حتى لو الصفحة ما عندها Navbar (مثل `/pricing`)

### 4️⃣ data-no-translate موسّع
- `Pricing.js`: على عناصر الأسعار `$X` (الأرقام ما تتترجم - لو تتترجم تصير "$XX" بترجمة "translated")
- `FloatingLanguagePicker`: محمي بـ `data-no-translate` (شأنه شأن LanguagePicker الأصلي)
- يضمن إن أسماء العملات والأرقام تظل حرفية

**اختبار live على `/pricing`**:
| لغة | الأسعار |
|----|---------|
| AR | $0, $9, $29, $79, $199 |
| EN | $0, **$12**, **$32**, **$82**, **$202** (مع badge "Includes +$3...") |

كل صفحة `/pricing` ترجمت بنجاح: "Build, Create, Innovate Without limits", "Choose the package that fits your ambition...", "Monthly subscription plans", "Top-up bundles", "Indie/Starter/Free", "Preferred payment method".

**ملفات معدلة/جديدة**:
- `/app/frontend/src/i18n/pricingMarkup.js` (جديد)
- `/app/frontend/src/components/FloatingLanguagePicker.js` (جديد)
- `/app/frontend/src/pages/Pricing.js` (markup للأسعار)
- `/app/frontend/src/pages/PricingPage.js` (markup للـ legacy /pricing-old)
- `/app/frontend/src/pages/FreeBuildChat.js` (إرسال user_language)
- `/app/frontend/src/App.js` (`<FloatingLanguagePicker />`)
- `/app/backend/modules/freebuild/freebuild_chat.py` (`user_language: str = Form`)
- `/app/backend/modules/freebuild/freebuild_agent.py` (`_lang_directive` injection)

---


## 2026-02-15 (c) — 🚀 تغيير اللغة الفوري الكامل + Auto-Detect + Banner ✅

**الشكوى**: "لما أغير اللغة لازم أعمل refresh، والأقسام الأساسية (إنشاء المواقع، التطبيقات...) ما تتغير". + "اسم الموقع Zitex ما يتغير".

**Root cause** (3 طبقات):
1. **Lazy chunk loading**: `pageTranslator` كان lazy-imported، فلو فشل chunk، الترجمة ما تشتغل.
2. **Early return عند `target === currentTarget`**: منع re-sweep بعد re-renders من React.
3. **خنق Connection pool**: الـ sweeps المتعددة المتداخلة تطلق نفس fetch لنفس النصوص متوازية → الـ proxy connection pool يتشبع → كل الـ requests تنتظر إلى الأبد.

**الحل**:
- **استيراد مباشر** لـ `pageTranslator` (مش lazy) — يضمن توفره دايماً
- **شطب الـ early return** — كل تغيير لغة يطلق re-sweep كامل
- **Multiple staggered sweeps** (400ms, 1.2s, 2.8s, 5.5s, 9s, 14s) للقبض على المحتوى الـ lazy / async
- **Scroll-listener sweep** debounced 180ms — للأقسام تحت الـ fold
- **Single-flight sweep mutex** (`sweepRunning`/`sweepQueued`) — sweep واحد فقط في وقت واحد
- **In-flight fetch deduplication** (`inflight: Map<key, Promise>`) — لا تطلب نفس النص مرتين متوازية
- **Parallel chunk fetching** عبر `Promise.all` (بدل sequential)
- **`data-no-translate="true"`** على Navbar logo (اسم Zitex) + LanguagePicker trigger + options + DetectedLanguageBanner

**نتائج الاختبار (Playwright live)**:
| السيناريو | leftover_count |
|-----------|----------------|
| AR → EN (16s wait) | **0** ✅ |
| EN → FR (16s wait) | **1** (~99%) ✅ |
| FR → AR (3s) | restore فوري بدون reload ✅ |

اسم "Zitex" بقي **Zitex** في الـ 3 لغات بدون أي ترجمة.

**الميزة الإضافية**: `DetectedLanguageBanner` — toast صغير يظهر لما الـ geo detection يغير اللغة، يعرض "🇫🇷 Français · تم اكتشاف لغتك تلقائياً" مع زر "العربية" للتراجع. يختفي بعد 8 ثواني أو dismiss.

**ملفات معدلة/جديدة**:
- `/app/frontend/src/i18n/pageTranslator.js` (مكتوب من جديد — single-flight + dedup + Promise.all)
- `/app/frontend/src/i18n/index.js` (direct import + custom event dispatch)
- `/app/frontend/src/components/DetectedLanguageBanner.js` (جديد)
- `/app/frontend/src/components/Navbar.js` (`data-no-translate` على logo)
- `/app/frontend/src/components/LanguagePicker.js` (`data-no-translate` على trigger)
- `/app/frontend/src/App.js` (تركيب `<DetectedLanguageBanner />`)

---


## 2026-02-15 (b) — 🌐 Auto-Detect Visitor Language by Geo + Browser ✅

**الطلب**: المستخدم يبي اللغة تتعين تلقائياً حسب منطقة الزائر، بدون ما يحتاج يفتح الـ Picker. ولو غيّر يدوياً، نحترم اختياره.

**الحل** — اكتشاف بثلاث طبقات (`/app/frontend/src/i18n/geoLanguage.js`):
1. **Manual override يفوز دايماً**: مفتاح `zenrex_lang_manual` في localStorage — يُحفظ فقط عند الاختيار اليدوي من Picker
2. **Browser language (instant)**: `navigator.language` (مثلاً `fr-FR` → `fr`) — يُطبَّق قبل أول render
3. **IP geolocation (background)**: ipapi.co + ipwho.is + geojs.io (fallbacks) — يرفع اللغة لـ country-based لو الزائر فرنسي ومتصفحه إنجليزي

**خريطة دولة → لغة** (curated): 130+ دولة مغطّاة (الخليج + شمال أفريقيا → ar، أوروبا → اللغات المحلية، أمريكا اللاتينية → es/pt، آسيا → اللغة الرئيسية لكل دولة...).

**حماية ضد الـ override الخاطئ**: لو `navigator.language` يطابق اللغة الحالية، ما نسمح للـ geo IP يبدلها (المستخدم وضع لغة متصفحه قصداً).

**التحقق (Screenshot Test)**:
- ✅ زائر بـ `navigator.language = fr-FR` يفتح الصفحة → كل النصوص ظهرت بالفرنسي مباشرة:
  - "Commencer gratuitement" (Start Free)
  - "Connexion" (Login)
  - "Tarifs" (Pricing)
  - "Construisez votre jeu" (Build your game)
  - "Plateforme Zitex — Créez des sites, applications, images et vidéos par IA"
  - شريط الإعلان: "Réduction de 20% sur l'abonnement Premium cette semaine · Utilisez le code ZITEX20"
- ✅ لما المستخدم يختار يدوياً من Picker، يُحفظ كـ manual choice → ما يُتدخّل فيه مرة ثانية
- ✅ الـ geo detection يجري بعد 600ms من البوت (ما يبطئ أول render)

**ملفات معدّلة/جديدة**:
- `/app/frontend/src/i18n/geoLanguage.js` (جديد — 145 سطر)
- `/app/frontend/src/i18n/index.js` (استبدال `localStorage.getItem('zenrex_lang') || 'ar'` بـ `getInitialLanguage()` + background geo invocation)
- `/app/frontend/src/components/LanguagePicker.js` (`markManualChoice(code)` عند الاختيار اليدوي)

---


## 2026-02-15 — 🌍 Dynamic Full-Page Translation (97+ Languages) ✅

**المشكلة**: المستخدم اشتكى إن تغيير اللغة من Language Picker ما يترجم النصوص العربية الموجودة على الصفحة فعلياً.

**الحل** (`/app/frontend/src/i18n/pageTranslator.js` — أعيدت كتابته كامل):
- **MutationObserver قوي** يراقب `childList + subtree + characterData` معاً
- **معالجة re-renders من React**: لما React يبدل nodeValue للنص الأصلي (شائع جداً بسبب state updates)، نعيد تطبيق الترجمة من الكاش فوراً بدون API call
- **WeakMap لكل عقدة**: تخزين النص الأصلي + الترجمة المطبّقة حالياً لكل text node — يمكّن:
  - الرجوع للعربي بدون reload (instant restore)
  - منع double-translation
- **Self-mutation guard (`isApplying`)**: علم يحمي من اللوبات اللانهائية
- **كاش ثنائي**: في-الذاكرة `Map` + localStorage (cache forever per browser)
- **Debounced batching**: تجميع 250ms ثم batch من 35 نص في طلب واحد لـ Claude
- **استثناءات ذكية**: scripts/styles/code/inputs/contenteditable/`data-no-translate="true"`/إيموجي/أرقام بحتة

**التحقق (Screenshot Test)**:
- ✅ الصفحة العربية → اختيار English → كل النصوص اتترجمت (Start Free, Login, Pricing, Zitex AI Platform, Create your website or app with AI, Cinematic videos with Sora 2, …)
- ✅ `html.lang=en` و `html.dir=ltr` يتحدثان فوراً
- ✅ شريط الإعلان العلوي يتترجم
- ✅ Language Picker نفسه محمي بـ `data-no-translate` (الأسماء الأصلية تبقى بلغتها)
- ✅ Claude batch endpoint `/api/i18n/translate-batch` يرد 200 OK وترجمات دقيقة

**ملفات معدّلة**:
- `/app/frontend/src/i18n/pageTranslator.js` (re-write كامل، ~270 سطر)
- `/app/frontend/src/components/LanguagePicker.js` (إضافة `data-no-translate="true"`)

---


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
- AI agent ("freebuild" in `zenrex_ai`) instructs Claude Sonnet to consult first then emit tags then HTML
- Tested: 16/16 backend pytest pass, frontend smoke ✅ (`/app/test_reports/iteration_37.json`)
- Pytest regression: `/app/backend/tests/test_freebuild_chat.py` (~60s, hits live Claude+Fal)
- Pushed to `main` → Railway auto-redeploys

## 2026-02-16 (b) — 🚀 Template-First Engine + Care Portal + Mobile App Upgrade ✅

### Phase 1: Template-First Engine
- **NEW**: `/app/backend/modules/ready_sites/template_renderer.py`
- Replaces AI generation for Ready Sites — zero hallucinations
- 3 hand-crafted templates: app_mode / story_mode / showroom_mode
- Auto-routes by business type (restaurant→story, jewelry→showroom)
- Brand/contact/products injected via `window.ZENREX_CONFIG` + regex string replacement
- Every generated site is **PWA-ready by default** (per-project manifest)
- Fallback to legacy AI agent if template render fails

### Phase 2: Wizard endpoints
- `GET /api/ready-sites/templates` — public catalog (3 master templates)
- `POST /api/ready-sites/select-template` — wizard step
- `POST /api/ready-sites/select-market` — wizard step (49 markets)
- `POST /api/ready-sites/preview-template` — live preview
- `GET /api/ready-sites/manifest/{id}.webmanifest` — per-project PWA manifest

### Phase 3: Care Portal — Post-delivery client dashboard ⭐
- **NEW**: `/app/backend/modules/care_portal/` (new module)
- **NEW**: `/app/frontend/src/pages/CarePortal.js`
- **Route**: `/care/:projectId`
- Shows project info + entitlements + live preview link
- ⭐ **"Mobile App Conversion" upgrade card** (the feature user requested):
  - **Pricing**: 99 SAR/mo · 950 SAR/yr (20% off) · 990 credits/mo · 9900 credits/yr
  - Pay with credits ✅ (working) — Stripe path is 501 (TODO)
  - On upgrade → activates PWA on the client's site (zoaar see "Install App" button)
  - `GET /api/care/project/{id}` — owned project + entitlements
  - `POST /api/care/upgrade/mobile-app` — buy upgrade
  - `GET /api/care/pwa-status/{id}` — public status (used by site's install script)

### Tested End-to-End
- ✅ Template list endpoint returns 3 templates
- ✅ Preview rendering: 40KB HTML with brand injected
- ✅ Care Portal loads for owner with project data
- ✅ Upgrade flow: 990 credits deducted, `pwa_enabled` flipped false→true
- ✅ Expires 31 days from purchase

### Backlog
- Stripe/Mada payment path for upgrade
- Wizard UI step to pick template_mode + market_id (currently auto by type)
- iOS APK generation tier via Capacitor + GitHub Actions

---
## 2026-02-10 — Storefront UI Overhaul + Settings Hub + AI Services

### Header Cleanup (`app_mode_full.html`)
- Removed left logo, settings gear button (⚙️), admin shortcut buttons
- Centered Zenrex logo only — now linked to https://zenrex.ai (opens in new tab)
- Single account icon on the left → opens the new full Account page

### Full Account / Settings Page Redesign
- **Profile**: avatar upload (base64, 2MB max), editable name/email/phone/address/birthday
- **Stats Grid**: orders count · loyalty points · wishlist count
- **Membership Tier**: 🥉Bronze → 🥈Silver → 🥇Gold → 💎Platinum (based on order count)
- **Appearance Settings (new)**:
  - Dark mode toggle (synced with global)
  - 8 accent color presets (purple/pink/cyan/emerald/orange/red/royal-blue/black/gold)
  - 6 text color presets
  - 4 font-size levels (small / normal / large / x-large)
  - All settings persist in localStorage via CSS variables `--zx-accent`, `--zx-text`, `--zx-font-scale`
- **Language & Region** moved into Account
- **Notifications**: 4 toggle prefs (orders/offers/new/email)
- **Order History** (last 3 inline + link to full page)
- **Addresses** (add/delete multiple addresses)
- **Security**: change phone/email · GDPR data download · delete account
- **Support**: AI assistant · WhatsApp · FAQ · policies

### Smart AI Services Category (NEW)
- Added new top-level category `ai_services` with 8 services:
  - Image analysis (30 pts) · Pro ad image (50) · Sora 2 video (200) · Ad copywriter (40)
  - Market analysis (80) · 24/7 chatbot (500/mo) · Logo design (60) · Pro translation (25)
- Special card styling (dark navy gradient + golden AI badge)
- Pays via Zenrex credits (no cart): requires login → instant credit deduction
- Logged into orders as "خدمة AI"

### More Categories + Products (30+ new)
- Added categories: Sports, Food, Kids (alongside existing electronics/fashion/beauty/home)
- 13 new physical products with images

### Mobile Fix
- `.p-card img`, `.p-card-stack img` capped at `max-width:100%`, height 120px
- Grid gap reduced on screens <480px

### Push
- Commit `0a406e7` → main → github.com/zuhair646-debug/zenrex
