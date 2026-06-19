"""Site-to-App Converter — takes an existing website (either one the user
already built inside Zenrex, or an external URL they provide) and produces
a structured "conversion plan" used to seed a new App project.

Pipeline:
  1. scan(url)   — fetch HTML, parse title/description/sections/assets.
  2. plan(scan)  — turn the scan into a phased App-build plan.
  3. start()     — provision a new freebuild_projects doc with mode='app',
                   pre-loaded with the plan and the scanned current_html.

Public endpoints:
  POST /api/site-to-app/scan        body: {source: 'project'|'url', url? | project_id?}
  POST /api/site-to-app/start       body: {scan_id, platform, tech_stack, category}
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

log = logging.getLogger("zenrex.site_to_app")

SCAN_TIMEOUT = 15
MAX_HTML_BYTES = 2_000_000   # 2 MB


# ─── Pydantic ─────────────────────────────────────────────────────────────
class ScanIn(BaseModel):
    source: str = Field(..., description="'project' or 'url'")
    url: Optional[str] = None
    project_id: Optional[str] = None


class StartIn(BaseModel):
    scan_id: str
    platform: str = "both"          # ios | android | both
    tech_stack: str = "pwa"         # pwa | react_native | flutter | native_ios | native_android
    category: Optional[str] = None  # e-commerce | services | content | community | other
    app_name: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────
async def _fetch_html(url: str) -> str:
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    async with httpx.AsyncClient(
        timeout=SCAN_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 ZenrexSiteScanner/1.0"},
    ) as c:
        r = await c.get(url)
        if r.status_code >= 400:
            raise HTTPException(400, f"Could not fetch {url} ({r.status_code})")
        text = r.text
        if len(text.encode("utf-8")) > MAX_HTML_BYTES:
            text = text[:MAX_HTML_BYTES]
        return text, str(r.url)


def _analyze_html(html: str, base_url: str) -> Dict[str, Any]:
    """Extract metadata + content summary from a webpage's HTML."""
    soup = BeautifulSoup(html, "html.parser")
    # Strip script/style for plain-text counting.
    for s in soup(["script", "style", "noscript"]):
        s.extract()
    title = (soup.title.string or "").strip() if soup.title else ""
    desc = ""
    md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if md and md.get("content"):
        desc = md["content"].strip()
    lang = (soup.html or {}).get("lang", "ar") if soup.html else "ar"

    # Section detection — semantic + heuristic
    sections: List[Dict[str, str]] = []
    for el in soup.find_all(["section", "main", "article"], limit=20):
        h = el.find(["h1", "h2", "h3"])
        if h:
            t = h.get_text(strip=True)[:80]
            if t:
                sections.append({"heading": t, "tag": el.name})

    # Headings
    headings = [h.get_text(strip=True)[:120] for h in soup.find_all(["h1", "h2"], limit=30) if h.get_text(strip=True)]

    # Links + nav items
    nav_links: List[str] = []
    for nav in soup.find_all("nav", limit=4):
        for a in nav.find_all("a", limit=12):
            t = a.get_text(strip=True)
            if t and len(t) <= 60:
                nav_links.append(t)

    # Images
    images = []
    for img in soup.find_all("img", limit=40):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        images.append({"src": src, "alt": (img.get("alt") or "")[:80]})

    # Forms
    forms = []
    for form in soup.find_all("form", limit=10):
        inputs = [i.get("name") or i.get("type") or "?" for i in form.find_all(["input", "textarea", "select"])]
        forms.append({"action": form.get("action") or "", "inputs": inputs[:10]})

    # Heuristics: detect features
    text_lower = html.lower()
    features = {
        "ecommerce": any(k in text_lower for k in ["add to cart", "أضف إلى السلة", "checkout", "السلة", "buy now"]),
        "booking": any(k in text_lower for k in ["book now", "احجز الآن", "appointment", "موعد"]),
        "blog": bool(soup.find("article")) or any(k in text_lower for k in ["blog", "مدونة", "post"]),
        "contact_form": any("contact" in (f.get("action") or "").lower() or "تواصل" in str(soup) for f in soup.find_all("form")),
        "video": bool(soup.find_all(["video", "iframe"]) and any("youtube" in (i.get("src") or "") or "vimeo" in (i.get("src") or "") for i in soup.find_all("iframe"))),
        "auth": any(k in text_lower for k in ["login", "تسجيل الدخول", "sign in", "register", "إنشاء حساب"]),
    }

    # Page-by-page guess (from nav links)
    inferred_pages = list({n.lower().strip() for n in nav_links if 2 <= len(n) <= 40})[:8]

    return {
        "url": base_url,
        "lang": lang,
        "title": title or base_url,
        "description": desc,
        "sections": sections[:12],
        "headings": headings[:15],
        "nav_links": nav_links[:12],
        "inferred_pages": inferred_pages,
        "images_count": len(soup.find_all("img")),
        "images_sample": images[:6],
        "forms": forms,
        "features": features,
        "text_chars": len(soup.get_text()),
    }


def _build_plan(scan: Dict[str, Any], platform: str, tech_stack: str) -> Dict[str, Any]:
    """Generate a phased conversion plan + what info we still need."""
    f = scan["features"]
    must_collect: List[Dict[str, str]] = []

    if f["ecommerce"]:
        must_collect.append({"key": "stripe_key", "label": "مفتاح Stripe", "why": "لتفعيل الدفع داخل التطبيق."})
        must_collect.append({"key": "product_catalog", "label": "كتالوج المنتجات (JSON أو CSV)", "why": "لاستيراد المنتجات والأسعار."})
    if f["booking"]:
        must_collect.append({"key": "calendar_url", "label": "Google Calendar / Calendly link", "why": "لربط الحجوزات."})
    if f["auth"]:
        must_collect.append({"key": "auth_provider", "label": "نوع التسجيل (Email / Google / Apple)", "why": "تكوين شاشات الدخول."})
    if f["video"]:
        must_collect.append({"key": "video_provider", "label": "مزوّد الفيديو", "why": "تضمين الفيديوهات بطريقة محسّنة للموبايل."})
    if f["contact_form"]:
        must_collect.append({"key": "support_email", "label": "إيميل دعم العملاء", "why": "استلام رسائل نموذج التواصل."})

    # Always recommended
    must_collect.extend([
        {"key": "brand_logo", "label": "شعار التطبيق (PNG ≥ 512×512)", "why": "أيقونة التطبيق و Splash screen."},
        {"key": "brand_colors", "label": "الألوان الأساسية (HEX)", "why": "هوية التطبيق."},
    ])

    # Unsupported-as-is (manual rebuild needed)
    cant_auto = []
    if scan["text_chars"] > 50_000:
        cant_auto.append("الموقع يحتوي على نصوص ضخمة جداً (سنختصرها ونعيد ترتيبها للجوال)")
    if any("webgl" in str(s).lower() for s in scan["headings"]):
        cant_auto.append("صفحات WebGL/3D معقّدة — سنحتاج إعادة تنفيذ يدوية")
    for form in scan["forms"]:
        if len(form["inputs"]) > 12:
            cant_auto.append("نماذج كبيرة جداً — سنقسّمها إلى خطوات على الموبايل")
            break

    phases = [
        {"id": 1, "title": "هيكل التطبيق", "summary": f"إنشاء Shell PWA + manifest + service worker لـ {platform}.", "estimated_minutes": 3},
        {"id": 2, "title": "الشاشة الرئيسية", "summary": f"تحويل صفحة `{scan['title']}` إلى شاشة Home موبايل.", "estimated_minutes": 5},
        {"id": 3, "title": "شاشات الأقسام", "summary": f"بناء {len(scan['inferred_pages']) or 3} شاشات إضافية حسب التنقل.", "estimated_minutes": 8},
    ]
    if f["ecommerce"]:
        phases.append({"id": 4, "title": "متجر + سلّة + دفع", "summary": "كتالوج منتجات + cart + Stripe checkout.", "estimated_minutes": 12})
    if f["auth"]:
        phases.append({"id": len(phases) + 1, "title": "تسجيل دخول وحساب", "summary": "شاشات Login/Signup + Profile.", "estimated_minutes": 6})
    phases.append({"id": len(phases) + 1, "title": "تجميع + اختبار", "summary": "تشغيل HTML Validator + Auto-Heal + قياس Site Health.", "estimated_minutes": 3})

    return {
        "platform": platform,
        "tech_stack": tech_stack,
        "phases": phases,
        "must_collect": must_collect,
        "cant_auto_convert": cant_auto,
        "estimated_total_minutes": sum(p["estimated_minutes"] for p in phases),
    }


# ─── Router ───────────────────────────────────────────────────────────────
def make_site_to_app_router(db, get_current_user):
    router = APIRouter(prefix="/api/site-to-app", tags=["site-to-app"])

    @router.post("/scan")
    async def scan(payload: ScanIn, user=Depends(get_current_user)):
        # Source: project (already in our DB) OR url (external)
        if payload.source == "project":
            if not payload.project_id:
                raise HTTPException(400, "project_id required")
            proj = await db.freebuild_projects.find_one(
                {"id": payload.project_id, "user_id": user["user_id"]},
                {"current_html": 1, "name": 1, "id": 1},
            )
            if not proj:
                raise HTTPException(404, "Project not found")
            if not proj.get("current_html"):
                raise HTTPException(400, "هذا المشروع لا يحتوي على موقع مبني بعد")
            html = proj["current_html"]
            analysis = _analyze_html(html, f"internal://{proj['id']}")
            source_label = f"مشروع Zenrex: {proj.get('name')}"
        elif payload.source == "url":
            if not payload.url:
                raise HTTPException(400, "url required")
            try:
                html, final_url = await _fetch_html(payload.url)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(400, f"تعذّر جلب الموقع: {e}")
            analysis = _analyze_html(html, final_url)
            source_label = analysis["url"]
        else:
            raise HTTPException(400, "source must be 'project' or 'url'")

        scan_id = uuid.uuid4().hex
        record = {
            "id": scan_id,
            "user_id": user["user_id"],
            "source": payload.source,
            "source_label": source_label,
            "url": payload.url or None,
            "project_id": payload.project_id or None,
            "html": html[:MAX_HTML_BYTES],
            "analysis": analysis,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.site_to_app_scans.insert_one(record)
        return {
            "scan_id": scan_id,
            "source_label": source_label,
            "analysis": analysis,
        }

    @router.post("/plan")
    async def plan(payload: StartIn, user=Depends(get_current_user)):
        scan = await db.site_to_app_scans.find_one(
            {"id": payload.scan_id, "user_id": user["user_id"]},
            {"_id": 0, "analysis": 1, "source_label": 1},
        )
        if not scan:
            raise HTTPException(404, "Scan not found")
        plan = _build_plan(scan["analysis"], payload.platform, payload.tech_stack)
        return {"plan": plan, "source_label": scan["source_label"]}

    @router.post("/start")
    async def start(payload: StartIn, user=Depends(get_current_user)):
        scan = await db.site_to_app_scans.find_one(
            {"id": payload.scan_id, "user_id": user["user_id"]}
        )
        if not scan:
            raise HTTPException(404, "Scan not found")
        analysis = scan["analysis"]
        plan = _build_plan(analysis, payload.platform, payload.tech_stack)
        pid = uuid.uuid4().hex
        app_name = payload.app_name or f"تطبيق {analysis['title'][:40]}"
        now = datetime.now(timezone.utc).isoformat()
        intro_msg = (
            f"مرحبا بك في المحوّل 🔁\n\n"
            f"حلّلت الموقع: **{scan['source_label']}**\n\n"
            f"📊 الملخّص:\n"
            f"- العنوان: {analysis['title']}\n"
            f"- اللغة: {analysis['lang']}\n"
            f"- عدد الصور: {analysis['images_count']}\n"
            f"- روابط القائمة: {len(analysis['nav_links'])}\n"
            f"- ميزات مكتشَفة: {', '.join([k for k,v in analysis['features'].items() if v]) or 'أساسية فقط'}\n\n"
            f"🎯 خطّة التحويل ({len(plan['phases'])} مراحل ~ {plan['estimated_total_minutes']} دقيقة):\n"
            + "\n".join([f"  {p['id']}. {p['title']} — {p['summary']}" for p in plan["phases"]])
            + (f"\n\n⚠️ هذي الأمور تحتاج إعادة بناء يدوية:\n" + "\n".join([f"  • {x}" for x in plan["cant_auto_convert"]]) if plan["cant_auto_convert"] else "")
            + (f"\n\n📥 احتاج منك المعلومات التالية لما نوصل لمرحلتها:\n" + "\n".join([f"  • {x['label']} — {x['why']}" for x in plan["must_collect"]]) if plan["must_collect"] else "")
            + "\n\nجاهز نبدأ المرحلة الأولى؟"
        )
        project_doc = {
            "id": pid,
            "user_id": user["user_id"],
            "name": app_name,
            "description": f"تحويل من {scan['source_label']}",
            "mode": "app",
            "platform": payload.platform,
            "tech_stack": payload.tech_stack,
            "site_to_app_scan_id": scan["id"],
            "source_url": scan.get("url"),
            "source_project_id": scan.get("project_id"),
            "conversion_plan": plan,
            "current_phase": "discovery",
            "current_html": "",  # AI will rebuild for mobile
            "messages": [{
                "id": uuid.uuid4().hex,
                "role": "assistant",
                "content": intro_msg,
                "options": [],
                "inline_images": [],
                "timestamp": now,
            }],
            "approved_assets": [],
            "status": "active",
            "code_unlocked": False,
            "unlocked": False,
            "created_at": now,
            "updated_at": now,
        }
        await db.freebuild_projects.insert_one(project_doc)
        return {"project_id": pid, "name": app_name, "plan": plan}

    return router
