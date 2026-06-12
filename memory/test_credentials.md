# Test Credentials

## Audit Test User (created Feb 8 2026 — for non-owner E2E tests)
- Email: `audit_1780793976@test.com`
- Password: `Test1234!`
- Role: regular user
- Starting credits: 20

## Merchant Control Panel (Real Backend Auth — Feb 2026)
- URL: `${REACT_APP_BACKEND_URL}/mockups/admin.html`
- Login: `owner@zenrex.ai` / `owner123` (real JWT via `/api/auth/login`)
- Products now persist to MongoDB via `/api/store/products` (per-merchant scoped by `merchant_id`)
- Customer login on storefront: any phone, OTP = `1234` (real backend via `/api/store/customer/request-otp` + `/verify-otp`)
- Wishlist + Reviews sync to MongoDB when customer is logged in

## Platform Owner (Admin)
- URL: `/login`
- Email: `owner@zenrex.ai`
- Password: `owner123`
- **Note**: Domain migrated from `@zitex.com` to `@zenrex.ai` during the Zenrex rebrand (Feb 16 2026).

## 📧 Owner Notification Email (Jun 11 2026)
- **Personal Gmail (receives all forwarded mail)**: `zenrex.ai@gmail.com`
- All domain emails (`owner@zenrex.ai`, `support@zenrex.ai`, `hello@zenrex.ai`, `info@zenrex.ai`) should forward to this Gmail via Porkbun Email Forwarding.

## 🔌 Track 1 — Real Data Wiring Complete (Jun 11 2026 14:10)

User requested comprehensive E2E testing before official launch. Testing agent (iter_42) discovered 3 blockers: (1) storefront orders never persisted, (2) admin showed 100% hardcoded demo data, (3) "Zerax Owner" leftover in admin sidebar. ALL THREE FIXED in this session, retested via iter_43.

**Backend changes** (`/app/backend/routers/delivery_router.py`):
- Added `_mongo_save_order()` helper → `update_one({"id":...}, {"$set": order}, upsert=True)` against `db.delivery_orders`.
- Added `_mongo_load_orders()` → boot-time hydration repopulates in-memory `ORDERS` dict from MongoDB so admin sees orders after restarts.
- Hooked into `create_order` so every POST persists to MongoDB.
- Server startup event: `@app.on_event("startup") async def _hydrate_delivery_orders()` in `server.py`.
- Expanded `OrderIn.payment_method` Literal: added `cod`, `mada`, `tabby`, `tamara`, `apple_pay`, `zenrex_split`, `zenrex_later`, `stripe`.
- Demo seed orders disabled by default (set `ENABLE_DEMO_ORDERS=1` to re-enable).

**Frontend changes** (`/app/frontend/public/mockups/app_mode_full.js`):
- `choosePay(id, el)` now validates `ck-name` + `ck-phone` then `fetch('/api/delivery/orders', {method:'POST', body: payload})` BEFORE showing success modal. Items use `{name, qty, sar}` matching the Pydantic model.
- Success modal injects the real `order.id` so customer can reference it.
- localStorage `my_orders` array for customer's "طلباتي" view.

**Admin changes** (`/app/frontend/public/mockups/admin.js`):
- `renderOrders()` is now `async` and calls `loadRealOrders()` → fetches `/api/delivery/orders?limit=50`. Falls back to clearly-labeled `(تجريبي)` rows only when DB is empty.
- `renderAll()` fetches `recent-orders` (limit 8) + `/api/delivery/stats` for KPI values (revenue, total_orders, active_drivers).
- New helpers: `_relTime(iso)` for "قبل X د" formatting, `_stLabel(st)` for Arabic status labels.

**Onboarding modal**:
- `closeOnboarding()` and `finishOnboarding()` BOTH set `localStorage.zx_onboarded='1'` so the 4-step welcome never blocks navigation after first dismissal.

**Database migration**:
- `users.name`: `"Zerax Owner"` → `"Zenrex Owner"` (mongosh `$replaceAll`).

**Storefront footer**:
- `+966512345678` → `+966 500 000 000`
- `info@brand.sa` → `support@zenrex.ai`

**Live verification (https://zenrex.ai)**:
- 5 real orders in MongoDB (4 from API tests, 1 from actual UI Playwright flow as `مختبر التدفق الكامل / 0599888777 / 99 ر.س / drv_555ee6ea`).
- Admin sidebar shows `Zenrex Owner` (verified screenshot `/tmp/admin_real_orders_final.png`).
- POST `/api/delivery/orders` from storefront confirmed via network trace.
- Auto driver assignment + Haversine + driver-share / merchant-share calculations all functional.
- Test report iteration_43 retest: PASS on rebrand/footer/onboarding/admin-real-data. Single remaining flake was driver OTP automation selector (not a backend issue).

## ⏸️ Pending Tracks (deferred to next session — context window limit):
- ~~**Track 2 — Payment UI Polish**~~ ✅ DONE Jun 11 14:25 — Card-input modal with sandbox-mode hints (`4242 4242 4242 4242`), live preview of card number / name / expiry, CVC validation, "Powered by Zenrex Pay · SSL 256-bit" footer. Triggered when user picks `card` / `mada` / `visa` / `mastercard` payment method.
- ~~**Track 3 — Business Category Templates**~~ ✅ DONE Jun 11 14:26 — 8 turnkey templates rendered in admin nav `قوالب الأعمال`: 💈 حلاقة, ✏️ قرطاسية, 🍔 مطعم, 💊 صيدلية, ☕ كافيه, 💅 صالون نسائي, 📱 إلكترونيات, 👗 أزياء. Each template = 6 categories + 6 sample products. One-click `applyBusinessTemplate()` POSTs to `/api/store/products` to seed merchant catalog. Stored in `/app/frontend/public/mockups/business_templates.js`.
- ~~**Track 4 — Driver app real-time order feed**~~ ✅ DONE Jun 11 14:24 — `loadOrders()` rewritten to fetch `/api/delivery/orders?limit=50` and filter by `driver_phone` for `mine` vs `pending` for `available`. `startRealOrderPolling()` runs every 15s while driver is online (`.sb-status.active.online`).



## 🔐 Stored API Credentials (Jun 12 2026)

**Already-configured in `/app/backend/.env` (auto-resolved by `_get_cred()` env-var aliases):**
- `FAL_KEY=423f71b4-16b5-46e1-ade6-...` → resolves for `fal_key` (Cinema Studio video generation works out of the box).
- `VERCEL_TOKEN=vcp_6CiuacOvaOswjxZ1uS2J...` → resolves for `vercel_token` (Vercel deploys work).
- `RESEND_API_KEY=re_dzXgkb3L_...` → resolves for `resend_key` (email sending works).
- `GITHUB_PAT=ghp_FhBF...` (account: `zuhair646-debug`, scope=`repo`) → resolves for `github_pat`.

**Currently invalid (needs replacement from user):**
- `ELEVENLABS_API_KEY=sk_1615de2ff615...` → returns HTTP 401. Get fresh key at https://elevenlabs.io → Profile → API Keys.

**How keys are looked up:** The AI calls `validate_credential(service)` which first checks the per-project encrypted store (`freebuild_credentials` collection), then falls back to `os.environ` aliases. So a key in `.env` works for ALL projects without needing per-project `save_credential`.

## 🌐 Production VPS (Hetzner — Jun 11 2026)
- **Public URL**: `https://zenrex.ai`
- **SSH**: `ssh -i /root/.ssh/zerax_deploy root@91.98.154.148`
- **Admin/Merchant dashboard**: `https://zenrex.ai/mockups/admin.html`
- **Customer storefront**: `https://zenrex.ai/mockups/app_mode_full.html`
- **Driver app**: `https://zenrex.ai/mockups/driver_app.html`
- **Same credentials apply** (owner@zenrex.ai/owner123, phone/OTP=1234)
- **JWT_SECRET**: `zenrex-prod-jwt-secret-2026-hetzner-91-98-154-148` (fixed across restarts)
- **DB**: ⭐ **MongoDB Atlas M2** — `cluster0.1tkzj4x.mongodb.net` / `zerax_prod`
  - User: `zenrex_admin`
  - Password: `uqTwj4zKvAURQXkz`
  - Full URI: `mongodb+srv://zenrex_admin:uqTwj4zKvAURQXkz@cluster0.1tkzj4x.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0`
  - Migrated Jun 11 2026 from local `zerax-mongo-1` (146 docs, 24 collections)
  - Local container kept as fallback in `docker-compose.yml`
- **Owner seeded via**: `docker exec zenrex-backend-1 python /app/scripts/seed_owner.py`
- **Nginx config**: `/etc/nginx/sites-enabled/zenrex` (gzip enabled — 4-5x smaller payloads)
- **⚠️ LLM Blocker**: ~~EMERGENT_LLM_KEY restricted to Emergent platform~~ **RESOLVED Jun 11 2026** via direct-SDK shim (`backend/direct_llm_shim.py`).
  - When `USE_DIRECT_LLM=1` is set, `emergentintegrations.llm.chat` is transparently redirected to direct provider calls using `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_DIRECT_KEY` from `.env`.
  - **All 20+ files using `LlmChat` keep working unchanged** — the shim mimics the same interface (`with_model`, `with_params`, `send_message`, `send_message_multimodal_response`).
  - Supported providers: `anthropic` (Claude Sonnet 4.5/4.6) · `gemini` (text + Nano Banana image gen) · `openai` (GPT-4o/GPT-5).
  - Automatic fallback chain: if primary provider fails, the shim tries the others.
  - Image generation uses `gemini-3.1-flash-image` (Nano Banana current production model).
  - On Emergent's preview/dev environment: leave `USE_DIRECT_LLM` unset to continue using the universal key.

## Demo Site — Cozy Cafe Demo

### Client Dashboard (for end-client to manage their site)
- Login URL: `/client/cozy-cafe-demo`
- Password: `WKDWkG0d`

### Public URLs
- Public site: `/sites/cozy-cafe-demo`
- Shareable preview: `/api/websites/share/05VuNbyO9McTmt9Z_Hz68CG4KH0`

### Site Customer (registered via the public site's auth)
- Name: أحمد الزهراني
- Phone: `0501122334`
- Password: `pass123`

### Delivery Driver (registered via client dashboard)
- Name: فهد السائق
- Phone: `0559988776`
- Password: `drv123`

## Auth Flow Notes
- Platform auth: `Authorization: Bearer <jwt>` (existing)
- Client auth: `Authorization: ClientToken <token>` (from `/client/login`)
- Site-customer auth: `Authorization: SiteToken <token>` (from `/public/{slug}/auth/*`)
- Driver auth: `Authorization: DriverToken <token>` (from `/driver/login`)

## Stripe Subscription Gate Test User (Website Studio paywall)
- Email: `gatetest@zenrex.ai`
- Password: `test123`
- Role: client (non-owner — hits paywall)
- Has active `studio_monthly` subscription (paid via Stripe test card 4242 4242 4242 4242, 12/34, 123, ZIP 12345)
- Owner bypasses the gate automatically (no payment required)

## Stripe Test Card
- Number: `4242 4242 4242 4242`
- Expiry: any future date (e.g., `12/34`)
- CVC: any 3 digits (e.g., `123`)
- ZIP: any (e.g., `12345`)

## Zitex Auto-Coder (برمجة زيتاكس) — Owner-Only Codebase Agent
- Route: `/admin/autocoder` (requires `is_owner=true` user)
- **🔑 Current passcode (Jun 2026)**: `zenrex2026`
- **Recovery codes** (use once each if you forget the passcode):
  - `5702-2746-0033-A0B1`
  - `60F3-BBB7-2628-CE0E`
  - `8709-73CF-1C0E-FCDC`
  - `47D8-124D-3183-3BE9`
  - `832D-222C-D803-0402`
  - `6266-B1DE-07D6-7912`
- First visit shows **Setup screen** → owner picks passcode (≥6 chars) → system generates 6 one-time recovery codes
- Subsequent visits show **Lock screen** → enter passcode → 4-hour session token
- Session token stored client-side in `localStorage.zenrex_autocoder_session` and sent in `X-AutoCoder-Token` header
- Forgot passcode? → "نسيت كلمة السر؟" → enter recovery code + new passcode (consumes the recovery code; if all 6 used, system regenerates a fresh batch)
- All actions audited in `autocoder_audit` collection (visible via `GET /api/autocoder/audit`)
- Tools available to the AI: `read_file`, `write_file`, `edit_file`, `delete_file`, `list_dir`, `search_code`, `run_command` (full bash), `restart_service`, `git_status`, `git_diff`, `git_commit_push`
- Backend uses Claude Sonnet 4.5 via owner's `ANTHROPIC_API_KEY` (synced from Railway production)

## App-Mode Mockup (Merchant Admin Control Panel + Video Studio + Delivery)
- **Landing page (unified)**: `${REACT_APP_BACKEND_URL}/mockups/index.html` — 3 cards: Merchant ACP / Driver App / Customer Track
- **Customer tracking**: `${REACT_APP_BACKEND_URL}/mockups/track.html?id=<order_id>` — public Leaflet map with live driver location, ETA, status timeline
- **Driver app**: `${REACT_APP_BACKEND_URL}/mockups/driver_app.html` — phone+OTP login (5 demo phones, OTP=1234)
- **Merchant ACP**: `${REACT_APP_BACKEND_URL}/mockups/app_mode_full.html` — click ♛ to open
- ACP delivery tab has 5 sub-sections: 📦 الطلبات · 🧑‍✈️ السائقون · 🏬 الفروع · 💰 الرواتب · ⚙️ التسعير
- Recharge: click `+ شحن` inside ACP → modal with 4 packages + 5 payment methods (mada/visa/mc/apple_pay/stc_pay)

### Public API endpoints (no auth required)
- `GET  /api/promo-video/health` · `POST /api/promo-video/storyboard` · `POST /api/promo-video/generate` · `GET /api/promo-video/packages` · `POST /api/promo-video/recharge` (MOCKED gateway)
- `POST /api/image-studio/product-info` (Gemini)
- **Delivery (16+ endpoints)**:
  - Drivers CRUD: `GET/POST /api/delivery/drivers`, `PATCH/DELETE /api/delivery/drivers/{id}` (driver now has employment_type, share_per_delivery_sar OR monthly_salary_sar, payout_method, payout_account, country)
  - Driver auth: `POST /api/delivery/driver/login` (returns OTP=1234), `POST /api/delivery/driver/verify-otp`, `GET /api/delivery/driver/me`, `GET /api/delivery/driver/feed`
  - Orders: `GET/POST /api/delivery/orders`, `PATCH /api/delivery/orders/{id}/assign`, `PATCH .../status`, `POST .../location`, `GET .../track` (public, returns driver+location+timeline)
  - **NEW**: `POST /api/delivery/calculate-fee` — Haversine distance + fee breakdown + driver/merchant share preview. Body: `{customer_lat, customer_lng, total_sar, branch_id?}`
  - **NEW**: `GET/POST /api/delivery/branches`, `DELETE /api/delivery/branches/{id}` — branch GPS coords used as distance origin
  - **NEW**: `GET/POST /api/delivery/payouts?driver_id=` — payout history + record wage transfers. Decrements `balance_pending_sar` on commission drivers.
  - **NEW**: `GET /api/delivery/payout-methods?country=SA|AE|EG|KW|BH|QA|OM|IQ` — country-specific payout methods (STC Pay, urpay, PayBy, Vodafone Cash, InstaPay, KNET, ZainCash, etc.)
  - **NEW**: `GET /api/delivery/countries` — 8 supported countries with currency codes
  - Settings: `GET/PATCH /api/delivery/settings` (now includes per_km_sar, base_fee_sar, min_fee_sar, max_fee_sar, driver_share_default_pct, use_distance_pricing toggle)


