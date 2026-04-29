# Zitex AI Platform

منصّة ذكاء اصطناعي عربية لتوليد المواقع، المتاجر، الألعاب، الصور، والفيديوهات.
Independent, externally-hosted AI platform powered by conversational AI for generating websites, games, mobile apps, images, and videos.

---

## 🏗️ المعمارية (Architecture)

```
zitex/
├── backend/                      # FastAPI app (Python 3.11)
│   ├── server.py                 # Main entry — bootstraps all modules
│   ├── modules/                  # Domain-isolated modules
│   │   ├── websites/             # Website builder + verticals + e-commerce
│   │   ├── site/                 # Main Zitex site banner & stories
│   │   ├── billing/              # Stripe subscription gate
│   │   ├── operator/             # DevOps AI Agent (WS streaming)
│   │   ├── affiliate/            # Affiliate marketing program
│   │   ├── source/               # Source code browser (owner only)
│   │   ├── games/  videos/  images/   # AI generation modules
│   ├── routers/                  # Shared HTTP routers (chat, deployment, ws)
│   ├── services/                 # Shared services (AI chat, deployment)
│   ├── models/                   # Pydantic data models
│   └── tests/                    # Pytest suites
└── frontend/                     # React 19 app (Tailwind + shadcn/ui)
    ├── src/
    │   ├── pages/                # Route-level pages
    │   │   ├── client/           # Multi-tenant client dashboard
    │   │   ├── driver/           # Delivery driver dashboard
    │   │   ├── websites/         # Website Studio (chat-first builder)
    │   │   ├── designer/         # Visual designer canvas
    │   │   └── billing/          # Stripe subscription pages
    │   ├── components/
    │   │   └── ui/               # shadcn/ui primitives
    │   └── hooks/  lib/
    └── public/
```

---

## 🚀 التشغيل المحلي (Local Setup)

### 1. Backend
```bash
cd backend
cp .env.example .env       # املأ القيم
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

### 2. Frontend
```bash
cd frontend
cp .env.example .env       # REACT_APP_BACKEND_URL=http://localhost:8001
yarn install
yarn start
```

افتح: http://localhost:3000

---

## 🌐 النشر على Railway (Deployment)

- `Procfile` و `railway.json` و `backend/Dockerfile` جاهزة.
- لازم تضبط متغيرات البيئة في Railway dashboard (انظر `backend/.env.example`).
- الـ frontend ينشر بشكل منفصل على Vercel/Netlify (أو static export).

---

## 🔑 الميزات الرئيسية

- 🧠 **محادثة AI** لتوليد المواقع (Claude Sonnet 4.5 + GPT-4o)
- 🎨 **25+ vertical** متخصصة (مطاعم، صالونات، عقارات، أسهم، إلخ)
- 🛒 **متاجر إلكترونية** مع شحن سعودي (SMSA, Aramex, SPL)
- 🚚 **تتبع توصيل حي** عبر WebSocket
- 💳 **بوابات دفع متعددة** (Moyasar, Tabby, Tamara, COD)
- 🎬 **Stories + بنر متحرك** لكل متجر (Nano Banana + Sora 2)
- 🤖 **AutoPilot Stories** — جدولة محتوى ذكية
- 📊 **محرك أسهم** مع Alpha Vantage البيانات الحية
- 🔐 **Google OAuth** (Emergent-managed) + JWT email/password

---

## 🌍 اللغة (Language)

التطبيق بالكامل **عربي RTL**.
The application is fully Arabic with RTL layout.

---

## 📜 الترخيص (License)

Proprietary. © 2026 Zitex.
