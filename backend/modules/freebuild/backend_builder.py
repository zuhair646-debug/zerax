"""
🔧 Backend Builder Agent — Phase 3 of Independence
═════════════════════════════════════════════════════════════════════

The Builder so far has produced STATIC sites. For the $799 Independence
customer who actually needs a backend (e-commerce, dashboards, user
accounts, etc.), this module generates a complete FastAPI + MongoDB
backend from the Discovery blueprint.

Stack (fixed for MVP — matches Zenrex's own production):
    FastAPI 0.115 + Motor (async MongoDB) + Pydantic v2 + JWT auth
    + Docker + GitHub Actions CI/CD

Flow:
    1. `analyze_blueprint(blueprint)` — Claude derives entities,
       endpoints, auth requirements as strict JSON.
    2. `generate_backend(project, blueprint, analysis)` — produces
       a dict of {filename: content} that gets bundled into the
       Independence Kit ZIP under `api/`.

Public API:
    await build_backend_kit(project) -> Dict[str, str]
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from modules.shared.claude_simple import ask_claude

_logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Analysis prompt — extracts a strict schema from the blueprint
# ─────────────────────────────────────────────────────────────────────

_ANALYSIS_SYSTEM_PROMPT = """أنت مهندس بنية برمجية. أعطيك blueprint مشروع (vertical + phases + essentials + answers).
استخرج تصميم backend متكامل بصيغة JSON صارمة (لا نص قبل أو بعد).

**نموذج الإخراج المطلوب:**
{
  "needs_backend": true,
  "needs_auth": true,
  "stack": "fastapi_mongo",
  "entities": [
    {
      "name": "Movie",
      "name_plural": "movies",
      "fields": [
        {"name": "id", "type": "str", "primary": true},
        {"name": "title", "type": "str", "required": true},
        {"name": "description", "type": "str", "required": false},
        {"name": "year", "type": "int", "required": false},
        {"name": "rating", "type": "float", "required": false},
        {"name": "image_url", "type": "str", "required": false},
        {"name": "created_at", "type": "datetime", "auto": true}
      ],
      "endpoints": ["list", "create", "get", "update", "delete"],
      "public_read": true
    }
  ],
  "auth": {
    "user_fields": ["email", "password_hash", "name"],
    "registration": true,
    "login": true,
    "roles": ["user", "admin"]
  },
  "extra_endpoints": []
}

**قواعد:**
- نوع الحقل من: str | int | float | bool | datetime | list[str]
- استخدم أسماء PascalCase للـentity name وsnake_case للـfield name
- name_plural يكون route prefix (lowercase + جمع)
- إذا الـmode إعلامي/تسويقي فقط (موقع تعريفي): needs_backend = false
- إذا فيه auth، فلازم تكون entities تربط بـuser_id (سيُضاف تلقائياً)
- لا تنشئ entity للـUser — auth.user_fields يكفي
- ركّز على الـessentials فقط — لا تخمّن

أعد JSON فقط، بدون أي نص.
"""


_FALLBACK_ANALYSIS = {
    "needs_backend": True,
    "needs_auth": True,
    "stack": "fastapi_mongo",
    "entities": [
        {
            "name": "Item",
            "name_plural": "items",
            "fields": [
                {"name": "id", "type": "str", "primary": True},
                {"name": "title", "type": "str", "required": True},
                {"name": "description", "type": "str", "required": False},
                {"name": "created_at", "type": "datetime", "auto": True},
            ],
            "endpoints": ["list", "create", "get", "update", "delete"],
            "public_read": True,
        }
    ],
    "auth": {
        "user_fields": ["email", "password_hash", "name"],
        "registration": True,
        "login": True,
        "roles": ["user", "admin"],
    },
    "extra_endpoints": [],
}


async def analyze_blueprint(blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """Call Claude to derive a backend schema from the discovery blueprint."""
    if not blueprint:
        return _FALLBACK_ANALYSIS

    user_msg = json.dumps({
        "vertical": blueprint.get("vertical"),
        "vertical_name_ar": blueprint.get("vertical_name_ar"),
        "vertical_summary_ar": blueprint.get("vertical_summary_ar"),
        "phases": blueprint.get("phases", []),
        "essentials": blueprint.get("essentials", []),
        "optional_modules": blueprint.get("optional_modules", []),
        "answers": blueprint.get("answers", {}),
    }, ensure_ascii=False)

    try:
        raw = await ask_claude(
            system=_ANALYSIS_SYSTEM_PROMPT,
            user_message=user_msg,
            max_tokens=3000,
            timeout=90.0,
        )
        # Strip code-fence if present
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return _FALLBACK_ANALYSIS
        data = json.loads(m.group(0))
        # Validate minimum shape
        if not isinstance(data.get("entities"), list):
            return _FALLBACK_ANALYSIS
        return data
    except Exception as e:  # noqa: BLE001
        _logger.warning("analyze_blueprint failed (%s) — using fallback", e)
        return _FALLBACK_ANALYSIS


# ─────────────────────────────────────────────────────────────────────
# File generators
# ─────────────────────────────────────────────────────────────────────

_PYTHON_TYPE_MAP = {
    "str": "str",
    "int": "int",
    "float": "float",
    "bool": "bool",
    "datetime": "datetime",
    "list[str]": "List[str]",
}


def _pascal(name: str) -> str:
    """Normalize an entity name to PascalCase."""
    parts = re.split(r"[\s_-]+", str(name).strip())
    return "".join(p.capitalize() for p in parts if p) or "Item"


def _snake(name: str) -> str:
    parts = re.findall(r"[A-Za-z][a-z0-9]*", str(name))
    return "_".join(p.lower() for p in parts) or "item"


def _gen_models(entities: List[Dict[str, Any]], auth: Dict[str, Any]) -> str:
    """Generate Pydantic models for each entity."""
    lines: List[str] = [
        '"""Pydantic models — auto-generated by Zenrex Backend Builder."""',
        "from __future__ import annotations",
        "",
        "from datetime import datetime",
        "from typing import List, Optional",
        "",
        "from pydantic import BaseModel, EmailStr, Field",
        "",
    ]

    # User model first (if auth)
    if auth and auth.get("registration"):
        lines += [
            "class UserBase(BaseModel):",
            '    email: EmailStr',
            '    name: str',
            "",
            "class UserRegister(UserBase):",
            '    password: str = Field(..., min_length=6)',
            "",
            "class UserLogin(BaseModel):",
            '    email: EmailStr',
            '    password: str',
            "",
            "class User(UserBase):",
            '    id: str',
            '    role: str = "user"',
            '    created_at: datetime',
            "",
            "class Token(BaseModel):",
            '    access_token: str',
            '    token_type: str = "bearer"',
            "",
        ]

    # Entity models
    for ent in entities:
        name = _pascal(ent.get("name") or "Item")
        fields = ent.get("fields") or []

        create_lines = [f"class {name}Create(BaseModel):"]
        full_lines = [f"class {name}(BaseModel):"]
        has_field = False
        for f in fields:
            fname = _snake(f.get("name") or "")
            ftype = _PYTHON_TYPE_MAP.get(f.get("type") or "str", "str")
            if f.get("primary") or fname == "id":
                full_lines.append("    id: str")
                continue
            if f.get("auto"):
                full_lines.append(f"    {fname}: {ftype}")
                continue
            required = bool(f.get("required"))
            if required:
                create_lines.append(f"    {fname}: {ftype}")
                full_lines.append(f"    {fname}: {ftype}")
            else:
                create_lines.append(f"    {fname}: Optional[{ftype}] = None")
                full_lines.append(f"    {fname}: Optional[{ftype}] = None")
            has_field = True
        if not has_field:
            create_lines.append("    pass")
        lines += create_lines + [""] + full_lines + [""]

    return "\n".join(lines) + "\n"


def _gen_route(ent: Dict[str, Any], auth_enabled: bool) -> str:
    """Generate a CRUD route file for one entity."""
    name = _pascal(ent.get("name") or "Item")
    plural = _snake(ent.get("name_plural") or (name.lower() + "s"))
    public_read = bool(ent.get("public_read"))
    endpoints = ent.get("endpoints") or ["list", "create", "get", "update", "delete"]
    auth_dep = (
        "    user=Depends(get_current_user),"
        if auth_enabled else ""
    )

    body = f'''"""Auto-generated CRUD route — /{plural}"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models import {name}, {name}Create
{"from app.auth import get_current_user" if auth_enabled else ""}
from app.db import get_db

router = APIRouter(prefix="/api/{plural}", tags=["{plural}"])


def _now():
    return datetime.now(timezone.utc)


def _from_mongo(doc: dict) -> dict:
    if not doc:
        return doc
    if "_id" in doc:
        doc.pop("_id", None)
    return doc

'''
    if "list" in endpoints:
        body += f'''
@router.get("", response_model=List[{name}])
async def list_{plural}(
    skip: int = 0,
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db["{plural}"].find().skip(skip).limit(min(limit, 200))
    items = []
    async for doc in cursor:
        items.append(_from_mongo(doc))
    return items
'''

    if "create" in endpoints:
        if auth_enabled and not public_read:
            body += f'''
@router.post("", response_model={name})
async def create_{_snake(name)}(
    payload: {name}Create,
{auth_dep}
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["user_id"] = user["user_id"]
    doc["created_at"] = _now()
    await db["{plural}"].insert_one(doc)
    return _from_mongo(doc)
'''
        else:
            body += f'''
@router.post("", response_model={name})
async def create_{_snake(name)}(
    payload: {name}Create,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = _now()
    await db["{plural}"].insert_one(doc)
    return _from_mongo(doc)
'''

    if "get" in endpoints:
        body += f'''
@router.get("/{{item_id}}", response_model={name})
async def get_{_snake(name)}(item_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db["{plural}"].find_one({{"id": item_id}})
    if not doc:
        raise HTTPException(404, "غير موجود")
    return _from_mongo(doc)
'''

    if "update" in endpoints:
        body += f'''
@router.patch("/{{item_id}}", response_model={name})
async def update_{_snake(name)}(
    item_id: str,
    payload: {name}Create,
{auth_dep if auth_enabled else ""}
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    update = {{k: v for k, v in payload.model_dump().items() if v is not None}}
    r = await db["{plural}"].find_one_and_update(
        {{"id": item_id}},
        {{"$set": update}},
        return_document=True,
    )
    if not r:
        raise HTTPException(404, "غير موجود")
    return _from_mongo(r)
'''

    if "delete" in endpoints:
        body += f'''
@router.delete("/{{item_id}}")
async def delete_{_snake(name)}(
    item_id: str,
{auth_dep if auth_enabled else ""}
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    r = await db["{plural}"].delete_one({{"id": item_id}})
    if r.deleted_count == 0:
        raise HTTPException(404, "غير موجود")
    return {{"ok": True}}
'''
    return body


def _gen_auth_module() -> str:
    return '''"""JWT auth — auto-generated by Zenrex Backend Builder."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models import User, UserRegister, UserLogin, Token
from app.db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


def _now():
    return datetime.now(timezone.utc)


def _hash(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


def _verify(pwd: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pwd.encode(), hashed.encode())
    except Exception:
        return False


def _create_token(user_id: str, email: str, role: str = "user") -> str:
    secret = os.environ.get("JWT_SECRET", "change-me-in-production")
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": _now() + timedelta(days=30),
        "iat": _now(),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not creds or not creds.credentials:
        raise HTTPException(401, "غير مسجل الدخول")
    try:
        secret = os.environ.get("JWT_SECRET", "change-me-in-production")
        payload = jwt.decode(creds.credentials, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "الجلسة منتهية")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "غير صالح")
    return {"user_id": user_id, "email": payload.get("email"), "role": payload.get("role", "user")}


@router.post("/register", response_model=Token)
async def register(payload: UserRegister, db: AsyncIOMotorDatabase = Depends(get_db)):
    existing = await db["users"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(400, "البريد مسجل مسبقاً")
    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id,
        "email": payload.email,
        "name": payload.name,
        "password_hash": _hash(payload.password),
        "role": "user",
        "created_at": _now(),
    }
    await db["users"].insert_one(doc)
    return Token(access_token=_create_token(user_id, payload.email, "user"))


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db["users"].find_one({"email": payload.email})
    if not doc or not _verify(payload.password, doc.get("password_hash", "")):
        raise HTTPException(401, "بيانات غير صحيحة")
    return Token(access_token=_create_token(doc["id"], doc["email"], doc.get("role", "user")))


@router.get("/me", response_model=User)
async def me(user=Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db["users"].find_one({"id": user["user_id"]})
    if not doc:
        raise HTTPException(404)
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc
'''


def _gen_db_module() -> str:
    return '''"""MongoDB connection — auto-generated by Zenrex Backend Builder."""
from __future__ import annotations

import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None


def _get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        url = os.environ.get("MONGO_URL", "mongodb://mongo:27017")
        _client = AsyncIOMotorClient(url)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    name = os.environ.get("DB_NAME", "app_db")
    return _get_client()[name]
'''


def _gen_server(entities: List[Dict[str, Any]], auth_enabled: bool) -> str:
    imports = []
    includes = []
    for ent in entities:
        plural = _snake(ent.get("name_plural") or (ent.get("name", "items").lower() + "s"))
        imports.append(f"from app.routes.{plural} import router as {plural}_router")
        includes.append(f"app.include_router({plural}_router)")
    auth_import = "from app.auth import router as auth_router" if auth_enabled else ""
    auth_include = "app.include_router(auth_router)" if auth_enabled else ""

    return f'''"""FastAPI server — auto-generated by Zenrex Backend Builder.

Start (dev):
    uvicorn app.server:app --reload --port 8000

Start (prod, via Docker):
    docker compose up -d api
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

{auth_import}
{chr(10).join(imports)}

app = FastAPI(
    title="API",
    version="1.0.0",
    description="Auto-generated by Zenrex.ai Independence Tier",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {{"ok": True, "service": "api"}}


{auth_include}
{chr(10).join(includes)}
'''


def _gen_requirements() -> str:
    return """# Auto-generated by Zenrex Backend Builder
fastapi==0.115.0
uvicorn[standard]==0.30.6
motor==3.5.3
pymongo==4.8.0
pydantic[email]==2.9.2
python-multipart==0.0.20
PyJWT==2.10.1
bcrypt==4.2.1
python-dotenv==1.1.0
"""


def _gen_dockerfile_api() -> str:
    return """# API Dockerfile — Zenrex Independence Backend
FROM python:3.11-slim
WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \\
    CMD curl -fs http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
"""


def _gen_compose_fullstack(project_slug: str) -> str:
    """Full-stack compose: web (nginx) + api (FastAPI) + mongo."""
    return f"""# docker-compose.yml — Full-stack (web + api + mongo)
# Generated by Zenrex Independence Kit (Phase 3 — Backend Builder)
version: "3.9"
services:
  web:
    build: .
    image: {project_slug}-web:latest
    container_name: {project_slug}_web
    restart: unless-stopped
    ports:
      - "${{HOST_HTTP_PORT:-80}}:80"
    environment:
      - TZ=${{TZ:-Asia/Riyadh}}
    networks:
      - {project_slug}_net
    depends_on:
      - api

  api:
    build:
      context: .
      dockerfile: api/Dockerfile.api
    image: {project_slug}-api:latest
    container_name: {project_slug}_api
    restart: unless-stopped
    ports:
      - "${{HOST_API_PORT:-8000}}:8000"
    environment:
      - MONGO_URL=mongodb://mongo:27017
      - DB_NAME=${{DB_NAME:-app_db}}
      - JWT_SECRET=${{JWT_SECRET:-change-me-in-production}}
      - CORS_ORIGINS=${{CORS_ORIGINS:-*}}
      - TZ=${{TZ:-Asia/Riyadh}}
    networks:
      - {project_slug}_net
    depends_on:
      - mongo

  mongo:
    image: mongo:7
    container_name: {project_slug}_mongo
    restart: unless-stopped
    volumes:
      - {project_slug}_mongo_data:/data/db
    networks:
      - {project_slug}_net

volumes:
  {project_slug}_mongo_data:

networks:
  {project_slug}_net:
    driver: bridge
"""


def _gen_github_actions(project_slug: str) -> str:
    return f"""# .github/workflows/deploy.yml
# Auto-generated by Zenrex Backend Builder.
# On push to main: SSH into the VPS, pull latest, rebuild Docker stack.
#
# Required GitHub Secrets:
#   VPS_HOST       — IP or hostname of your Hetzner server
#   VPS_USER       — usually 'root' (or a non-root sudo user)
#   VPS_SSH_KEY    — private SSH key (PEM format) with access to the VPS
name: Deploy {project_slug}

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{{{ secrets.VPS_SSH_KEY }}}}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -H ${{{{ secrets.VPS_HOST }}}} >> ~/.ssh/known_hosts

      - name: Deploy
        run: |
          ssh -i ~/.ssh/deploy_key ${{{{ secrets.VPS_USER }}}}@${{{{ secrets.VPS_HOST }}}} <<'EOF'
            set -e
            cd /opt/app
            git pull origin main || true
            docker compose pull || true
            docker compose up -d --build
            docker system prune -f
          EOF
"""


def _gen_env_example_backend(auth_enabled: bool) -> str:
    return f"""# .env.example — copy to .env and fill REAL values on your VPS
# DO NOT commit .env to git (it's in .gitignore)

# ─── Database ─────────────────────────────────────────────────────
MONGO_URL=mongodb://mongo:27017
DB_NAME=app_db

# ─── Server ───────────────────────────────────────────────────────
HOST_HTTP_PORT=80
HOST_API_PORT=8000
TZ=Asia/Riyadh

# ─── CORS ─────────────────────────────────────────────────────────
# Comma-separated list of allowed origins. Use * for any (dev only)
CORS_ORIGINS=*

{'# ─── JWT (REQUIRED — change in production!) ──────────────────────' if auth_enabled else ''}
{'JWT_SECRET=change-me-to-a-long-random-string-32+-chars' if auth_enabled else ''}

# ─── Future ───────────────────────────────────────────────────────
# STRIPE_SECRET_KEY=sk_live_XXXX
# SENDGRID_API_KEY=SG.XXXX
"""


def _gen_backend_readme(entities: List[Dict[str, Any]], auth_enabled: bool, project_name: str) -> str:
    ent_table_rows = []
    for ent in entities:
        plural = _snake(ent.get("name_plural") or (ent.get("name", "items").lower() + "s"))
        ent_table_rows.append(
            f"| `{ent.get('name')}` | `/api/{plural}` | GET, POST, PATCH, DELETE |"
        )
    rows = "\n".join(ent_table_rows) or "| — | — | — |"

    auth_section = ""
    if auth_enabled:
        auth_section = """
## 🔐 Auth Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/auth/register` | POST | إنشاء حساب جديد |
| `/api/auth/login` | POST | تسجيل دخول |
| `/api/auth/me` | GET | بيانات الحساب الحالي (يحتاج Bearer token) |

كل CRUD endpoints محمية بـJWT. أضف الـheader:

```
Authorization: Bearer <token-من-login>
```
"""

    return f"""# {project_name} — Backend API

> Auto-generated by Zenrex.ai Backend Builder (Independence Tier $799)

FastAPI + MongoDB backend جاهز للإنتاج. هذا الجزء يتشغّل تلقائياً مع الـweb عن طريق `docker-compose up`.

## 🚀 تشغيل سريع

```bash
# على الـVPS — كل شيء مع بعض
docker compose up -d

# تأكد إن الـAPI شغّال
curl http://localhost:8000/api/health
# → {{"ok": true, "service": "api"}}
```

## 📂 بنية المجلد

```
api/
├── Dockerfile.api          # صورة الـAPI (Python 3.11 + FastAPI)
├── requirements.txt        # حزم Python
└── app/
    ├── server.py           # نقطة الدخول الرئيسية
    ├── models.py           # Pydantic models لكل entity
    ├── db.py               # اتصال MongoDB (Motor)
    {"├── auth.py             # JWT auth (register/login/me)" if auth_enabled else ""}
    └── routes/             # CRUD routes (entity واحد لكل ملف)
```

## 📋 Entities المُولّدة

| Entity | Route prefix | Methods |
|---|---|---|
{rows}
{auth_section}

## 🛠️ التعديل

كل entity في ملف منفصل تحت `api/app/routes/`. لإضافة endpoint جديد:

```python
@router.post("/{{item_id}}/like")
async def like_item(item_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    await db["likes"].insert_one({{"item_id": item_id, "ts": _now()}})
    return {{"ok": True}}
```

## 🔍 OpenAPI Docs

FastAPI يولّد docs تلقائياً:
- Swagger UI: `http://your-server:8000/docs`
- ReDoc: `http://your-server:8000/redoc`

## 🚨 قبل الإنتاج

1. **غيّر JWT_SECRET** في `.env` لسلسلة عشوائية طويلة (32+ حرف).
2. **اضبط CORS_ORIGINS** للدومين الفعلي بدلاً من `*`.
3. **فعّل MongoDB auth** (root user + password في `MONGO_URL`).
4. **فعّل HTTPS** (Caddy في `deploy.sh` يفعّلها تلقائياً لو حطّيت دومين).
"""


# ─────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────

async def build_backend_kit(project: Dict[str, Any]) -> Dict[str, str]:
    """Build a complete FastAPI + MongoDB backend from the project's
    Discovery blueprint. Returns {filename: content} for ZIP packing.

    Files are namespaced under `api/` so they live alongside the static
    frontend in the Independence ZIP.
    """
    blueprint = (project.get("discovery") or {})
    analysis = await analyze_blueprint(blueprint)

    if not analysis.get("needs_backend"):
        # Marketing/brochure site — no backend at all. Return a placeholder
        # README so the customer understands explicitly.
        return {
            "api/README.md": (
                "# Backend\n\nبناءً على تحليل المشروع، هذا الموقع تعريفي/تسويقي "
                "ولا يحتاج backend. إذا تريد إضافة وظائف لاحقاً (نموذج تواصل، "
                "نشرة بريدية، إلخ)، تواصل مع `support@zenrex.ai`.\n"
            ),
        }

    entities = analysis.get("entities") or []
    auth_cfg = analysis.get("auth") or {}
    auth_enabled = bool(auth_cfg.get("registration") or auth_cfg.get("login"))

    project_name = project.get("name") or "Zenrex Project"
    project_slug = _snake((project.get("name") or "zenrex-app").replace(" ", "-"))[:30] or "zenrex-app"

    files: Dict[str, str] = {}
    files["api/Dockerfile.api"] = _gen_dockerfile_api()
    files["api/requirements.txt"] = _gen_requirements()
    files["api/app/__init__.py"] = ""
    files["api/app/server.py"] = _gen_server(entities, auth_enabled)
    files["api/app/models.py"] = _gen_models(entities, auth_cfg)
    files["api/app/db.py"] = _gen_db_module()
    files["api/app/routes/__init__.py"] = ""

    if auth_enabled:
        files["api/app/auth.py"] = _gen_auth_module()

    for ent in entities:
        plural = _snake(ent.get("name_plural") or (ent.get("name", "items").lower() + "s"))
        files[f"api/app/routes/{plural}.py"] = _gen_route(ent, auth_enabled)

    files["api/README.md"] = _gen_backend_readme(entities, auth_enabled, project_name)
    files[".env.example"] = _gen_env_example_backend(auth_enabled)
    files[".github/workflows/deploy.yml"] = _gen_github_actions(project_slug)
    # Override the static-only compose with full-stack version
    files["docker-compose.yml"] = _gen_compose_fullstack(project_slug)

    return files
