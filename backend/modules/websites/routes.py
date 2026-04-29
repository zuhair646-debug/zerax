"""FastAPI routes for the Websites module — fully isolated."""
import os
import uuid
import re
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Header as _Header, Response, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .models import WebsiteProject, ChatMessageIn, AIGenerateIn
from .templates import list_templates, get_template
from .renderer import render_website_to_html
from .ai_service import (
    chat_with_consultant, extract_wizard_action, clean_display_text,
    extract_build_payload, build_sections_from_payload, detect_section_intent,
    detect_snapshot_intent,
)
from .variants import list_variants_for_template, list_style_variants, get_variant_project
from .catalog import list_categories, list_layouts, get_layout
from .logo_service import generate_logo, generate_logo_variants, generate_hero_image
from .wizard import (
    STEPS, default_wizard_state, get_step, get_question_for_step,
    get_chips_for_step, next_step_id, apply_answer, steps_metadata,
    COLOR_VARIANT_MAP, RADIUS_MAP,
)
from .realtime import realtime
from . import payment_gateways as pg
from . import widget_styles as wx
from . import section_variants as sv
from . import snapshots as snaps

logger = logging.getLogger(__name__)


class WizardStepIn(BaseModel):
    step: str
    value: Any   # string | list | dict


class WizardChatIn(BaseModel):
    message: str


class LogoGenerateIn(BaseModel):
    prompt: str
    style_hint: Optional[str] = ""


class LogoVariantsIn(BaseModel):
    prompt: str
    style_hint: Optional[str] = ""
    color_hint: Optional[str] = ""
    count: int = 3


class LogoApplyIn(BaseModel):
    logo_url: str


class HeroImageIn(BaseModel):
    prompt: str
    section_type: str = "hero"


class BuildPreviewIn(BaseModel):
    theme_override: Optional[Dict[str, Any]] = None
    sections_override: Optional[List[Dict[str, Any]]] = None


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str) -> str:
    """ASCII-safe slug generation from (possibly Arabic) text."""
    if not text:
        return "site"
    # Keep alphanumerics + dashes; replace spaces with dashes
    slug = re.sub(r"[^\w\u0600-\u06FF\s-]", "", str(text)).strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    # If mostly non-ASCII, fall back to a short random id prefix
    if not re.search(r"[a-z0-9]", slug):
        slug = f"site-{uuid.uuid4().hex[:8]}"
    return slug[:60] or f"site-{uuid.uuid4().hex[:8]}"


async def _generate_unique_slug(database, base: str) -> str:
    """Ensure slug is unique in collection."""
    slug = _slugify(base)
    candidate = slug
    i = 1
    while await database.website_projects.find_one({"slug": candidate}, {"_id": 0, "id": 1}):
        i += 1
        candidate = f"{slug}-{i}"
        if i > 99:
            candidate = f"{slug}-{uuid.uuid4().hex[:6]}"
            break
    return candidate


def _hash_pwd(pwd: str) -> str:
    import bcrypt as _b
    return _b.hashpw(pwd.encode("utf-8"), _b.gensalt()).decode("utf-8")


def _check_pwd(pwd: str, hashed: str) -> bool:
    import bcrypt as _b
    try:
        return _b.checkpw(pwd.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _rand_token(length: int = 28) -> str:
    import secrets
    return secrets.token_urlsafe(length)




def register_routes(app, database, auth_dep):
    """Mount all /api/websites/* routes onto `app` with bound db + auth."""
    r = APIRouter(prefix="/api/websites", tags=["websites"])

    # ---------------- Templates & Variants (public) ----------------
    @r.get("/templates")
    async def _t_list():
        return {"templates": list_templates()}

    @r.get("/templates/{template_id}/preview-html")
    async def _t_preview(template_id: str):
        tpl = get_template(template_id)
        project = {"name": tpl["name"], "theme": tpl["theme"], "sections": tpl["sections"], "meta": {"title": tpl["name"]}}
        return {"html": render_website_to_html(project)}

    @r.get("/variants")
    async def _v_list():
        return {"variants": list_style_variants()}

    # ---------------- Categories & Layouts (public) ----------------
    @r.get("/categories")
    async def _c_list():
        return {"categories": list_categories()}

    @r.get("/categories/{category_id}/layouts")
    async def _c_layouts(category_id: str):
        layouts = list_layouts(category_id)
        # Strip heavy sections from list response; include enough for card previews
        return {"layouts": [
            {
                "id": L["id"],
                "name": L["name"],
                "icon": L.get("icon", ""),
                "description": L.get("description", ""),
                "density": L.get("density"),
                "hero_layout": L.get("hero_layout"),
                "sections_count": L.get("sections_count") or len(L.get("sections") or []),
                "section_types": [s.get("type") for s in (L.get("sections") or [])],
                "theme": L.get("theme", {}),
                "theme_name": L.get("theme_name"),
                "hero_image": L.get("hero_image"),
            }
            for L in layouts
        ]}

    @r.get("/categories/{category_id}/layouts/{layout_id}/preview-html")
    async def _c_layout_preview(category_id: str, layout_id: str):
        L = get_layout(category_id, layout_id)
        theme = dict(L.get("theme") or {})
        if L.get("custom_css"):
            theme["custom_css"] = L["custom_css"]
        project = {"name": L["name"], "theme": theme, "sections": L["sections"], "meta": {"title": L["name"]}}
        return {"html": render_website_to_html(project)}

    @r.get("/categories/{category_id}/layouts-gallery", response_class=Response)
    async def _c_layouts_gallery(category_id: str):
        """Single HTML page showing ALL archetypes in a numbered grid for visual preview."""
        from fastapi.responses import HTMLResponse
        layouts = list_layouts(category_id)
        cards = ""
        for i, L in enumerate(layouts, 1):
            preview_url = f"/api/websites/categories/{category_id}/layouts/{L['id']}/preview-html-raw"
            cards += f"""
            <div class="card" data-num="{i}">
              <div class="num">{i}</div>
              <div class="frame-wrap">
                <iframe src="{preview_url}" loading="lazy" sandbox="allow-same-origin"></iframe>
              </div>
              <div class="name">{L.get('icon','')} {L['name']}</div>
              <div class="desc">{L.get('description','')[:80]}</div>
            </div>"""
        html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>معرض القوالب</title>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Tajawal',sans-serif;background:#0b0f1f;color:#fff;padding:20px}}
.header{{text-align:center;margin-bottom:30px}}
.header h1{{font-size:36px;font-weight:900;background:linear-gradient(135deg,#FFD700,#FF6B35);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}}
.header p{{opacity:.7;font-size:14px}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;max-width:1400px;margin:0 auto}}
@media(max-width:1100px){{.grid{{grid-template-columns:repeat(3,1fr)}}}}
@media(max-width:800px){{.grid{{grid-template-columns:repeat(2,1fr)}}}}
.card{{background:#0e1128;border:2px solid rgba(255,215,0,.15);border-radius:14px;overflow:hidden;position:relative;transition:transform .3s,border-color .3s}}
.card:hover{{transform:translateY(-4px);border-color:#FFD700}}
.num{{position:absolute;top:8px;right:8px;width:38px;height:38px;background:linear-gradient(135deg,#FFD700,#FF6B35);color:#000;font-weight:900;font-size:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;z-index:10;box-shadow:0 4px 12px rgba(255,215,0,.4)}}
.frame-wrap{{height:240px;overflow:hidden;background:#fff;position:relative}}
.frame-wrap iframe{{border:0;width:1280px;height:1600px;transform:scale(.25);transform-origin:top right;pointer-events:none}}
.name{{padding:10px 14px 4px;font-weight:700;font-size:14px}}
.desc{{padding:0 14px 12px;font-size:11px;opacity:.7;line-height:1.5;height:38px;overflow:hidden}}
</style></head><body>
<div class="header">
  <h1>📐 معرض القوالب — {len(layouts)} تصميم</h1>
  <p>كل قالب رقم واضح في الزاوية. اختر الرقم وأرسله لتطبيقه على موقعك.</p>
</div>
<div class="grid">{cards}</div>
</body></html>"""
        return HTMLResponse(content=html)

    @r.get("/categories/{category_id}/layouts/{layout_id}/preview-html-raw", response_class=Response)
    async def _c_layout_preview_raw(category_id: str, layout_id: str):
        from fastapi.responses import HTMLResponse
        L = get_layout(category_id, layout_id)
        theme = dict(L.get("theme") or {})
        if L.get("custom_css"):
            theme["custom_css"] = L["custom_css"]
        project = {
            "name": L["name"], "theme": theme, "sections": L["sections"],
            "meta": {"title": L["name"], "category_id": category_id, "layout_id": layout_id},
            "template": category_id, "business_type": category_id,
        }
        return HTMLResponse(content=render_website_to_html(project))

    # DNA Mixer — random layout for a category
    @r.get("/categories/{category_id}/mix")
    async def _c_mix(category_id: str):
        import random
        layouts = list_layouts(category_id)
        if not layouts:
            raise HTTPException(404, "No layouts")
        L = random.choice(layouts)
        theme = dict(L.get("theme") or {})
        if L.get("custom_css"):
            theme["custom_css"] = L["custom_css"]
        project = {"name": L["name"], "theme": theme, "sections": L["sections"], "meta": {"title": L["name"]}}
        return {"layout": {"id": L["id"], "name": L["name"], "icon": L.get("icon", "")},
                "html": render_website_to_html(project)}

    @r.get("/templates/{template_id}/variants")
    async def _t_variants(template_id: str):
        return {"variants": list_variants_for_template(template_id)}

    @r.get("/templates/{template_id}/variants/{variant_id}/preview-html")
    async def _v_preview(template_id: str, variant_id: str):
        project = get_variant_project(template_id, variant_id)
        return {"html": render_website_to_html(project)}

    # ---------------- Wizard meta (public) ----------------
    @r.get("/wizard/steps")
    async def _w_steps(project_id: Optional[str] = None):
        """Public — returns wizard steps metadata. project_id optional (used to merge vertical-specific steps).
        Does NOT require auth — these are just step labels/chips, not user data."""
        p = None
        if project_id:
            p = await database.website_projects.find_one({"id": project_id}, {"_id": 0})
        return {"steps": steps_metadata(p)}

    # ---------------- Projects ----------------
    @r.get("/projects")
    async def _p_list(current_user: dict = Depends(auth_dep)):
        # Auto-fix: ensure approved projects of this user have a slug
        missing = await database.website_projects.find(
            {"user_id": current_user["user_id"], "status": "approved", "slug": {"$in": [None, ""]}},
            {"_id": 0, "id": 1, "name": 1}
        ).to_list(200)
        for m in missing:
            new_slug = await _generate_unique_slug(database, m.get("name") or "site")
            await database.website_projects.update_one({"id": m["id"]}, {"$set": {"slug": new_slug}})
        items = await database.website_projects.find(
            {"user_id": current_user["user_id"]}, {"_id": 0}
        ).sort("updated_at", -1).to_list(200)
        return {"projects": items}

    @r.get("/projects/{project_id}")
    async def _p_get(project_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        return p

    @r.post("/projects")
    async def _p_create(project: WebsiteProject, current_user: dict = Depends(auth_dep)):
        now = _iso_now()
        d = project.model_dump()
        d["id"] = str(uuid.uuid4())
        d["user_id"] = current_user["user_id"]
        d["created_at"] = now
        d["updated_at"] = now
        # Resolve catalog layout if provided in meta
        layout_id = (d.get("meta") or {}).get("layout_id") if d.get("meta") else None
        category_id = d.get("template") or "blank"
        if layout_id:
            L = get_layout(category_id, layout_id)
            if not d.get("sections"):
                d["sections"] = [s.copy() for s in L["sections"]]
            theme = dict(L.get("theme") or {})
            if L.get("custom_css"):
                theme["custom_css"] = L["custom_css"]
            d["theme"] = {**theme, **(d.get("theme") or {})}
            # Store layout_id for reference
            d["meta"] = {**(d.get("meta") or {}), "layout_id": layout_id}
        else:
            # Default: use first archetype if layout_id not provided
            from .catalog import list_layouts as _ll
            layouts = _ll(category_id) or []
            if layouts:
                L = layouts[0]
                if not d.get("sections"):
                    d["sections"] = [s.copy() for s in L["sections"]]
                d["theme"] = {**(L.get("theme") or {}), **(d.get("theme") or {})}
                d["meta"] = {**(d.get("meta") or {}), "layout_id": L["id"]}
            else:
                tpl = get_template(category_id)
                if not d.get("sections"):
                    d["sections"] = [s.copy() for s in tpl["sections"]]
                    d["theme"] = {**tpl["theme"], **(d.get("theme") or {})}
        for s in d["sections"]:
            if not s.get("id"):
                s["id"] = f"sec-{uuid.uuid4().hex[:8]}"
        # Init wizard state + greet message
        is_blank = category_id == "blank"
        wiz = default_wizard_state()
        if is_blank:
            wiz["step"] = "brief"
        d["wizard"] = wiz
        # 🆕 Vertical mapping: category_id → vertical_id + seed sample data
        from . import verticals as _vx
        _category_to_vertical = {
            "restaurant": "restaurant", "coffee": "restaurant",
            "barber": "salon",
            "salon_women": "salon_women",
            "pets": "pets",
            "clinic": "medical",
            "store": "ecommerce",
            "gym": "gym",
            "academy": "academy",
            "realestate": "realestate",
            "stocks": "stocks",
            "bakery": "bakery",
            "car_wash": "car_wash",
            "sports_club": "sports_club",
            "library": "library",
            "art_gallery": "art_gallery",
            "maintenance": "maintenance",
            "jewelry": "jewelry",
            "cosmetics": "ecommerce",       # 💄 cosmetics use ecommerce engine (products + cart)
            "automotive": "automotive",     # 🏎️ cars showroom — uses dedicated automotive vertical (or fallback ecommerce)
        }
        vid = _category_to_vertical.get(category_id)
        if vid:
            d["vertical"] = vid
            v_def = _vx.get_vertical(vid) or {}
            if v_def.get("sample_services") and not d.get("services"):
                d["services"] = [{**s, "created_at": now} for s in v_def["sample_services"]]
            if v_def.get("sample_products") and not d.get("products"):
                d["products"] = [{**s, "created_at": now} for s in v_def["sample_products"]]
            if v_def.get("sample_courses") and not d.get("courses"):
                d["courses"] = [{**s, "created_at": now} for s in v_def["sample_courses"]]
            if v_def.get("sample_membership_plans") and not d.get("membership_plans"):
                d["membership_plans"] = [{**s, "created_at": now} for s in v_def["sample_membership_plans"]]
            if v_def.get("sample_listings") and not d.get("listings"):
                d["listings"] = [{**s, "created_at": now} for s in v_def["sample_listings"]]
        if is_blank:
            greet = "✨ ممتاز! اخترت قالباً مخصّصاً. صف لي نشاطك بحرّية (مثل: 'متجر قطط' أو 'عيادة أسنان حديثة') وسأبني لك تصميماً ابتكارياً فوراً."
        else:
            greet = get_question_for_step(wiz["step"], d)
        if not d.get("chat"):
            d["chat"] = [{"role": "assistant", "content": greet}]
        await database.website_projects.insert_one(d)
        d.pop("_id", None)
        return d

    @r.patch("/projects/{project_id}")
    async def _p_update(project_id: str, project: WebsiteProject, current_user: dict = Depends(auth_dep)):
        existing = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}
        )
        if not existing:
            raise HTTPException(404, "Project not found")
        update = project.model_dump(exclude={"id", "user_id", "created_at"})
        # Preserve wizard state unless sent explicitly
        if "wizard" not in update or update["wizard"] is None:
            update.pop("wizard", None)
        update["updated_at"] = _iso_now()
        await database.website_projects.update_one({"id": project_id}, {"$set": update})
        return await database.website_projects.find_one({"id": project_id}, {"_id": 0})

    @r.delete("/projects/{project_id}")
    async def _p_delete(project_id: str, current_user: dict = Depends(auth_dep)):
        res = await database.website_projects.delete_one(
            {"id": project_id, "user_id": current_user["user_id"]}
        )
        if res.deleted_count == 0:
            raise HTTPException(404, "Project not found")
        return {"ok": True}

    @r.post("/projects/{project_id}/duplicate")
    async def _p_duplicate(project_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        p["id"] = str(uuid.uuid4())
        p["name"] = f"{p.get('name','موقع')} (نسخة)"
        p["created_at"] = _iso_now()
        p["updated_at"] = _iso_now()
        await database.website_projects.insert_one(p)
        p.pop("_id", None)
        return p

    @r.post("/projects/{project_id}/build")
    async def _p_build(project_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        return {"html": render_website_to_html(p), "project_id": project_id}

    # ════════════════════════════════════════════════════════════════════
    # 🆕 LIVE EDIT MODE — Reorder sections + AI custom widget design
    # ════════════════════════════════════════════════════════════════════
    @r.post("/projects/{project_id}/reorder-sections")
    async def _p_reorder(project_id: str, body: Dict[str, Any], current_user: dict = Depends(auth_dep)):
        """Apply a new section order — body.section_ids is the desired ordered list of section ids/types."""
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        ordered_ids = body.get("section_ids") or []
        if not isinstance(ordered_ids, list) or not ordered_ids:
            raise HTTPException(400, "section_ids must be a non-empty list")
        secs = p.get("sections") or []
        by_key = {(s.get("id") or s.get("type")): s for s in secs}
        new_secs = []
        for i, key in enumerate(ordered_ids):
            s = by_key.get(key)
            if s:
                new_secs.append({**s, "order": i, "visible": True})
        seen = set(ordered_ids)
        for s in secs:
            k = s.get("id") or s.get("type")
            if k not in seen:
                new_secs.append({**s, "order": len(new_secs)})
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {"sections": new_secs, "updated_at": _iso_now()}},
        )
        p["sections"] = new_secs
        p["updated_at"] = _iso_now()
        return p

    @r.post("/projects/{project_id}/widget-ai-design")
    async def _p_widget_ai(project_id: str, body: Dict[str, Any], current_user: dict = Depends(auth_dep)):
        """Generate custom widget CSS via AI based on Arabic mood description."""
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        widget_id = (body.get("widget_id") or "").strip()
        brief = (body.get("brief") or "").strip()
        if not widget_id or not brief:
            raise HTTPException(400, "widget_id and brief are required")
        try:
            from .widget_styles import WIDGETS
            w = WIDGETS.get(widget_id)
        except Exception:
            w = None
        if not w:
            raise HTTPException(404, f"Unknown widget: {widget_id}")
        theme = p.get("theme") or {}
        primary = theme.get("primary", "#FFD700")
        secondary = theme.get("secondary", "#1a1a1a")
        prompt = (
            f"You are a CSS designer. Generate properties for a floating action button widget '{w.get('name_ar', widget_id)}'.\n"
            f"User mood (Arabic): \"{brief}\"\n"
            f"Brand colors: primary={primary}, secondary={secondary}.\n"
            "Output ONLY raw CSS property declarations (no selectors, no braces, no markdown, one per line, separated by ;).\n"
            "Include 10-14 properties: width, height, border-radius, background (use a gradient), color, border, box-shadow, font-weight, font-size, display:flex, align-items:center, justify-content:center, cursor:pointer.\n"
            "Size 50-60px circular or pill-shaped. Use the brand colors.\n"
            "Example: width:54px;height:54px;border-radius:50%;background:linear-gradient(135deg,#FFD700,#FF6B00);color:#000;border:2px solid rgba(255,255,255,.3);box-shadow:0 12px 30px rgba(255,215,0,.5);font-weight:900;font-size:22px;display:flex;align-items:center;justify-content:center;cursor:pointer;"
        )
        try:
            import litellm
            from litellm import acompletion
            key = os.environ.get("EMERGENT_LLM_KEY")
            if not key:
                raise RuntimeError("EMERGENT_LLM_KEY missing")
            litellm.api_base = "https://integrations.emergentagent.com/llm"
            resp = await acompletion(
                model="openai/gpt-4o-mini",
                api_key=key,
                api_base="https://integrations.emergentagent.com/llm",
                messages=[
                    {"role": "system", "content": "You output only valid CSS property declarations. Never markdown, never code fences."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.85,
                max_tokens=220,
            )
            css = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            raise HTTPException(500, f"AI design failed: {e}")
        css = css.replace("```css", "").replace("```", "").strip()
        if "{" in css:
            css = css.split("{", 1)[1]
        if "}" in css:
            css = css.split("}", 1)[0]
        css = css.strip()
        styles = p.get("widget_styles") or {}
        widget_state = dict(styles.get(widget_id) or {})
        widget_state["variant"] = "ai_custom"
        widget_state["ai_brief"] = brief
        widget_state["ai_css"] = css
        widget_state.pop("awaiting_ai_brief", None)
        styles[widget_id] = widget_state
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {"widget_styles": styles, "updated_at": _iso_now()}},
        )
        return {"widget_id": widget_id, "css": css, "applied": True}

    # ════════════════════════════════════════════════════════════════════
    # 🆕 SHIPPING SYSTEM — 6 Saudi providers + Geo-aware quote engine
    # ════════════════════════════════════════════════════════════════════
    @r.get("/shipping/providers")
    async def _shipping_providers():
        """Public — list all available shipping providers (for dashboard UI)."""
        from .shipping import get_all_providers_summary
        return {"providers": get_all_providers_summary()}

    @r.get("/projects/{project_id}/shipping/config")
    async def _shipping_config_get(project_id: str, current_user: dict = Depends(auth_dep)):
        """Get the shipping configuration for a store."""
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        cfg = p.get("shipping_settings") or {
            "enabled_providers": ["smsa", "aramex", "saudi_post"],
            "custom_rates": {},
            "store_city": "جدة",
            "local_delivery_enabled": True,
            "local_delivery_fee": 15,
            "local_delivery_eta_hours": "2-4",
            "free_shipping_above_sar": 200,
            "cod_markup_enabled": False,
            "cod_markup_sar": 5,
            "insurance_enabled": False,
            "insurance_percent": 2.0,
            "insurance_min_sar": 10.0,
            "pickup_enabled": False,
            "pickup_address": "",
            "pickup_hours": "",
        }
        return cfg

    @r.put("/projects/{project_id}/shipping/config")
    async def _shipping_config_put(
        project_id: str, body: Dict[str, Any], current_user: dict = Depends(auth_dep)
    ):
        """Update shipping config — owner toggles which providers are enabled, sets custom rates."""
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        allowed_keys = {
            "enabled_providers", "custom_rates", "store_city",
            "local_delivery_enabled", "local_delivery_fee",
            "local_delivery_eta_hours", "free_shipping_above_sar",
            "cod_markup_enabled", "cod_markup_sar",
            "insurance_enabled", "insurance_percent", "insurance_min_sar",
            "pickup_enabled", "pickup_address", "pickup_hours",
        }
        cfg = dict(p.get("shipping_settings") or {})
        for k, v in body.items():
            if k in allowed_keys:
                cfg[k] = v
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {"shipping_settings": cfg, "updated_at": _iso_now()}},
        )
        return cfg

    @r.post("/projects/{project_id}/shipping/quote")
    async def _shipping_quote(project_id: str, body: Dict[str, Any], request: Request):
        """
        Public — at checkout time, returns available shipping options with prices/ETAs.
        Body: { country?: "SA", city?: "جدة", weight_kg?: 1.5, cart_subtotal?: 240, ip?: auto }
        Auto-detects country/city from IP if not provided.
        """
        p = await database.website_projects.find_one({"id": project_id}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Project not found")
        from .shipping import calculate_shipping_quote, detect_country_from_ip

        country = (body.get("country") or "").strip().upper()
        city = (body.get("city") or "").strip()
        weight = float(body.get("weight_kg") or 1.0)
        subtotal = float(body.get("cart_subtotal") or 0)

        # Geolocation fallback — get from request IP
        if not country:
            client_ip = (request.client.host if request.client else "") or ""
            try:
                xff = request.headers.get("x-forwarded-for")
                if xff:
                    client_ip = xff.split(",")[0].strip()
            except Exception:
                pass
            country, city_from_ip = detect_country_from_ip(client_ip)
            if not city:
                city = city_from_ip or ""

        cfg = p.get("shipping_settings") or {
            "enabled_providers": ["smsa", "aramex", "saudi_post"],
            "store_city": "جدة",
            "local_delivery_enabled": True,
            "local_delivery_fee": 15,
            "local_delivery_eta_hours": "2-4",
            "free_shipping_above_sar": 200,
        }
        options = calculate_shipping_quote(
            project_settings=cfg,
            customer_country=country,
            customer_city=city,
            weight_kg=weight,
            cart_subtotal=subtotal,
        )
        return {
            "country": country,
            "city": city,
            "weight_kg": weight,
            "options": options,
        }

    # ---------------- Logo / Hero image generation (AI) ----------------
    @r.post("/projects/{project_id}/generate-logo")
    async def _p_generate_logo(project_id: str, body: LogoGenerateIn, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        result = await generate_logo(body.prompt, body.style_hint or "")
        if not result:
            raise HTTPException(500, "فشل توليد اللوقو — حاول بوصف مختلف")
        data_url, _sid = result
        theme = {**(p.get("theme") or {}), "logo_url": data_url}
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {"theme": theme, "updated_at": _iso_now()}},
        )
        return {"ok": True, "logo_url": data_url}

    @r.post("/projects/{project_id}/generate-logo-variants")
    async def _p_generate_logo_variants(project_id: str, body: LogoVariantsIn, current_user: dict = Depends(auth_dep)):
        """Generate N logo variants in parallel so the user can pick one by click."""
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        urls = await generate_logo_variants(body.prompt, body.style_hint or "", body.count or 3, body.color_hint or "")
        if not urls:
            raise HTTPException(500, "فشل توليد اللوقوهات — حاول بوصف أوضح")
        return {"ok": True, "logos": urls, "count": len(urls)}

    @r.post("/projects/{project_id}/apply-logo")
    async def _p_apply_logo(project_id: str, body: LogoApplyIn, current_user: dict = Depends(auth_dep)):
        """Persist a chosen logo URL onto the project's theme."""
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        theme = {**(p.get("theme") or {}), "logo_url": body.logo_url}
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {"theme": theme, "updated_at": _iso_now()}},
        )
        return {"ok": True, "logo_url": body.logo_url}

    @r.post("/projects/{project_id}/generate-hero-image")
    async def _p_generate_hero(project_id: str, body: HeroImageIn, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        url = await generate_hero_image(body.prompt)
        if not url:
            raise HTTPException(500, "فشل توليد الصورة")
        sections = list(p.get("sections") or [])
        for i, s in enumerate(sections):
            if s.get("type") == body.section_type:
                sections[i] = {**s, "data": {**(s.get("data") or {}), "image": url}}
                break
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {"sections": sections, "updated_at": _iso_now()}},
        )
        return {"ok": True, "image_url": url}

    # Preview with un-persisted theme / section overrides (used for live-before-confirm)
    @r.post("/projects/{project_id}/build-preview")
    async def _p_build_preview(project_id: str, body: BuildPreviewIn, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        theme = {**(p.get("theme") or {}), **(body.theme_override or {})}
        sections = body.sections_override if body.sections_override is not None else p.get("sections")
        return {"html": render_website_to_html({**p, "theme": theme, "sections": sections})}

    # ---------------- Color palettes catalog + apply (post-template step) ----------------
    @r.get("/palettes")
    async def _palettes_catalog():
        """10 color palettes — picked in the wizard AFTER the user selects a template.
        Decouples structure from color."""
        from .variants import STYLE_VARIANTS
        return {"palettes": [{
            "id": v["id"],
            "name": v["name"],
            "primary": v["theme_override"].get("primary"),
            "secondary": v["theme_override"].get("secondary"),
            "accent": v["theme_override"].get("accent"),
            "background": v["theme_override"].get("background"),
            "font": v["theme_override"].get("font"),
        } for v in STYLE_VARIANTS]}

    class ApplyPaletteIn(BaseModel):
        palette_id: str

    @r.post("/projects/{project_id}/apply-palette")
    async def _p_apply_palette(project_id: str, body: ApplyPaletteIn, current_user: dict = Depends(auth_dep)):
        """Apply a color palette WITHOUT touching sections (sections stay as user picked them)."""
        from .variants import STYLE_VARIANTS
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        palette = next((v for v in STYLE_VARIANTS if v["id"] == body.palette_id), None)
        if not palette:
            raise HTTPException(404, "Palette not found")
        # 📸 Snapshot pre-change
        new_snaps = snaps.push_snapshot(p, label=f"قبل تطبيق ألوان: {palette['name']}", origin="variant")
        merged_theme = {**(p.get("theme") or {}), **palette["theme_override"]}
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {"theme": merged_theme, "snapshots": new_snaps, "updated_at": _iso_now()}}
        )
        return await database.website_projects.find_one({"id": project_id}, {"_id": 0})

    # ---------------- Variant apply ----------------
    class ApplyVariantIn(BaseModel):
        template_id: str
        variant_id: str
        replace_sections: bool = False   # if False → keep current sections, only apply theme

    @r.post("/projects/{project_id}/apply-variant")
    async def _p_apply_variant(project_id: str, body: ApplyVariantIn, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        vp = get_variant_project(body.template_id, body.variant_id)
        # 📸 Snapshot pre-change
        new_snaps = snaps.push_snapshot(p, label=f"قبل تطبيق نمط: {body.variant_id}", origin="variant")
        update = {"theme": vp["theme"], "template": body.template_id, "updated_at": _iso_now(), "snapshots": new_snaps}
        if body.replace_sections:
            sections = [{**s, "id": f"sec-{uuid.uuid4().hex[:8]}"} for s in vp["sections"]]
            update["sections"] = sections
            update["business_type"] = vp["business_type"]
        await database.website_projects.update_one({"id": project_id}, {"$set": update})
        return await database.website_projects.find_one({"id": project_id}, {"_id": 0})

    # Owner-facing snapshot endpoints (parallel to /client/snapshots for the studio chat)
    @r.get("/projects/{project_id}/snapshots")
    async def _p_snapshots_list(project_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        return {"snapshots": snaps.list_snapshots_summary(p), "total": len(p.get("snapshots") or [])}

    class _OwnerSnapIn(BaseModel):
        label: Optional[str] = "نسخة يدوية"

    @r.post("/projects/{project_id}/snapshots")
    async def _p_snapshots_create(project_id: str, body: _OwnerSnapIn, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        new_snaps = snaps.push_snapshot(p, label=(body.label or "نسخة يدوية").strip()[:60], origin="manual")
        await database.website_projects.update_one(
            {"id": project_id}, {"$set": {"snapshots": new_snaps, "updated_at": _iso_now()}}
        )
        return {"ok": True, "total": len(new_snaps)}

    @r.post("/projects/{project_id}/snapshots/{snapshot_id}/restore")
    async def _p_snapshots_restore(project_id: str, snapshot_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        update = snaps.apply_snapshot(p, snapshot_id)
        if not update:
            raise HTTPException(404, "النسخة غير موجودة")
        await database.website_projects.update_one({"id": project_id}, {"$set": update})
        return await database.website_projects.find_one({"id": project_id}, {"_id": 0})

    @r.get("/projects/{project_id}/snapshots/{snapshot_id}/preview-html")
    async def _p_snapshots_preview(project_id: str, snapshot_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        snap = snaps.find_snapshot(p, snapshot_id)
        if not snap:
            raise HTTPException(404, "النسخة غير موجودة")
        payload = snap.get("payload") or {}
        virtual = {**p, **{k: v for k, v in payload.items() if v is not None}}
        return {"html": render_website_to_html(virtual), "label": snap.get("label"), "created_at": snap.get("created_at")}

    @r.delete("/projects/{project_id}/snapshots/{snapshot_id}")
    async def _p_snapshots_delete(project_id: str, snapshot_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        snaps_list = [s for s in (p.get("snapshots") or []) if s.get("id") != snapshot_id]
        await database.website_projects.update_one(
            {"id": project_id}, {"$set": {"snapshots": snaps_list, "updated_at": _iso_now()}}
        )
        return {"ok": True}

    # ---------------- Wizard: deterministic step answer (chip click) ----------------
    @r.post("/projects/{project_id}/wizard/answer")
    async def _w_answer(project_id: str, body: WizardStepIn, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        if not p.get("wizard"):
            p["wizard"] = default_wizard_state()
        # Apply
        p = apply_answer(p, body.step, body.value)
        # Append a system-style acknowledgement + next question
        chat = p.get("chat", [])
        human_label = _chip_label(body.step, body.value)
        chat.append({"role": "user", "content": human_label})
        nxt_step = p["wizard"].get("step")
        if nxt_step and nxt_step != "done":
            chat.append({"role": "assistant", "content": get_question_for_step(nxt_step, p)})
        else:
            chat.append({"role": "assistant", "content": "🎉 تمّت كل الأسئلة! راجع المعاينة — لو كل شيء تمام، اضغط 'اعتماد' من القائمة."})
        p["chat"] = chat
        # 📸 Snapshot after wizard step
        new_snaps = snaps.push_snapshot(p, label=f"خطوة: {_chip_label(body.step, body.value)}", origin="wizard")
        update = {
            "theme": p["theme"], "sections": p.get("sections", []),
            "wizard": p["wizard"], "chat": chat,
            "name": p.get("name"),
            "snapshots": new_snaps,
            "widget_styles": p.get("widget_styles") or {},
            "updated_at": _iso_now(),
        }
        await database.website_projects.update_one({"id": project_id}, {"$set": update})
        return await database.website_projects.find_one({"id": project_id}, {"_id": 0})

    # ---------------- Wizard: free-text chat (priority aware) ----------------
    @r.post("/projects/{project_id}/wizard/chat")
    async def _w_chat(project_id: str, body: WizardChatIn, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        if not p.get("wizard"):
            p["wizard"] = default_wizard_state()
        history = list(p.get("chat", []))
        history.append({"role": "user", "content": body.message})
        summary = {"name": p.get("name"), "template": p.get("template"), "business_type": p.get("business_type")}
        ai_text = await chat_with_consultant(history, wizard=p.get("wizard"), project_summary=summary)
        display = clean_display_text(ai_text)
        action = extract_wizard_action(ai_text)
        # 🕰️ Snapshot intent takes PRIORITY over AI's action (AI can mis-interpret
        # "ارجعلي للتصاميم السابقة" as remove_section). Check user message first.
        snap_intent = detect_snapshot_intent(body.message)
        if snap_intent:
            action = snap_intent
            display = "📚 فتحت لك سجل التصاميم السابقة — اختر أي نسخة لاستعادتها."
        # 🛡️ Safety net: if AI didn't emit a structural directive but the user
        # explicitly asked to add a known section type, inject the directive now.
        STRUCTURAL_ACTIONS = {"add_section", "scaffold", "fill_section", "patch_section", "remove_section", "move_section"}
        if not action or action.get("action") not in STRUCTURAL_ACTIONS:
            fallback = detect_section_intent(body.message)
            if fallback:
                action = fallback
                # Make the visible message reflect what just happened
                stype = fallback["value"]["type"]
                from .renderer import _humanize_type
                label = _humanize_type(stype)
                added_note = f"\n\n✨ تمّت إضافة قسم \"{label}\" في موقعك — شاهده في المعاينة فوراً."
                if added_note.strip() not in display:
                    display = (display or "تمام! ").rstrip() + added_note
        history.append({"role": "assistant", "content": display})
        p["chat"] = history
        # Apply AI action (if any)
        p = _apply_ai_action(p, action)
        # Handle async generate_logo directive
        if action and action.get("action") == "generate_logo" and isinstance(action.get("value"), dict):
            try:
                v = action["value"]
                result = await generate_logo(v.get("prompt", ""), v.get("style", ""))
                if result:
                    data_url, _ = result
                    p["theme"] = {**(p.get("theme") or {}), "logo_url": data_url}
            except Exception as e:
                logger.warning(f"logo gen in chat failed: {e}")
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {
                "chat": p["chat"], "theme": p.get("theme"), "sections": p.get("sections"),
                "wizard": p.get("wizard"), "name": p.get("name"),
                "snapshots": snaps.push_snapshot(p, label=f"AI: {(action or {}).get('action') or 'محادثة'}", origin="ai_chat") if action else (p.get("snapshots") or []),
                "updated_at": _iso_now(),
            }}
        )
        updated = await database.website_projects.find_one({"id": project_id}, {"_id": 0})
        return {"project": updated, "action": action, "response": display}

    # ---------------- Legacy /chat — keep for back-compat ----------------
    @r.post("/projects/{project_id}/chat")
    async def _p_chat(project_id: str, body: ChatMessageIn, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        history = list(p.get("chat", []))
        history.append({"role": "user", "content": body.message})
        ai_text = await chat_with_consultant(history, wizard=p.get("wizard"),
                                             project_summary={"name": p.get("name"), "template": p.get("template"), "business_type": p.get("business_type")})
        display = clean_display_text(ai_text)
        action = extract_wizard_action(ai_text)
        payload = extract_build_payload(ai_text)
        history.append({"role": "assistant", "content": display})
        update: Dict[str, Any] = {"chat": history, "updated_at": _iso_now()}
        built = False
        if payload:
            try:
                sections, theme, tpl_id = build_sections_from_payload(payload)
                for s in sections:
                    if not s.get("id"):
                        s["id"] = f"sec-{uuid.uuid4().hex[:8]}"
                update["sections"] = sections
                update["theme"] = theme
                update["template"] = tpl_id
                update["business_type"] = payload.get("business_type", p.get("business_type", "company"))
                if payload.get("name"):
                    update["name"] = payload["name"]
                built = True
            except Exception:
                pass
        if action:
            p["chat"] = history
            p = _apply_ai_action(p, action)
            update["theme"] = p.get("theme")
            update["sections"] = p.get("sections")
            update["wizard"] = p.get("wizard")
            update["name"] = p.get("name")
        await database.website_projects.update_one({"id": project_id}, {"$set": update})
        updated = await database.website_projects.find_one({"id": project_id}, {"_id": 0})
        return {"response": display, "built": built, "project": updated, "action": action}

    @r.post("/ai/instant-build")
    async def _p_instant(body: AIGenerateIn, current_user: dict = Depends(auth_dep)):
        valid = ("store", "restaurant", "company", "portfolio", "saas")
        tpl_key = body.business_type if body.business_type in valid else "blank"
        tpl = get_template(tpl_key)
        now = _iso_now()
        d = {
            "id": str(uuid.uuid4()), "user_id": current_user["user_id"],
            "name": body.name or tpl["name"], "business_type": body.business_type, "template": tpl_key,
            "lang": "ar", "direction": "rtl", "theme": tpl["theme"],
            "sections": [{**s, "id": f"sec-{uuid.uuid4().hex[:8]}"} for s in tpl["sections"]],
            "meta": {"title": body.name or tpl["name"], "description": body.brief},
            "chat": [
                {"role": "user", "content": body.brief},
                {"role": "assistant", "content": f"تم إنشاء موقعك بقالب {tpl['name']}. عدّل أي قسم من المحرر المرئي."},
            ],
            "wizard": default_wizard_state(),
            "created_at": now, "updated_at": now,
        }
        await database.website_projects.insert_one(d)
        d.pop("_id", None)
        return d

    # ---------------- Independence placeholder (returns guide only, no code) ----------------
    @r.post("/projects/{project_id}/approve")
    async def _p_approve(project_id: str, current_user: dict = Depends(auth_dep)):
        from datetime import datetime, timezone
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        now = datetime.now(timezone.utc).isoformat()
        # Generate slug if not already set
        slug = p.get("slug")
        if not slug:
            slug = await _generate_unique_slug(database, p.get("name") or "site")
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {"status": "approved", "approved_at": now, "updated_at": now, "slug": slug}}
        )
        return {"ok": True, "status": "approved", "approved_at": now, "slug": slug, "public_url": f"/sites/{slug}"}

    @r.post("/projects/{project_id}/unapprove")
    async def _p_unapprove(project_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {"status": "draft", "updated_at": _iso_now()}}
        )
        return {"ok": True, "status": "draft"}

    @r.post("/projects/{project_id}/independence/request")
    async def _independence(project_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        return {
            "ok": True,
            "message": "طلب الاستقلالية مسجّل. سيتم التواصل لاستكمال خطوات النشر.",
            "status": "pending_payment",
            "guides": [
                {"id": "vercel", "name": "Vercel", "summary": "الأفضل للمواقع الحديثة — مجاني، نطاق مخصّص، CI/CD تلقائي."},
                {"id": "netlify", "name": "Netlify", "summary": "بديل ممتاز لـ Vercel — نفس السهولة."},
                {"id": "github", "name": "GitHub Pages", "summary": "مجاني تماماً للمواقع الثابتة (بدون Backend)."},
            ],
        }

    # ---------------- Public site by slug ----------------
    @r.get("/public/{slug}", response_class=HTMLResponse)
    async def _public_site(slug: str):
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0})
        if not p:
            return HTMLResponse("<h1>الموقع غير موجود</h1>", status_code=404)
        # increment visits
        try:
            await database.website_projects.update_one({"id": p["id"]}, {"$inc": {"visits": 1}})
        except Exception:
            pass
        return HTMLResponse(render_website_to_html(p))

    @r.get("/public/{slug}/info")
    async def _public_site_info(slug: str):
        """Public metadata only (no PII)."""
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"},
                                                    {"_id": 0, "name": 1, "template": 1, "slug": 1, "approved_at": 1, "visits": 1})
        if not p:
            raise HTTPException(404, "not found")
        return p

    # ---------------- Admin: all approved sites (owner view) ----------------
    @r.get("/admin/sites")
    async def _admin_sites(current_user: dict = Depends(auth_dep)):
        # Only owner/admin can see ALL users' approved sites
        user_doc = await database.users.find_one({"id": current_user["user_id"]}, {"_id": 0, "role": 1, "email": 1})
        role = (user_doc or {}).get("role", "client")
        if role not in ("owner", "super_admin", "admin"):
            raise HTTPException(403, "غير مسموح — لوحة المشرف فقط")
        # Auto-fix: ensure every approved project has a slug
        missing = await database.website_projects.find({"status": "approved", "slug": {"$in": [None, ""]}}, {"_id": 0}).to_list(500)
        for m in missing:
            new_slug = await _generate_unique_slug(database, m.get("name") or "site")
            await database.website_projects.update_one({"id": m["id"]}, {"$set": {"slug": new_slug}})
        items = await database.website_projects.find(
            {"status": "approved"},
            {"_id": 0, "id": 1, "name": 1, "template": 1, "slug": 1, "approved_at": 1, "visits": 1, "user_id": 1, "theme": 1}
        ).sort("approved_at", -1).to_list(500)
        # Attach user email
        user_ids = list({it["user_id"] for it in items})
        users = await database.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "email": 1, "name": 1}).to_list(500)
        umap = {u["id"]: u for u in users}
        for it in items:
            u = umap.get(it["user_id"], {})
            it["owner_email"] = u.get("email")
            it["owner_name"] = u.get("name")
            it["public_url"] = f"/sites/{it.get('slug','')}"
        return {"sites": items, "total": len(items)}

    @r.get("/admin/sites/{project_id}")
    async def _admin_site_detail(project_id: str, current_user: dict = Depends(auth_dep)):
        user_doc = await database.users.find_one({"id": current_user["user_id"]}, {"_id": 0, "role": 1})
        if (user_doc or {}).get("role") not in ("owner", "super_admin", "admin"):
            raise HTTPException(403, "غير مسموح")
        p = await database.website_projects.find_one({"id": project_id}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Project not found")
        return p

    # ═══════════════════════════════════════════════════════════════
    # 🆕 SHARE LINK — owner shares preview with end-client (no auth)
    # ═══════════════════════════════════════════════════════════════
    class ShareFeedbackIn(BaseModel):
        feedback: str
        rating: Optional[int] = None
        email: Optional[str] = ""

    class ContactMessageIn(BaseModel):
        name: str
        phone: Optional[str] = ""
        email: Optional[str] = ""
        message: str

    @r.post("/projects/{project_id}/share")
    async def _share_create(project_id: str, current_user: dict = Depends(auth_dep)):
        from datetime import timedelta
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        token = _rand_token(20)
        expires = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {"share_token": token, "share_token_expires_at": expires, "updated_at": _iso_now()}},
        )
        return {"ok": True, "token": token, "url": f"/preview-share/{token}", "expires_at": expires}

    @r.get("/share/{token}/info")
    async def _share_info(token: str):
        p = await database.website_projects.find_one({"share_token": token}, {"_id": 0, "name": 1, "slug": 1, "share_token_expires_at": 1, "id": 1, "approved_at": 1})
        if not p:
            raise HTTPException(404, "Share link not found")
        exp = p.get("share_token_expires_at")
        if exp and exp < _iso_now():
            raise HTTPException(410, "Share link expired")
        return p

    @r.get("/share/{token}", response_class=HTMLResponse)
    async def _share_view(token: str):
        p = await database.website_projects.find_one({"share_token": token}, {"_id": 0})
        if not p:
            return HTMLResponse("<h1>الرابط غير صالح أو انتهت صلاحيته</h1>", status_code=404)
        exp = p.get("share_token_expires_at")
        if exp and exp < _iso_now():
            return HTMLResponse("<h1>انتهت صلاحية الرابط</h1>", status_code=410)
        html = render_website_to_html(p)
        import html as _html_lib
        safe_name = _html_lib.escape(p.get('name', '') or '')
        # Inject a lightweight "review bar" at the top so the client can give feedback
        bar = f"""<div id='zx-review-bar' style='position:fixed;top:0;left:0;right:0;z-index:9999;padding:10px 16px;background:linear-gradient(90deg,#1e293b,#0f172a);color:#fff;font-family:Tajawal,sans-serif;font-size:13px;box-shadow:0 4px 20px rgba(0,0,0,.5);border-bottom:2px solid #eab308;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>
<span>🔍 <b>معاينة خاصة لمراجعتك</b> — {safe_name} · اعط ملاحظاتك لأصحاب المشروع</span>
<span><button onclick=\"document.getElementById('zx-fb').style.display='flex'\" style='background:#eab308;color:#0f172a;border:0;padding:6px 14px;border-radius:20px;font-weight:900;cursor:pointer;font-size:12px'>✍️ اكتب ملاحظاتي</button></span></div>
<div id='zx-fb' style='display:none;position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:9999;background:#0f172a;color:#fff;padding:18px;border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.6);width:min(92vw,480px);font-family:Tajawal,sans-serif;border:1px solid #eab308'>
<div style='font-weight:900;margin-bottom:8px'>📝 ملاحظاتك على التصميم</div>
<textarea id='zx-fb-text' style='width:100%;min-height:100px;background:#1e293b;color:#fff;border:1px solid rgba(255,255,255,.2);border-radius:8px;padding:10px;font-family:inherit;font-size:13px;box-sizing:border-box' placeholder='اكتب تعليقك هنا...'></textarea>
<input id='zx-fb-email' style='width:100%;background:#1e293b;color:#fff;border:1px solid rgba(255,255,255,.2);border-radius:8px;padding:8px 10px;font-family:inherit;font-size:12px;box-sizing:border-box;margin-top:8px' placeholder='بريدك (اختياري)'/>
<div style='display:flex;gap:8px;margin-top:10px'>
<button onclick=\"document.getElementById('zx-fb').style.display='none'\" style='flex:1;background:rgba(255,255,255,.1);color:#fff;border:0;padding:8px;border-radius:8px;cursor:pointer;font-weight:700'>إلغاء</button>
<button id='zx-fb-send' style='flex:2;background:#eab308;color:#0f172a;border:0;padding:8px;border-radius:8px;cursor:pointer;font-weight:900'>إرسال</button></div></div>
<script>document.getElementById('zx-fb-send').addEventListener('click',async function(){{var t=document.getElementById('zx-fb-text').value.trim();if(!t)return;var e=document.getElementById('zx-fb-email').value.trim();this.disabled=true;this.textContent='جاري الإرسال...';try{{await fetch('/api/websites/share/{token}/feedback',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{feedback:t,email:e}})}});this.textContent='✅ تم — شكراً لك';setTimeout(()=>document.getElementById('zx-fb').style.display='none',1400);}}catch(e){{this.textContent='❌ فشل';this.disabled=false;}}}});</script>"""
        html = html.replace("<body>", "<body style='padding-top:44px'>" + bar, 1)
        return HTMLResponse(html)

    @r.post("/share/{token}/feedback")
    async def _share_feedback(token: str, body: ShareFeedbackIn):
        p = await database.website_projects.find_one({"share_token": token}, {"_id": 0, "id": 1})
        if not p:
            raise HTTPException(404, "invalid token")
        entry = {"id": str(uuid.uuid4()), "at": _iso_now(),
                 "feedback": body.feedback[:2000], "email": (body.email or "")[:200],
                 "rating": body.rating}
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"feedback": entry}, "$set": {"updated_at": _iso_now()}}
        )
        return {"ok": True}

    # Public contact form — stores a lead on the project
    @r.post("/public/{slug}/contact")
    async def _public_contact(slug: str, body: ContactMessageIn):
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0, "id": 1})
        if not p:
            raise HTTPException(404, "not found")
        msg = {"id": str(uuid.uuid4()), "at": _iso_now(),
               "name": body.name[:100], "phone": (body.phone or "")[:50],
               "email": (body.email or "")[:200], "message": body.message[:4000],
               "read": False}
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$push": {"messages": msg}, "$set": {"updated_at": _iso_now()}}
        )
        return {"ok": True}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 CLIENT ACCESS — delivers the site to the end-client with their own panel
    # ═══════════════════════════════════════════════════════════════
    class ClientLoginIn(BaseModel):
        slug: str
        password: str

    class ClientPasswordChangeIn(BaseModel):
        old_password: str
        new_password: str

    class SectionPatchIn(BaseModel):
        data: Optional[Dict[str, Any]] = None
        visible: Optional[bool] = None
        order: Optional[int] = None

    async def _resolve_client_project(token: str) -> Dict[str, Any]:
        if not token or not token.startswith("ClientToken "):
            raise HTTPException(401, "غير مصرح")
        tok = token.replace("ClientToken ", "", 1).strip()
        p = await database.website_projects.find_one({"client_access.session_token": tok}, {"_id": 0})
        if not p:
            raise HTTPException(401, "انتهت الجلسة — سجّل دخول مرة أخرى")
        return p

    def _client_safe(p: Dict[str, Any]) -> Dict[str, Any]:
        """Strip internal fields before returning to client."""
        out = dict(p)
        ca = dict(out.get("client_access") or {})
        ca.pop("password_hash", None)
        ca.pop("session_token", None)
        out["client_access"] = ca
        out.pop("user_id", None)
        return out

    from fastapi import Header as _Header

    @r.get("/client/session")
    async def _client_session(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        return _client_safe(p)

    @r.post("/projects/{project_id}/client-access")
    async def _client_access_create(project_id: str, current_user: dict = Depends(auth_dep)):
        """Enable client login for this project (resets the password)."""
        import secrets, string
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        alphabet = string.ascii_letters + string.digits
        temp_pwd = ''.join(secrets.choice(alphabet) for _ in range(8))
        hashed = _hash_pwd(temp_pwd)
        slug = p.get("slug")
        if not slug:
            slug = await _generate_unique_slug(database, p.get("name") or "site")
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": {
                "client_access": {"enabled": True, "password_hash": hashed, "created_at": _iso_now()},
                "slug": slug,
                "updated_at": _iso_now(),
            }},
        )
        return {"ok": True, "slug": slug, "temp_password": temp_pwd, "login_url": f"/client/{slug}"}

    @r.post("/client/login")
    async def _client_login(body: ClientLoginIn):
        p = await database.website_projects.find_one({"slug": body.slug}, {"_id": 0})
        if not p or not (p.get("client_access") or {}).get("enabled"):
            raise HTTPException(401, "بيانات دخول غير صحيحة")
        if not _check_pwd(body.password, (p.get("client_access") or {}).get("password_hash", "")):
            raise HTTPException(401, "كلمة المرور غير صحيحة")
        token = _rand_token(24)
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$set": {"client_access.session_token": token, "client_access.last_login": _iso_now()}},
        )
        return {"ok": True, "token": token, "slug": p.get("slug"), "name": p.get("name"),
                "vertical": p.get("vertical")}

    @r.patch("/client/sections/{section_id}")
    async def _client_patch_section(section_id: str, body: SectionPatchIn, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        sections = list(p.get("sections") or [])
        found = False
        for i, s in enumerate(sections):
            if s.get("id") == section_id:
                if body.data is not None:
                    s = {**s, "data": {**(s.get("data") or {}), **body.data}}
                if body.visible is not None:
                    s = {**s, "visible": body.visible}
                if body.order is not None:
                    s = {**s, "order": int(body.order)}
                sections[i] = s
                found = True
                break
        if not found:
            raise HTTPException(404, "Section not found")
        # Re-sort by order then rewrite consecutive order
        sections.sort(key=lambda s: s.get("order", 0))
        sections = [{**s, "order": i} for i, s in enumerate(sections)]
        # 📸 Snapshot before persisting (so client can revert)
        new_snaps = snaps.push_snapshot(p, label="تعديل قسم من لوحة العميل", origin="auto")
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"sections": sections, "snapshots": new_snaps, "updated_at": _iso_now()}}
        )
        return {"ok": True}

    # ═══════════════════════════════════════════════════════════════
    # 📚 SECTION VARIANTS CATALOG + 🕰️ SNAPSHOTS (Version History)
    # ═══════════════════════════════════════════════════════════════
    @r.get("/section-variants/catalog")
    async def _section_variants_catalog():
        """Public: full catalog of visual styles for each section type."""
        return {"catalog": sv.catalog_public()}

    @r.get("/client/snapshots")
    async def _client_list_snapshots(authorization: str = _Header(None)):
        """List ALL snapshots (version history) for the authenticated client's project."""
        p = await _resolve_client_project(authorization or "")
        return {"snapshots": snaps.list_snapshots_summary(p), "total": len(p.get("snapshots") or [])}

    class SnapshotCreateIn(BaseModel):
        label: Optional[str] = "نسخة يدوية"

    @r.post("/client/snapshots")
    async def _client_create_snapshot(body: SnapshotCreateIn, authorization: str = _Header(None)):
        """Manually save a named snapshot of the current state."""
        p = await _resolve_client_project(authorization or "")
        new_snaps = snaps.push_snapshot(p, label=(body.label or "نسخة يدوية").strip()[:60], origin="manual")
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"snapshots": new_snaps, "updated_at": _iso_now()}}
        )
        return {"ok": True, "total": len(new_snaps)}

    @r.post("/client/snapshots/{snapshot_id}/restore")
    async def _client_restore_snapshot(snapshot_id: str, authorization: str = _Header(None)):
        """Restore the project to a previous snapshot's state."""
        p = await _resolve_client_project(authorization or "")
        update = snaps.apply_snapshot(p, snapshot_id)
        if not update:
            raise HTTPException(404, "النسخة غير موجودة")
        await database.website_projects.update_one({"id": p["id"]}, {"$set": update})
        return {"ok": True, "restored_id": snapshot_id}

    @r.delete("/client/snapshots/{snapshot_id}")
    async def _client_delete_snapshot(snapshot_id: str, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        snaps_list = [s for s in (p.get("snapshots") or []) if s.get("id") != snapshot_id]
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"snapshots": snaps_list, "updated_at": _iso_now()}}
        )
        return {"ok": True}

    @r.get("/client/snapshots/{snapshot_id}/preview-html")
    async def _client_snapshot_preview(snapshot_id: str, authorization: str = _Header(None)):
        """Render the snapshot to HTML for thumbnail preview (iframe)."""
        p = await _resolve_client_project(authorization or "")
        snap = snaps.find_snapshot(p, snapshot_id)
        if not snap:
            raise HTTPException(404, "النسخة غير موجودة")
        payload = snap.get("payload") or {}
        # Merge snapshot payload onto the project (for render context)
        virtual = {**p, **{k: v for k, v in payload.items() if v is not None}}
        html = render_website_to_html(virtual)
        return {"html": html, "label": snap.get("label"), "created_at": snap.get("created_at")}

    @r.post("/client/change-password")
    async def _client_change_password(body: ClientPasswordChangeIn, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        if not _check_pwd(body.old_password, (p.get("client_access") or {}).get("password_hash", "")):
            raise HTTPException(401, "كلمة المرور الحالية غير صحيحة")
        if len(body.new_password) < 6:
            raise HTTPException(400, "كلمة المرور الجديدة قصيرة (6 أحرف على الأقل)")
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$set": {"client_access.password_hash": _hash_pwd(body.new_password),
                      "client_access.password_changed_at": _iso_now()}},
        )
        return {"ok": True}

    @r.get("/client/messages")
    async def _client_messages(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        return {"messages": list(reversed(p.get("messages") or [])), "total": len(p.get("messages") or [])}

    @r.post("/client/messages/{message_id}/read")
    async def _client_mark_read(message_id: str, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"], "messages.id": message_id}, {"$set": {"messages.$.read": True}}
        )
        return {"ok": True}

    @r.get("/client/analytics")
    async def _client_analytics(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        return {
            "visits": int(p.get("visits") or 0),
            "messages_total": len(p.get("messages") or []),
            "messages_unread": sum(1 for m in (p.get("messages") or []) if not m.get("read")),
            "approved_at": p.get("approved_at"),
            "sections_count": len(p.get("sections") or []),
            "name": p.get("name"),
            "slug": p.get("slug"),
        }

    @r.post("/client/logout")
    async def _client_logout(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$unset": {"client_access.session_token": ""}}
        )
        return {"ok": True}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 DELIVERY KIT — everything the owner needs to hand over
    # ═══════════════════════════════════════════════════════════════
    @r.get("/projects/{project_id}/delivery-kit")
    async def _delivery_kit(project_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        slug = p.get("slug")
        return {
            "project_id": project_id,
            "name": p.get("name"),
            "slug": slug,
            "approved": p.get("status") == "approved",
            "approved_at": p.get("approved_at"),
            "public_url": f"/sites/{slug}" if slug else None,
            "share_url": (f"/preview-share/{p['share_token']}" if p.get("share_token") else None),
            "client_login_url": f"/client/{slug}" if slug and (p.get("client_access") or {}).get("enabled") else None,
            "client_access_enabled": bool((p.get("client_access") or {}).get("enabled")),
            "messages_count": len(p.get("messages") or []),
            "feedback_count": len(p.get("feedback") or []),
            "visits": int(p.get("visits") or 0),
        }

    @r.post("/projects/{project_id}/propose-designs")
    async def _propose_designs(project_id: str, current_user: dict = Depends(auth_dep)):
        """Return 4 curated, distinctive design proposals — shown in chat for the user to pick before applying.
        Each proposal mixes a layout variant with a mood/palette to feel genuinely different.
        """
        from .variants import STYLE_VARIANTS
        from .catalog import list_layouts
        from .templates import TEMPLATES
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        template_id = p.get("template") or "blank"
        layouts = list_layouts(template_id) or []

        chosen_moods = ["luxury", "modern", "warm", "playful"]
        proposals = []
        for i, mood_id in enumerate(chosen_moods):
            mood = next((v for v in STYLE_VARIANTS if v["id"] == mood_id), STYLE_VARIANTS[0])
            layout = layouts[i % max(1, len(layouts))] if layouts else None
            base_template = TEMPLATES.get(template_id) or TEMPLATES.get("blank") or {}
            theme = {**(base_template.get("theme") or {}), **mood["theme_override"]}
            if layout and layout.get("theme_hints"):
                theme = {**theme, **layout["theme_hints"]}
            proposals.append({
                "id": f"{mood_id}-{i}",
                "name": mood["name"],
                "mood_id": mood_id,
                "layout_id": layout.get("id") if layout else None,
                "layout_name": layout.get("name") if layout else None,
                "palette": {"primary": theme.get("primary"), "accent": theme.get("accent"), "secondary": theme.get("secondary"), "background": theme.get("background", "#0b0f1f")},
                "font": theme.get("font"),
                "tagline": layout.get("tagline") if layout else mood["name"],
            })
        return {"ok": True, "proposals": proposals, "template": template_id}

    @r.post("/projects/{project_id}/apply-proposal")
    async def _apply_proposal(project_id: str, body: dict, current_user: dict = Depends(auth_dep)):
        """Apply a chosen proposal — merges mood theme + layout onto the project, preserving user content."""
        from .variants import STYLE_VARIANTS
        from .catalog import get_layout, list_layouts
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        mood_id = body.get("mood_id")
        layout_id = body.get("layout_id")
        template_id = p.get("template") or "blank"
        mood = next((v for v in STYLE_VARIANTS if v["id"] == mood_id), None)
        if not mood:
            raise HTTPException(400, "invalid mood")
        theme = dict(p.get("theme") or {})
        theme.update(mood["theme_override"])
        updates = {"theme": theme, "updated_at": _iso_now()}
        has_layouts = bool(list_layouts(template_id))
        if layout_id and has_layouts:
            try:
                lay = get_layout(template_id, layout_id)
                updates["sections"] = [{**s, "id": s.get("id") or f"sec-{uuid.uuid4().hex[:8]}", "order": i} for i, s in enumerate(lay.get("sections") or [])]
                lay_theme = lay.get("theme") or {}
                theme.update(lay_theme)
                theme.update(mood["theme_override"])
                updates["theme"] = theme
            except Exception:
                pass
        await database.website_projects.update_one({"id": project_id}, {"$set": updates})
        return {"ok": True}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 SUPPORT TICKETS — client can request maintenance (points-based)
    # ═══════════════════════════════════════════════════════════════
    class SupportTicketIn(BaseModel):
        subject: str
        description: str
        category: Optional[str] = "general"  # general | bug | content | design | other

    @r.post("/client/support-tickets")
    async def _client_support_create(body: SupportTicketIn, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        ticket = {
            "id": str(uuid.uuid4()), "at": _iso_now(),
            "subject": body.subject[:200], "description": body.description[:4000],
            "category": body.category or "general",
            "status": "open",
        }
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$push": {"support_tickets": ticket}, "$set": {"updated_at": _iso_now()}}
        )
        return {"ok": True, "ticket": ticket}

    @r.get("/client/support-tickets")
    async def _client_support_list(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        tickets = list(reversed(p.get("support_tickets") or []))
        return {"tickets": tickets, "total": len(tickets)}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 QUALITY CHECKS — automated site health checks after creation
    # ═══════════════════════════════════════════════════════════════
    @r.get("/projects/{project_id}/quality-checks")
    async def _quality_checks(project_id: str, current_user: dict = Depends(auth_dep)):
        """Run automated quality checks on the project and report issues."""
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "Project not found")
        checks = []
        sections = p.get("sections") or []
        theme = p.get("theme") or {}

        # 1) Has hero
        has_hero = any(s.get("type") == "hero" for s in sections)
        checks.append({"id": "hero", "label": "قسم رئيسي (Hero)", "pass": has_hero,
                       "msg": "موجود ✓" if has_hero else "⚠️ لا يوجد قسم رئيسي — يُنصح بإضافة Hero"})
        # 2) Has contact/footer
        has_footer = any(s.get("type") == "footer" for s in sections)
        checks.append({"id": "footer", "label": "تذييل الصفحة", "pass": has_footer,
                       "msg": "موجود ✓" if has_footer else "⚠️ لا يوجد فوتر"})
        # 3) Has contact info
        has_contact = any(s.get("type") in ("contact", "footer") for s in sections)
        checks.append({"id": "contact", "label": "معلومات التواصل", "pass": has_contact,
                       "msg": "متوفرة ✓" if has_contact else "⚠️ أضف قسم تواصل"})
        # 4) Has logo or brand
        has_brand = bool(theme.get("logo_url") or p.get("name"))
        checks.append({"id": "brand", "label": "الهوية البصرية (لوقو/اسم)", "pass": has_brand,
                       "msg": "مضبوطة ✓" if has_brand else "⚠️ أضف لوقو أو اسم نشاط"})
        # 5) Sections count
        sections_count = len([s for s in sections if s.get("visible", True)])
        checks.append({"id": "sections_depth", "label": "عمق المحتوى", "pass": sections_count >= 4,
                       "msg": f"{sections_count} أقسام ظاهرة" + (" ✓" if sections_count >= 4 else " — يُنصح بـ 4 أو أكثر")})
        # 6) Has payment methods (for stores)
        if theme.get("payment_methods"):
            checks.append({"id": "payment", "label": "طرق الدفع", "pass": True, "msg": f"{len(theme['payment_methods'])} طريقة ✓"})
        # 7) Features
        has_features = bool(theme.get("extras"))
        checks.append({"id": "features", "label": "ميزات تفاعلية (واتساب/سلة/حجز)", "pass": has_features,
                       "msg": f"{len(theme.get('extras') or [])} ميزة" + (" ✓" if has_features else " — لم يُفعَّل")})
        # 8) Approved?
        approved = p.get("status") == "approved"
        checks.append({"id": "approved", "label": "معتمد ومنشور", "pass": approved,
                       "msg": "نعم — منشور على /sites/" + (p.get("slug") or "") if approved else "⚠️ غير معتمد — المشروع لا يزال مسودة"})
        # 9) Client access
        has_client = bool((p.get("client_access") or {}).get("enabled"))
        checks.append({"id": "client_access", "label": "لوحة تحكم العميل", "pass": has_client,
                       "msg": "مفعّلة ✓" if has_client else "— لم تُفعّل بعد"})

        score = int(100 * sum(1 for c in checks if c["pass"]) / max(1, len(checks)))
        return {"score": score, "checks": checks,
                "passed": sum(1 for c in checks if c["pass"]),
                "total": len(checks)}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 SITE CUSTOMERS + ORDERS + DRIVERS — full commerce stack per site
    # ═══════════════════════════════════════════════════════════════
    class SiteRegisterIn(BaseModel):
        name: str
        phone: str
        password: str
        email: Optional[str] = ""

    class SiteLoginIn(BaseModel):
        phone: str
        password: str

    class OrderItem(BaseModel):
        name: str
        price: float
        qty: int = 1
        note: Optional[str] = ""

    class OrderCreateIn(BaseModel):
        items: List[OrderItem]
        address: Optional[str] = ""
        lat: Optional[float] = None
        lng: Optional[float] = None
        note: Optional[str] = ""
        delivery_fee: Optional[float] = 0
        coupon_code: Optional[str] = ""
        redeem_points: Optional[int] = 0
        payment_method: Optional[str] = "cod"
        # 🆕 Shipping fields
        city: Optional[str] = ""
        country: Optional[str] = ""
        shipping_provider: Optional[str] = ""        # e.g. "smsa", "aramex", "local_delivery"
        shipping_provider_name: Optional[str] = ""    # display name in Arabic
        shipping_fee: Optional[float] = None          # client-quoted fee (re-validated server-side)
        shipping_eta: Optional[str] = ""
        # 🆕 Optional shipping insurance (computed server-side from cart_subtotal)
        insurance_opted: Optional[bool] = False

    class DriverCreateIn(BaseModel):
        name: str
        phone: str
        password: str
        vehicle: Optional[str] = ""
        zone: Optional[str] = ""

    class OrderStatusIn(BaseModel):
        status: str  # pending|accepted|preparing|ready|on_the_way|delivered|cancelled
        driver_id: Optional[str] = None
        tracking_number: Optional[str] = None  # 🆕 owner sets this when handing off to courier

    # ---- customer auth (per-site) ----
    async def _resolve_site_customer(slug: str, token: str) -> Dict[str, Any]:
        if not token or not token.startswith("SiteToken "):
            raise HTTPException(401, "غير مصرح")
        tok = token.replace("SiteToken ", "", 1).strip()
        p = await database.website_projects.find_one(
            {"slug": slug, "site_customers.session_token": tok}, {"_id": 0}
        )
        if not p:
            raise HTTPException(401, "انتهت الجلسة")
        cust = next((c for c in (p.get("site_customers") or []) if c.get("session_token") == tok), None)
        if not cust:
            raise HTTPException(401, "جلسة غير صحيحة")
        return {"project": p, "customer": cust}

    def _cust_safe(c: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in c.items() if k not in ("password_hash", "session_token")}

    @r.post("/public/{slug}/auth/register")
    async def _site_register(slug: str, body: SiteRegisterIn):
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0, "id": 1, "site_customers": 1, "loyalty_settings": 1})
        if not p:
            raise HTTPException(404, "الموقع غير متاح")
        if any(c.get("phone") == body.phone for c in (p.get("site_customers") or [])):
            raise HTTPException(400, "رقم الجوال مسجّل مسبقاً — سجّل دخولك بدلاً من ذلك")
        cid = str(uuid.uuid4())
        token = _rand_token(18)
        loyalty = p.get("loyalty_settings") or {"welcome_bonus": 50, "enabled": True}
        welcome_pts = int(loyalty.get("welcome_bonus", 50)) if loyalty.get("enabled", True) else 0
        cust = {
            "id": cid, "name": body.name[:100], "phone": body.phone[:30],
            "email": (body.email or "")[:200],
            "password_hash": _hash_pwd(body.password),
            "session_token": token, "created_at": _iso_now(),
            "points": welcome_pts,
        }
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$push": {"site_customers": cust}, "$set": {"updated_at": _iso_now()}}
        )
        return {"ok": True, "token": token, "customer": _cust_safe(cust), "welcome_points": welcome_pts}

    @r.post("/public/{slug}/auth/login")
    async def _site_login(slug: str, body: SiteLoginIn):
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0, "id": 1, "site_customers": 1})
        if not p:
            raise HTTPException(404, "الموقع غير متاح")
        cust = next((c for c in (p.get("site_customers") or []) if c.get("phone") == body.phone), None)
        if not cust or not _check_pwd(body.password, cust.get("password_hash", "")):
            raise HTTPException(401, "بيانات دخول غير صحيحة")
        token = _rand_token(18)
        await database.website_projects.update_one(
            {"id": p["id"], "site_customers.id": cust["id"]},
            {"$set": {"site_customers.$.session_token": token, "site_customers.$.last_login": _iso_now()}}
        )
        return {"ok": True, "token": token, "customer": _cust_safe({**cust, "session_token": token})}

    @r.get("/public/{slug}/auth/me")
    async def _site_me(slug: str, authorization: str = _Header(None)):
        data = await _resolve_site_customer(slug, authorization or "")
        return _cust_safe(data["customer"])

    # ---- 🆕 PUBLIC shipping quote (by slug) — used at storefront checkout ----
    @r.post("/public/{slug}/shipping/quote")
    async def _public_shipping_quote(slug: str, body: Dict[str, Any], request: Request):
        """
        Public — at storefront checkout, returns available shipping options with prices/ETAs.
        Body: { country?: "SA", city?: "جدة", weight_kg?: 1.5, cart_subtotal?: 240 }
        Auto-detects country/city from IP if not provided.
        """
        p = await database.website_projects.find_one(
            {"slug": slug, "status": "approved"},
            {"_id": 0, "id": 1, "shipping_settings": 1, "delivery_settings": 1},
        )
        if not p:
            raise HTTPException(404, "الموقع غير متاح")
        from .shipping import calculate_shipping_quote, detect_country_from_ip

        country = (body.get("country") or "").strip().upper()
        city = (body.get("city") or "").strip()
        weight = float(body.get("weight_kg") or 1.0)
        subtotal = float(body.get("cart_subtotal") or 0)

        if not country:
            client_ip = (request.client.host if request.client else "") or ""
            try:
                xff = request.headers.get("x-forwarded-for")
                if xff:
                    client_ip = xff.split(",")[0].strip()
            except Exception:
                pass
            detected_country, detected_city = detect_country_from_ip(client_ip)
            country = detected_country
            if not city:
                city = detected_city or ""

        cfg = p.get("shipping_settings") or {
            "enabled_providers": ["smsa", "aramex", "saudi_post"],
            "store_city": "جدة",
            "local_delivery_enabled": True,
            "local_delivery_fee": 15,
            "local_delivery_eta_hours": "2-4",
            "free_shipping_above_sar": 200,
        }
        options = calculate_shipping_quote(
            project_settings=cfg,
            customer_country=country,
            customer_city=city,
            weight_kg=weight,
            cart_subtotal=subtotal,
        )
        return {
            "country": country,
            "city": city,
            "weight_kg": weight,
            "options": options,
            "store_city": cfg.get("store_city") or "",
            "cod_markup_enabled": bool(cfg.get("cod_markup_enabled")),
            "cod_markup_sar": float(cfg.get("cod_markup_sar") or 0),
            "insurance_enabled": bool(cfg.get("insurance_enabled")),
            "insurance_percent": float(cfg.get("insurance_percent") or 2.0),
            "insurance_min_sar": float(cfg.get("insurance_min_sar") or 10.0),
        }

    # ---- orders (customer-side) ----
    @r.post("/public/{slug}/orders")
    async def _order_create(slug: str, body: OrderCreateIn, authorization: str = _Header(None)):
        data = await _resolve_site_customer(slug, authorization or "")
        subtotal = sum((i.price or 0) * (i.qty or 1) for i in body.items)
        # 🆕 Shipping fee resolution:
        # If a shipping_provider was selected at checkout, re-quote server-side and trust the cheapest match
        # Otherwise, fall back to legacy haversine local delivery logic
        shipping_provider = (body.shipping_provider or "").strip()
        shipping_provider_name = (body.shipping_provider_name or "").strip()
        shipping_eta = (body.shipping_eta or "").strip()
        shipping_fee = 0.0
        cod_markup_applied = 0.0
        km = 0.0
        if shipping_provider:
            # Re-quote on server to prevent client-side fee tampering
            from .shipping import calculate_shipping_quote
            cfg = data["project"].get("shipping_settings") or {
                "enabled_providers": ["smsa", "aramex", "saudi_post"],
                "store_city": "جدة",
                "local_delivery_enabled": True,
                "local_delivery_fee": 15,
                "local_delivery_eta_hours": "2-4",
                "free_shipping_above_sar": 200,
            }
            try:
                opts = calculate_shipping_quote(
                    project_settings=cfg,
                    customer_country=(body.country or "SA"),
                    customer_city=(body.city or ""),
                    weight_kg=1.0,
                    cart_subtotal=subtotal,
                )
                match = next((o for o in opts if o["provider_id"] == shipping_provider), None)
                if match:
                    shipping_fee = float(match["fee_sar"])
                    if not shipping_provider_name:
                        shipping_provider_name = match.get("provider_name", "")
                    if not shipping_eta:
                        shipping_eta = match.get("delivery_eta", "")
                    # 🆕 COD markup: only when payment is COD AND the provider supports COD AND the toggle is on
                    pay_method = (body.payment_method or "cod").lower()
                    if (
                        pay_method == "cod"
                        and bool(cfg.get("cod_markup_enabled"))
                        and bool(match.get("supports_cod"))
                    ):
                        cod_markup_applied = max(0.0, float(cfg.get("cod_markup_sar") or 0))
                        shipping_fee += cod_markup_applied
                else:
                    # Provider not available for this location — fall back to client-quoted (clamped)
                    shipping_fee = max(0.0, float(body.shipping_fee or 0))
            except Exception:
                shipping_fee = max(0.0, float(body.shipping_fee or 0))
            fee = round(shipping_fee, 2)
        else:
            # Legacy: Auto-compute delivery fee via Haversine if site has delivery_settings
            s = (data["project"].get("delivery_settings") or {"base_fee": 10, "fee_per_km": 2, "free_delivery_above": 200})
            km = _haversine_km(s.get("base_lat"), s.get("base_lng"), body.lat, body.lng) if s.get("base_lat") else 0
            auto_fee = float(s.get("base_fee", 10)) + km * float(s.get("fee_per_km", 2))
            if s.get("free_delivery_above") and subtotal >= float(s["free_delivery_above"]):
                auto_fee = 0
            fee = float(body.delivery_fee or 0) or round(auto_fee, 2)
        # 🆕 Apply coupon
        discount = 0
        coupon_used = None
        if body.coupon_code:
            code = body.coupon_code.strip().upper()
            coupon = next((c for c in (data["project"].get("coupons") or [])
                           if c.get("code") == code and c.get("active")
                           and c.get("used", 0) < c.get("max_uses", 999)
                           and subtotal >= c.get("min_order", 0)), None)
            if coupon:
                if coupon.get("discount_percent"):
                    discount = subtotal * (coupon["discount_percent"] / 100)
                if coupon.get("discount_amount"):
                    discount = max(discount, coupon["discount_amount"])
                coupon_used = code
                await database.website_projects.update_one(
                    {"id": data["project"]["id"], "coupons.code": code},
                    {"$inc": {"coupons.$.used": 1}}
                )
        # 🆕 Redeem loyalty points
        redeemed_points = 0
        redeem_discount = 0
        if body.redeem_points and body.redeem_points > 0:
            avail = int(data["customer"].get("points") or 0)
            pts_to_use = min(int(body.redeem_points), avail)
            loyalty = data["project"].get("loyalty_settings") or {"redeem_rate": 0.1}
            redeem_discount = pts_to_use * float(loyalty.get("redeem_rate", 0.1))
            redeemed_points = pts_to_use
        # 🆕 Shipping insurance (optional, customer-opted at checkout)
        insurance_fee = 0.0
        if body.insurance_opted:
            ship_cfg = data["project"].get("shipping_settings") or {}
            if bool(ship_cfg.get("insurance_enabled")):
                pct = float(ship_cfg.get("insurance_percent") or 2.0)
                min_v = float(ship_cfg.get("insurance_min_sar") or 10.0)
                insurance_fee = max(min_v, round(subtotal * pct / 100, 2))
        total = max(0, subtotal + fee + insurance_fee - discount - redeem_discount)
        # 🆕 Earn loyalty points on order
        loyalty = data["project"].get("loyalty_settings") or {"enabled": True, "points_per_sar": 1}
        earned_points = int(total * float(loyalty.get("points_per_sar", 1))) if loyalty.get("enabled", True) else 0
        order = {
            "id": str(uuid.uuid4()),
            "at": _iso_now(),
            "customer_id": data["customer"]["id"],
            "customer_name": data["customer"]["name"],
            "customer_phone": data["customer"]["phone"],
            "items": [i.dict() for i in body.items],
            "subtotal": subtotal,
            "delivery_fee": fee,
            "distance_km": km,
            "coupon_code": coupon_used,
            "coupon_discount": round(discount, 2),
            "points_redeemed": redeemed_points,
            "points_discount": round(redeem_discount, 2),
            "points_earned": earned_points,
            "payment_method": body.payment_method or "cod",
            "total": round(total, 2),
            "address": (body.address or "")[:400],
            "lat": body.lat, "lng": body.lng,
            "note": (body.note or "")[:500],
            "status": "pending",
            "driver_id": None,
            # 🆕 Shipping metadata
            "shipping_provider": shipping_provider,
            "shipping_provider_name": shipping_provider_name,
            "shipping_eta": shipping_eta,
            "shipping_city": (body.city or "")[:80],
            "shipping_country": (body.country or "")[:8],
            "cod_markup_applied": round(cod_markup_applied, 2),
            "insurance_fee": round(insurance_fee, 2),
            "tracking_number": "",
        }
        # Update customer points balance
        new_pts = max(0, int(data["customer"].get("points") or 0) - redeemed_points + earned_points)
        await database.website_projects.update_one(
            {"id": data["project"]["id"]},
            {"$push": {"orders": order}, "$set": {"updated_at": _iso_now()}}
        )
        await database.website_projects.update_one(
            {"id": data["project"]["id"], "site_customers.id": data["customer"]["id"]},
            {"$set": {"site_customers.$.points": new_pts}}
        )
        # 🛰️ broadcast new order to client dashboard & drivers
        try:
            await realtime.broadcast_all(slug, "order_created", {
                "order_id": order["id"],
                "customer": data["customer"].get("name") or "",
                "total": order["total"],
                "status": order["status"],
                "lat": order.get("lat"), "lng": order.get("lng"),
                "at": order["created_at"],
            })
        except Exception as _re:
            logger.debug(f"ws broadcast failed: {_re}")
        return {"ok": True, "order_id": order["id"], "total": order["total"],
                "delivery_fee": fee, "distance_km": km, "discount": round(discount + redeem_discount, 2),
                "points_earned": earned_points, "points_balance": new_pts, "status": "pending"}

    @r.get("/public/{slug}/orders/my")
    async def _order_list_my(slug: str, authorization: str = _Header(None)):
        data = await _resolve_site_customer(slug, authorization or "")
        cid = data["customer"]["id"]
        # 🆕 Enrich orders with tracking_url derived from provider's tracking_url_template
        from .shipping import PROVIDER_BY_ID
        out = []
        for o in (data["project"].get("orders") or []):
            if o.get("customer_id") != cid:
                continue
            tn = (o.get("tracking_number") or "").strip()
            pid = (o.get("shipping_provider") or "").strip()
            tracking_url = ""
            if tn and pid in PROVIDER_BY_ID:
                tmpl = PROVIDER_BY_ID[pid].get("tracking_url_template") or ""
                if tmpl:
                    tracking_url = tmpl.replace("{tracking}", tn)
            o2 = {**o, "tracking_url": tracking_url}
            out.append(o2)
        return {"orders": list(reversed(out))}

    # ---- orders (owner/client dashboard) ----
    @r.get("/client/orders")
    async def _client_orders(authorization: str = _Header(None), status: Optional[str] = None):
        p = await _resolve_client_project(authorization or "")
        orders = p.get("orders") or []
        if status:
            orders = [o for o in orders if o.get("status") == status]
        return {"orders": list(reversed(orders)), "total": len(p.get("orders") or [])}

    @r.patch("/client/orders/{order_id}")
    async def _client_order_patch(order_id: str, body: OrderStatusIn, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        update = {"orders.$.status": body.status, "updated_at": _iso_now()}
        if body.driver_id is not None:
            update["orders.$.driver_id"] = body.driver_id
        if body.tracking_number is not None:
            update["orders.$.tracking_number"] = (body.tracking_number or "")[:80]
        res = await database.website_projects.update_one(
            {"id": p["id"], "orders.id": order_id}, {"$set": update}
        )
        if res.matched_count == 0:
            raise HTTPException(404, "Order not found")
        # 🆕 Build a WhatsApp link for the owner to notify the customer (1-tap)
        order = next((o for o in (p.get("orders") or []) if o.get("id") == order_id), None)
        wa = None
        if order and order.get("customer_phone"):
            # 🆕 Tracking-aware message — when a tracking_number was just saved, include the deep-link
            if body.tracking_number is not None and body.tracking_number.strip():
                from .shipping import PROVIDER_BY_ID
                pid = (order.get("shipping_provider") or "").strip()
                tn = body.tracking_number.strip()
                tracking_url = ""
                if pid in PROVIDER_BY_ID:
                    tmpl = PROVIDER_BY_ID[pid].get("tracking_url_template") or ""
                    if tmpl:
                        tracking_url = tmpl.replace("{tracking}", tn)
                lines = [
                    f"📦 طلبك رقم #{order_id[:8]} في {p.get('name','موقعنا')}",
                    f"🚚 شحنته الآن عبر {order.get('shipping_provider_name') or pid}",
                    f"رقم التتبع: {tn}",
                ]
                if tracking_url:
                    lines.append(f"تتبّع الشحنة: {tracking_url}")
                wa = _wa_link(order["customer_phone"], "\n".join(lines))
            elif body.status in _ORDER_STATUS_MSGS:
                msg = f"طلبك رقم #{order_id[:8]} في {p.get('name','موقعنا')}\n{_ORDER_STATUS_MSGS[body.status]}"
                wa = _wa_link(order["customer_phone"], msg)
        # 🛰️ broadcast status/assignment change
        try:
            await realtime.broadcast_all(p["slug"], "order_status", {
                "order_id": order_id,
                "status": body.status,
                "driver_id": body.driver_id,
            })
        except Exception as _re:
            logger.debug(f"ws broadcast failed: {_re}")
        return {"ok": True, "whatsapp_link": wa}

    # ---- drivers (client dashboard) ----
    @r.post("/client/drivers")
    async def _driver_create(body: DriverCreateIn, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        if any(d.get("phone") == body.phone for d in (p.get("drivers") or [])):
            raise HTTPException(400, "رقم الجوال مستخدم مسبقاً")
        driver = {
            "id": str(uuid.uuid4()),
            "name": body.name[:100], "phone": body.phone[:30],
            "password_hash": _hash_pwd(body.password),
            "vehicle": (body.vehicle or "")[:100],
            "zone": (body.zone or "")[:100],
            "active": True,
            "lat": None, "lng": None,
            "created_at": _iso_now(),
        }
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$push": {"drivers": driver}, "$set": {"updated_at": _iso_now()}}
        )
        # strip sensitive
        return {"ok": True, "driver": {k: v for k, v in driver.items() if k != "password_hash"}}

    @r.get("/client/drivers")
    async def _drivers_list(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        drivers = [{k: v for k, v in d.items() if k != "password_hash"} for d in (p.get("drivers") or [])]
        return {"drivers": drivers}

    @r.delete("/client/drivers/{driver_id}")
    async def _driver_delete(driver_id: str, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$pull": {"drivers": {"id": driver_id}}, "$set": {"updated_at": _iso_now()}}
        )
        return {"ok": True}

    @r.get("/client/customers")
    async def _customers_list(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        customers = [{k: v for k, v in c.items() if k not in ("password_hash", "session_token")} for c in (p.get("site_customers") or [])]
        return {"customers": list(reversed(customers)), "total": len(customers)}

    # ---- driver auth (simple) ----
    class DriverLoginIn(BaseModel):
        slug: str
        phone: str
        password: str

    @r.post("/driver/login")
    async def _driver_login(body: DriverLoginIn):
        p = await database.website_projects.find_one({"slug": body.slug}, {"_id": 0, "id": 1, "drivers": 1, "name": 1, "slug": 1})
        if not p:
            raise HTTPException(404, "الموقع غير موجود")
        drv = next((d for d in (p.get("drivers") or []) if d.get("phone") == body.phone), None)
        if not drv or not _check_pwd(body.password, drv.get("password_hash", "")):
            raise HTTPException(401, "بيانات دخول غير صحيحة")
        token = _rand_token(20)
        await database.website_projects.update_one(
            {"id": p["id"], "drivers.id": drv["id"]},
            {"$set": {"drivers.$.session_token": token, "drivers.$.last_login": _iso_now()}}
        )
        return {"ok": True, "token": token, "driver": {"id": drv["id"], "name": drv["name"]}, "site": p["name"]}

    async def _resolve_driver(slug: str, token: str) -> Dict[str, Any]:
        if not token or not token.startswith("DriverToken "):
            raise HTTPException(401, "غير مصرح")
        tok = token.replace("DriverToken ", "", 1).strip()
        p = await database.website_projects.find_one(
            {"slug": slug, "drivers.session_token": tok}, {"_id": 0}
        )
        if not p:
            raise HTTPException(401, "انتهت الجلسة")
        drv = next((d for d in (p.get("drivers") or []) if d.get("session_token") == tok), None)
        return {"project": p, "driver": drv}

    class DriverLocationIn(BaseModel):
        lat: float
        lng: float

    @r.get("/driver/{slug}/orders")
    async def _driver_orders(slug: str, authorization: str = _Header(None)):
        data = await _resolve_driver(slug, authorization or "")
        drv_id = data["driver"]["id"]
        orders = [o for o in (data["project"].get("orders") or []) if o.get("driver_id") == drv_id]
        return {"orders": list(reversed(orders))}

    @r.post("/driver/{slug}/location")
    async def _driver_update_location(slug: str, body: DriverLocationIn, authorization: str = _Header(None)):
        data = await _resolve_driver(slug, authorization or "")
        await database.website_projects.update_one(
            {"id": data["project"]["id"], "drivers.id": data["driver"]["id"]},
            {"$set": {"drivers.$.lat": body.lat, "drivers.$.lng": body.lng, "drivers.$.last_ping": _iso_now()}}
        )
        # 🛰️ broadcast live location to client dashboard
        try:
            await realtime.broadcast_to_clients(slug, "location", {
                "driver_id": data["driver"]["id"],
                "driver_name": data["driver"].get("name"),
                "lat": body.lat, "lng": body.lng,
                "at": _iso_now(),
            })
        except Exception as _re:
            logger.debug(f"ws broadcast failed: {_re}")
        return {"ok": True}

    # ═══════════════════════════════════════════════════════════════
    # 🛰️ WEBSOCKET LIVE-MAP ENDPOINTS (replaces polling)
    # ═══════════════════════════════════════════════════════════════
    async def _validate_client_token(slug: str, token: str) -> bool:
        if not token:
            return False
        p = await database.website_projects.find_one(
            {"slug": slug, "client_access.session_token": token},
            {"_id": 0, "id": 1},
        )
        return bool(p)

    async def _validate_driver_token(slug: str, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        p = await database.website_projects.find_one(
            {"slug": slug, "drivers.session_token": token},
            {"_id": 0},
        )
        if not p:
            return None
        drv = next((d for d in (p.get("drivers") or []) if d.get("session_token") == token), None)
        return {"project": p, "driver": drv} if drv else None

    @r.websocket("/ws/client/{slug}")
    async def _ws_client(ws: WebSocket, slug: str, token: str = ""):
        """Live feed for client dashboard. Auth via ?token=<ClientToken>."""
        if not await _validate_client_token(slug, token):
            await ws.close(code=4401)
            return
        await realtime.connect("client", slug, ws)
        try:
            await ws.send_json({"type": "hello", "data": {"slug": slug, "role": "client"}})
            while True:
                # We don't require incoming messages, but read to detect disconnect.
                msg = await ws.receive_text()
                if msg == "ping":
                    await ws.send_json({"type": "pong", "data": {}})
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug(f"ws client error: {e}")
        finally:
            await realtime.disconnect("client", slug, ws)

    @r.websocket("/ws/driver/{slug}")
    async def _ws_driver(ws: WebSocket, slug: str, token: str = ""):
        """Driver connection. Auth via ?token=<DriverToken>.

        Driver may send location updates via:
            {"type": "location", "lat": ..., "lng": ...}
        """
        info = await _validate_driver_token(slug, token)
        if not info:
            await ws.close(code=4401)
            return
        driver = info["driver"]
        await realtime.connect("driver", slug, ws)
        try:
            await ws.send_json({"type": "hello", "data": {
                "slug": slug, "role": "driver", "driver_id": driver["id"],
            }})
            while True:
                raw = await ws.receive_json()
                mtype = (raw or {}).get("type")
                if mtype == "location":
                    lat = raw.get("lat"); lng = raw.get("lng")
                    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                        await database.website_projects.update_one(
                            {"id": info["project"]["id"], "drivers.id": driver["id"]},
                            {"$set": {
                                "drivers.$.lat": float(lat),
                                "drivers.$.lng": float(lng),
                                "drivers.$.last_ping": _iso_now(),
                            }}
                        )
                        await realtime.broadcast_to_clients(slug, "location", {
                            "driver_id": driver["id"],
                            "driver_name": driver.get("name"),
                            "lat": float(lat), "lng": float(lng),
                            "at": _iso_now(),
                        })
                elif mtype == "ping":
                    await ws.send_json({"type": "pong", "data": {}})
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug(f"ws driver error: {e}")
        finally:
            await realtime.disconnect("driver", slug, ws)

    # ═══════════════════════════════════════════════════════════════
    # 🆕 HAVERSINE DISTANCE + AUTO DELIVERY FEE + WHATSAPP LINKS
    # ═══════════════════════════════════════════════════════════════
    def _haversine_km(lat1, lng1, lat2, lng2) -> float:
        if None in (lat1, lng1, lat2, lng2):
            return 0.0
        from math import radians, sin, cos, asin, sqrt
        R = 6371.0
        dlat = radians(lat2 - lat1)
        dlng = radians(lng2 - lng1)
        a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlng/2)**2
        return round(2 * R * asin(sqrt(a)), 2)

    def _wa_link(phone: str, text: str) -> str:
        """Generate a wa.me link (zero SDK needed)."""
        import urllib.parse as _u
        digits = "".join(c for c in (phone or "") if c.isdigit())
        # Assume Saudi Arabia if no country code (966)
        if digits.startswith("0"):
            digits = "966" + digits[1:]
        return f"https://wa.me/{digits}?text={_u.quote(text)}"

    _ORDER_STATUS_MSGS = {
        "accepted": "✅ تم قبول طلبك وسنبدأ التحضير قريباً.",
        "preparing": "👨‍🍳 طلبك قيد التحضير الآن.",
        "ready": "📦 طلبك جاهز — في انتظار السائق.",
        "on_the_way": "🛵 الطلب في الطريق إليك الآن!",
        "delivered": "✅ تم توصيل طلبك — بالهناء والشفاء!",
        "cancelled": "❌ عذراً، تم إلغاء طلبك. للاستفسار تواصل معنا.",
    }

    class SiteSettingsIn(BaseModel):
        base_lat: Optional[float] = None
        base_lng: Optional[float] = None
        base_fee: Optional[float] = None
        fee_per_km: Optional[float] = None
        free_delivery_above: Optional[float] = None

    @r.post("/client/delivery-settings")
    async def _delivery_settings(body: SiteSettingsIn, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        settings = {k: v for k, v in body.dict().items() if v is not None}
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"delivery_settings": settings, "updated_at": _iso_now()}}
        )
        return {"ok": True, "settings": settings}

    @r.get("/client/delivery-settings")
    async def _delivery_settings_get(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        return p.get("delivery_settings") or {"base_lat": None, "base_lng": None, "base_fee": 10, "fee_per_km": 2, "free_delivery_above": 200}

    @r.post("/public/{slug}/estimate-delivery")
    async def _estimate_delivery(slug: str, body: dict):
        """Estimate delivery fee for a given lat/lng based on site's delivery settings."""
        p = await database.website_projects.find_one({"slug": slug}, {"_id": 0, "delivery_settings": 1, "orders": 1})
        if not p:
            raise HTTPException(404, "not found")
        s = p.get("delivery_settings") or {"base_fee": 10, "fee_per_km": 2, "free_delivery_above": 200}
        lat = body.get("lat"); lng = body.get("lng"); subtotal = body.get("subtotal", 0)
        km = _haversine_km(s.get("base_lat"), s.get("base_lng"), lat, lng) if s.get("base_lat") else 0
        fee = float(s.get("base_fee", 10)) + km * float(s.get("fee_per_km", 2))
        if s.get("free_delivery_above") and subtotal >= float(s["free_delivery_above"]):
            fee = 0
        return {"fee": round(fee, 2), "distance_km": km, "free": fee == 0}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 TICKETS OWNER REPLY + CLIENT TICKET UPDATES
    # ═══════════════════════════════════════════════════════════════
    class TicketReplyIn(BaseModel):
        reply: str
        status: Optional[str] = None  # open | resolved

    @r.post("/admin/sites/{project_id}/tickets/{ticket_id}/reply")
    async def _admin_reply_ticket(project_id: str, ticket_id: str, body: TicketReplyIn, current_user: dict = Depends(auth_dep)):
        user_doc = await database.users.find_one({"id": current_user["user_id"]}, {"_id": 0, "role": 1})
        if (user_doc or {}).get("role") not in ("owner", "super_admin", "admin"):
            raise HTTPException(403, "غير مسموح")
        update = {"support_tickets.$.reply": body.reply[:4000], "support_tickets.$.replied_at": _iso_now()}
        if body.status:
            update["support_tickets.$.status"] = body.status
        res = await database.website_projects.update_one(
            {"id": project_id, "support_tickets.id": ticket_id}, {"$set": update}
        )
        if res.matched_count == 0:
            raise HTTPException(404, "Ticket not found")
        return {"ok": True}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 TECH STACK INFO — owner can show clients what powers their site
    # ═══════════════════════════════════════════════════════════════
    @r.get("/tech-stack")
    async def _tech_stack():
        return {
            "stack": [
                {"layer": "الواجهة الأمامية", "tech": "React 19 + TailwindCSS", "why": "الأسرع والأكثر استقراراً عالمياً — يستخدمه Netflix, Airbnb, Instagram"},
                {"layer": "الخادم (Backend)", "tech": "FastAPI + Python 3.11", "why": "أداء عالٍ + توثيق تلقائي + يدعم async — منافس لـ Node.js"},
                {"layer": "قاعدة البيانات", "tech": "MongoDB", "why": "مرنة، موزّعة، تتحمل ملايين الطلبات — أفضل للمحتوى الديناميكي"},
                {"layer": "المواقع المُنتجة", "tech": "HTML5 + CSS3 + Vanilla JS", "why": "خفيفة جداً، تعمل على كل الأجهزة، لا تحتاج Build"},
                {"layer": "الذكاء الاصطناعي", "tech": "GPT-4o + GPT-Image-1", "why": "أقوى نماذج OpenAI — للنصوص والشعارات"},
                {"layer": "المصادقة", "tech": "bcrypt + JWT", "why": "معيار صناعي — 100M+ موقع يستخدمونه"},
                {"layer": "الخرائط", "tech": "OpenStreetMap + Haversine", "why": "مجاني، لا يحتاج API key، دقيق"},
                {"layer": "الإشعارات", "tech": "wa.me (WhatsApp)", "why": "بدون تكلفة SDK — ينتقل لـ WhatsApp مباشرة"},
            ],
            "comparison": {
                "speed": "أسرع من WordPress بـ 5× (لا قاعدة بيانات PHP بطيئة)",
                "cost": "بدون رسوم شهرية للاستضافة (مقابل Wix $15-40/شهر)",
                "control": "ملكية كاملة للكود والبيانات (عكس Shopify/Squarespace)",
                "scale": "يتحمل ملايين الزيارات (MongoDB + FastAPI)",
            },
            "alternatives": [
                {"name": "WordPress", "pros": "قوالب كثيرة", "cons": "بطيء، يحتاج صيانة، hacked بسهولة"},
                {"name": "Wix", "pros": "سهل للمبتدئ", "cons": "غالٍ، ملكية ضعيفة، SEO متوسط"},
                {"name": "Shopify", "pros": "متخصص متاجر", "cons": "رسوم 2.9% على كل طلب + $29/شهر"},
                {"name": "Zitex", "pros": "أسرع + مجاني الاستضافة + AI مدمج + عربي أصيل", "cons": "—"},
            ],
        }

    # ═══════════════════════════════════════════════════════════════
    # 🆕 LOYALTY POINTS + COUPONS + ARABIC PAYMENT METHODS
    # ═══════════════════════════════════════════════════════════════
    class LoyaltySettingsIn(BaseModel):
        enabled: bool = True
        welcome_bonus: int = 50  # points on registration
        points_per_sar: float = 1  # earn 1 point per 1 SAR spent
        redeem_rate: float = 0.1  # 10 points = 1 SAR discount
        referral_bonus: int = 100  # points for referring a friend

    class CouponIn(BaseModel):
        code: str
        discount_percent: Optional[float] = 0  # e.g., 10 = 10% off
        discount_amount: Optional[float] = 0   # fixed amount
        min_order: Optional[float] = 0
        max_uses: Optional[int] = 100
        expires_at: Optional[str] = ""

    class CouponApplyIn(BaseModel):
        code: str
        subtotal: float

    @r.post("/client/loyalty-settings")
    async def _loyalty_settings(body: LoyaltySettingsIn, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"loyalty_settings": body.dict(), "updated_at": _iso_now()}}
        )
        return {"ok": True}

    @r.get("/client/loyalty-settings")
    async def _loyalty_settings_get(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        return p.get("loyalty_settings") or LoyaltySettingsIn().dict()

    @r.post("/client/coupons")
    async def _coupon_create(body: CouponIn, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        code = body.code.strip().upper()
        if any(c.get("code") == code for c in (p.get("coupons") or [])):
            raise HTTPException(400, "كود الكوبون مستخدم مسبقاً")
        coupon = {"id": str(uuid.uuid4()), "code": code,
                  "discount_percent": body.discount_percent or 0,
                  "discount_amount": body.discount_amount or 0,
                  "min_order": body.min_order or 0,
                  "max_uses": body.max_uses or 100, "used": 0,
                  "expires_at": body.expires_at or "",
                  "created_at": _iso_now(), "active": True}
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$push": {"coupons": coupon}, "$set": {"updated_at": _iso_now()}}
        )
        return {"ok": True, "coupon": coupon}

    @r.get("/client/coupons")
    async def _coupon_list(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        return {"coupons": p.get("coupons") or []}

    @r.delete("/client/coupons/{coupon_id}")
    async def _coupon_delete(coupon_id: str, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$pull": {"coupons": {"id": coupon_id}}}
        )
        return {"ok": True}

    @r.post("/public/{slug}/coupons/apply")
    async def _coupon_apply(slug: str, body: CouponApplyIn):
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0, "coupons": 1})
        if not p:
            raise HTTPException(404, "not found")
        code = body.code.strip().upper()
        coupon = next((c for c in (p.get("coupons") or []) if c.get("code") == code and c.get("active")), None)
        if not coupon:
            raise HTTPException(404, "كود الكوبون غير صحيح")
        if coupon.get("used", 0) >= coupon.get("max_uses", 0):
            raise HTTPException(400, "انتهت استخدامات هذا الكوبون")
        if body.subtotal < coupon.get("min_order", 0):
            raise HTTPException(400, f"الحد الأدنى للطلب {coupon['min_order']} ر.س")
        discount = 0
        if coupon.get("discount_percent"):
            discount = body.subtotal * (coupon["discount_percent"] / 100)
        if coupon.get("discount_amount"):
            discount = max(discount, coupon["discount_amount"])
        return {"ok": True, "discount": round(discount, 2), "code": code, "new_total": round(body.subtotal - discount, 2)}

    @r.get("/public/{slug}/my-points")
    async def _my_points(slug: str, authorization: str = _Header(None)):
        data = await _resolve_site_customer(slug, authorization or "")
        s = data["project"].get("loyalty_settings") or LoyaltySettingsIn().dict()
        pts = int(data["customer"].get("points") or 0)
        return {"points": pts, "redeem_rate": s.get("redeem_rate", 0.1),
                "equivalent_sar": round(pts * s.get("redeem_rate", 0.1), 2),
                "enabled": s.get("enabled", True)}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 LIVE MAP — drivers' last known locations + active orders
    # ═══════════════════════════════════════════════════════════════
    @r.get("/client/live-map")
    async def _client_live_map(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        s = p.get("delivery_settings") or {}
        drivers = [
            {"id": d.get("id"), "name": d.get("name"), "lat": d.get("lat"), "lng": d.get("lng"),
             "last_ping": d.get("last_ping"), "active": d.get("active", True)}
            for d in (p.get("drivers") or []) if d.get("lat") and d.get("lng")
        ]
        active_orders = [
            {"id": o.get("id"), "customer": o.get("customer_name"),
             "lat": o.get("lat"), "lng": o.get("lng"),
             "status": o.get("status"), "driver_id": o.get("driver_id"),
             "total": o.get("total")}
            for o in (p.get("orders") or [])
            if o.get("lat") and o.get("lng") and o.get("status") not in ("delivered", "cancelled")
        ]
        return {
            "base": {"lat": s.get("base_lat"), "lng": s.get("base_lng")},
            "drivers": drivers,
            "orders": active_orders,
        }

    # ═══════════════════════════════════════════════════════════════
    # 🆕 MULTI-TENANT PAYMENT GATEWAYS (Moyasar / Tabby / Tamara / COD)
    # Each tenant stores its own keys (encrypted). Checkout uses tenant-scoped keys.
    # ═══════════════════════════════════════════════════════════════
    @r.get("/payment-gateways/catalog")
    async def _pg_catalog():
        """Public catalog (no auth) — used by the client dashboard UI."""
        return {"providers": pg.catalog_public()}

    @r.get("/payment-gateways/compare")
    async def _pg_compare():
        """Detailed side-by-side comparison of all gateways (fees, settlement, pros/cons)."""
        return {"rows": pg.compare_all()}

    # ═══════════════════════════════════════════════════════════════
    # 🎨 WIDGET CUSTOMIZATION — variants + position per widget per site
    # ═══════════════════════════════════════════════════════════════
    @r.get("/widget-styles/catalog")
    async def _widget_catalog():
        """Public catalog of all customizable widgets + their variants."""
        return {"widgets": wx.catalog(), "positions": list(wx.POSITIONS.keys())}

    @r.get("/client/widget-styles")
    async def _client_ws(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        return {"widget_styles": p.get("widget_styles") or {}}

    class WidgetStyleIn(BaseModel):
        variant: Optional[str] = None
        position: Optional[str] = None
        offset_x: Optional[int] = 0
        offset_y: Optional[int] = 0
        hidden: Optional[bool] = False

    @r.put("/client/widget-styles/{widget_id}")
    async def _save_ws(widget_id: str, body: WidgetStyleIn, authorization: str = _Header(None)):
        if widget_id not in wx.WIDGETS:
            raise HTTPException(404, "ودجت غير معروفة")
        if body.position and body.position not in wx.POSITIONS:
            raise HTTPException(400, "موقع غير صالح")
        p = await _resolve_client_project(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$set": {f"widget_styles.{widget_id}": body.model_dump(exclude_none=False),
                      "updated_at": _iso_now()}},
        )
        return {"ok": True}

    @r.delete("/client/widget-styles/{widget_id}")
    async def _reset_ws(widget_id: str, authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$unset": {f"widget_styles.{widget_id}": ""}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True}

    @r.get("/client/payment-gateways")
    async def _client_pg_list(authorization: str = _Header(None)):
        p = await _resolve_client_project(authorization or "")
        stored = p.get("payment_gateways") or {}
        return {
            "gateways": [pg.safe_gateway_view(pid, stored.get(pid)) for pid in pg.PROVIDERS],
        }

    class GatewayUpdateIn(BaseModel):
        enabled: Optional[bool] = None
        publishable_key: Optional[str] = None
        secret_key: Optional[str] = None
        public_key: Optional[str] = None
        api_token: Optional[str] = None
        notification_token: Optional[str] = None
        methods: Optional[List[str]] = None
        test_mode: Optional[bool] = None

    @r.put("/client/payment-gateways/{provider_id}")
    async def _client_pg_update(provider_id: str, body: GatewayUpdateIn, authorization: str = _Header(None)):
        if provider_id not in pg.PROVIDERS:
            raise HTTPException(404, "مزود غير معروف")
        p = await _resolve_client_project(authorization or "")
        builder = pg.PATCH_BUILDERS[provider_id]
        # Merge with existing so partial updates work
        current = (p.get("payment_gateways") or {}).get(provider_id) or {}
        new_patch = builder(body.model_dump(exclude_none=True))
        merged = {**current, **new_patch}
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$set": {f"payment_gateways.{provider_id}": merged, "updated_at": _iso_now()}},
        )
        return {"ok": True, "gateway": pg.safe_gateway_view(provider_id, merged)}

    @r.delete("/client/payment-gateways/{provider_id}")
    async def _client_pg_delete(provider_id: str, authorization: str = _Header(None)):
        if provider_id not in pg.PROVIDERS:
            raise HTTPException(404, "مزود غير معروف")
        p = await _resolve_client_project(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$unset": {f"payment_gateways.{provider_id}": ""}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True}

    @r.post("/client/payment-gateways/{provider_id}/test")
    async def _client_pg_test(provider_id: str, authorization: str = _Header(None)):
        """Validate stored credentials by hitting the provider's API."""
        if provider_id not in pg.PROVIDERS:
            raise HTTPException(404, "مزود غير معروف")
        p = await _resolve_client_project(authorization or "")
        gw = (p.get("payment_gateways") or {}).get(provider_id) or {}
        if provider_id == "moyasar":
            prov = pg.load_moyasar(gw)
            if not prov:
                return {"ok": False, "message": "لم يتم إعداد مفاتيح Moyasar بعد"}
            ok, msg = await prov.test()
            return {"ok": ok, "message": msg}
        if provider_id == "tabby":
            prov = pg.load_tabby(gw)
            if not prov:
                return {"ok": False, "message": "لم يتم إعداد مفاتيح Tabby بعد"}
            ok, msg = await prov.test()
            return {"ok": ok, "message": msg}
        if provider_id == "tamara":
            prov = pg.load_tamara(gw)
            if not prov:
                return {"ok": False, "message": "لم يتم إعداد API Token لـTamara بعد"}
            ok, msg = await prov.test()
            return {"ok": ok, "message": msg}
        if provider_id == "cod":
            return {"ok": True, "message": "الدفع عند الاستلام لا يحتاج مفاتيح — فقط فعّله"}
        return {"ok": False, "message": "غير مدعوم"}

    # ---- Public checkout init (tenant-scoped) ----
    class PaymentInitIn(BaseModel):
        order_id: str
        provider: str  # moyasar | cod | tabby | tamara

    @r.get("/public/{slug}/payment-gateways")
    async def _public_pg_list(slug: str):
        """Frontend-visible gateway list for a given site (only enabled & safe fields)."""
        proj = await database.website_projects.find_one(
            {"slug": slug}, {"_id": 0, "payment_gateways": 1}
        )
        if not proj:
            raise HTTPException(404, "الموقع غير موجود")
        stored = proj.get("payment_gateways") or {}
        visible = []
        for pid, meta in pg.PROVIDERS.items():
            raw = stored.get(pid) or {}
            if not raw.get("enabled"):
                continue
            if pid == "cod":
                visible.append({"id": "cod", "name_ar": meta["name_ar"], "methods": ["cod"]})
            elif pid == "moyasar":
                if not (raw.get("publishable_key") and raw.get("secret_key_enc")):
                    continue
                visible.append({
                    "id": "moyasar",
                    "name_ar": meta["name_ar"],
                    "methods": raw.get("methods") or meta["supports_methods"],
                    "publishable_key": raw.get("publishable_key"),  # pk_ is safe for browser
                })
            elif pid == "tabby":
                if not (raw.get("public_key") and raw.get("secret_key_enc")):
                    continue
                visible.append({"id": "tabby", "name_ar": meta["name_ar"],
                                "methods": ["tabby"], "public_key": raw.get("public_key")})
            elif pid == "tamara":
                if not raw.get("api_token_enc"):
                    continue
                visible.append({"id": "tamara", "name_ar": meta["name_ar"],
                                "methods": ["tamara"]})
        return {"gateways": visible}

    @r.post("/public/{slug}/payments/init")
    async def _public_payment_init(slug: str, body: PaymentInitIn, authorization: str = _Header(None)):
        data = await _resolve_site_customer(slug, authorization or "")
        proj = data["project"]
        order = next((o for o in (proj.get("orders") or []) if o.get("id") == body.order_id), None)
        if not order:
            raise HTTPException(404, "الطلب غير موجود")
        # Must belong to the logged-in customer
        if order.get("customer_id") != data["customer"]["id"]:
            raise HTTPException(403, "غير مصرح")
        amount_sar = float(order.get("total") or 0)
        if amount_sar <= 0:
            raise HTTPException(400, "مبلغ غير صحيح")

        stored = proj.get("payment_gateways") or {}
        gw = stored.get(body.provider) or {}
        if not gw.get("enabled"):
            raise HTTPException(400, "هذه الطريقة غير مفعلة في هذا المتجر")

        if body.provider == "cod":
            await database.website_projects.update_one(
                {"id": proj["id"], "orders.id": body.order_id},
                {"$set": {"orders.$.payment": {"provider": "cod", "status": "pending"}}},
            )
            return {"ok": True, "provider": "cod", "status": "pending",
                    "message": "طلبك سيُدفَع نقداً عند الاستلام", "redirect_url": None}

        if body.provider == "moyasar":
            prov = pg.load_moyasar(gw)
            if not prov:
                raise HTTPException(400, "مفاتيح Moyasar غير مُعدّة")
            base = os.environ.get("BACKEND_URL", "").rstrip("/")
            callback = f"{base}/api/websites/public/{slug}/payments/callback?order_id={body.order_id}"
            try:
                inv = await prov.create_invoice(
                    amount_sar=amount_sar,
                    description=f"طلب #{body.order_id[:8]} — {proj.get('name','')}",
                    callback_url=callback,
                    methods=gw.get("methods") or ["creditcard", "mada", "applepay", "stcpay"],
                    metadata={"order_id": body.order_id, "slug": slug, "customer_id": data["customer"]["id"]},
                )
            except pg.PaymentError as e:
                raise HTTPException(502, str(e))
            await database.website_projects.update_one(
                {"id": proj["id"], "orders.id": body.order_id},
                {"$set": {"orders.$.payment": {
                    "provider": "moyasar",
                    "invoice_id": inv["invoice_id"],
                    "status": "initiated",
                    "amount_sar": amount_sar,
                }}},
            )
            return {"ok": True, "provider": "moyasar", "redirect_url": inv["url"],
                    "invoice_id": inv["invoice_id"], "status": "initiated"}

        if body.provider in ("tabby", "tamara"):
            base = os.environ.get("BACKEND_URL", "").rstrip("/")
            callback = f"{base}/api/websites/public/{slug}/payments/callback?order_id={body.order_id}"
            cust = {
                "name": data["customer"].get("name"),
                "phone": data["customer"].get("phone"),
                "email": data["customer"].get("email") or f"{data['customer'].get('phone','user')}@zitex.site",
                "address": order.get("address"),
                "city": order.get("city") or "الرياض",
            }
            items = order.get("items") or [{"id": "item", "name": "طلب", "price": amount_sar, "qty": 1}]
            try:
                if body.provider == "tabby":
                    prov = pg.load_tabby(gw)
                    if not prov:
                        raise HTTPException(400, "مفاتيح Tabby غير مُعدّة")
                    out = await prov.create_checkout(
                        amount_sar=amount_sar, order_id=body.order_id, slug=slug,
                        customer=cust, items=items, callback_url=callback,
                    )
                    pay_doc = {"provider": "tabby", "checkout_id": out["checkout_id"],
                               "status": "initiated", "amount_sar": amount_sar}
                else:
                    prov = pg.load_tamara(gw)
                    if not prov:
                        raise HTTPException(400, "API Token لـTamara غير مُعدّ")
                    out = await prov.create_checkout(
                        amount_sar=amount_sar, order_id=body.order_id, slug=slug,
                        customer=cust, items=items, callback_url=callback,
                    )
                    pay_doc = {"provider": "tamara",
                               "tamara_order_id": out["order_id_tamara"],
                               "checkout_id": out["checkout_id"],
                               "status": "initiated", "amount_sar": amount_sar}
            except pg.PaymentError as e:
                raise HTTPException(502, str(e))
            await database.website_projects.update_one(
                {"id": proj["id"], "orders.id": body.order_id},
                {"$set": {"orders.$.payment": pay_doc}},
            )
            return {"ok": True, "provider": body.provider, "redirect_url": out["url"],
                    "status": "initiated"}

        raise HTTPException(400, "بوابة غير مدعومة بعد")

    @r.get("/public/{slug}/payments/callback")
    async def _public_payment_callback(slug: str, order_id: str, id: Optional[str] = None, status: Optional[str] = None):
        """Moyasar redirects here after customer completes payment.

        We verify server-side by fetching the invoice/payment, then update the order.
        Returns a simple Arabic HTML page redirecting back to the site.
        """
        proj = await database.website_projects.find_one({"slug": slug}, {"_id": 0})
        if not proj:
            raise HTTPException(404, "الموقع غير موجود")
        order = next((o for o in (proj.get("orders") or []) if o.get("id") == order_id), None)
        if not order:
            raise HTTPException(404, "الطلب غير موجود")
        pay = order.get("payment") or {}
        verified_status = "pending"
        if pay.get("provider") == "moyasar" and pay.get("invoice_id"):
            prov = pg.load_moyasar((proj.get("payment_gateways") or {}).get("moyasar"))
            if prov:
                try:
                    inv = await prov.fetch_invoice(pay["invoice_id"])
                    paid_halalas = inv.get("amount", 0)
                    expected_halalas = int(round(float(pay.get("amount_sar") or order.get("total") or 0) * 100))
                    mstatus = inv.get("status")
                    if mstatus == "paid" and paid_halalas == expected_halalas:
                        verified_status = "paid"
                    elif mstatus in ("expired", "failed", "canceled"):
                        verified_status = mstatus
                except pg.PaymentError as e:
                    logger.warning(f"callback fetch failed: {e}")
        elif pay.get("provider") == "tabby" and pay.get("checkout_id"):
            prov = pg.load_tabby((proj.get("payment_gateways") or {}).get("tabby"))
            if prov:
                try:
                    inv = await prov.verify(pay["checkout_id"])
                    tstatus = (inv.get("status") or "").upper()
                    if tstatus in ("APPROVED", "AUTHORIZED", "CLOSED"):
                        verified_status = "paid"
                    elif tstatus in ("EXPIRED", "REJECTED", "FAILED"):
                        verified_status = tstatus.lower()
                except pg.PaymentError as e:
                    logger.warning(f"tabby verify failed: {e}")
        elif pay.get("provider") == "tamara" and pay.get("tamara_order_id"):
            prov = pg.load_tamara((proj.get("payment_gateways") or {}).get("tamara"))
            if prov:
                try:
                    inv = await prov.verify(pay["tamara_order_id"])
                    tstatus = (inv.get("status") or "").upper()
                    if tstatus in ("APPROVED", "AUTHORISED", "FULLY_CAPTURED"):
                        verified_status = "paid"
                    elif tstatus in ("DECLINED", "CANCELED", "CANCELLED", "EXPIRED", "FAILED"):
                        verified_status = tstatus.lower()
                except pg.PaymentError as e:
                    logger.warning(f"tamara verify failed: {e}")
        # Persist (idempotent)
        if pay.get("status") != "paid":
            await database.website_projects.update_one(
                {"id": proj["id"], "orders.id": order_id},
                {"$set": {
                    "orders.$.payment.status": verified_status,
                    "orders.$.payment.verified_at": _iso_now(),
                    "updated_at": _iso_now(),
                }},
            )
            try:
                await realtime.broadcast_all(slug, "order_status", {
                    "order_id": order_id, "status": order.get("status"),
                    "payment_status": verified_status,
                })
            except Exception:
                pass
        # Arabic HTML success/failure page
        success = verified_status == "paid"
        color = "#16a34a" if success else "#dc2626"
        icon = "✅" if success else "❌"
        title = "تم الدفع بنجاح" if success else "لم يكتمل الدفع"
        body = ("شكراً لك! تم استلام طلبك وسيتم تجهيزه قريباً."
                if success else "يمكنك المحاولة مجدداً من صفحة طلباتك.")
        html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>body{{margin:0;font-family:-apple-system,Tahoma,sans-serif;background:#0b0f1f;color:#fff;
display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}}
.card{{max-width:420px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);
border-radius:24px;padding:40px;text-align:center}}.icon{{font-size:72px;margin-bottom:12px}}
h1{{margin:0 0 12px;color:{color}}}p{{opacity:.75;line-height:1.7}}
a{{display:inline-block;margin-top:24px;padding:12px 24px;background:linear-gradient(90deg,#FFD700,#FFA500);
color:#000;text-decoration:none;border-radius:12px;font-weight:900}}</style></head><body>
<div class="card"><div class="icon">{icon}</div><h1>{title}</h1><p>{body}</p>
<a href="/sites/{slug}">العودة للمتجر</a></div></body></html>"""
        return HTMLResponse(content=html)

    @r.post("/webhook/payments/{slug}/moyasar")
    async def _webhook_moyasar(slug: str, payload: Dict[str, Any]):
        """Moyasar webhook (optional) — idempotent update of order status.

        Moyasar does not sign webhooks by default the same way as Stripe; we rely
        on re-fetching the invoice to verify the event payload.
        """
        order_id = (payload.get("data") or {}).get("metadata", {}).get("order_id") or payload.get("metadata", {}).get("order_id")
        if not order_id:
            return {"received": True, "note": "no order_id in metadata"}
        proj = await database.website_projects.find_one({"slug": slug}, {"_id": 0})
        if not proj:
            return {"received": True, "note": "unknown slug"}
        order = next((o for o in (proj.get("orders") or []) if o.get("id") == order_id), None)
        if not order:
            return {"received": True, "note": "order not found"}
        pay = order.get("payment") or {}
        if pay.get("provider") != "moyasar" or not pay.get("invoice_id"):
            return {"received": True, "note": "no moyasar invoice"}
        prov = pg.load_moyasar((proj.get("payment_gateways") or {}).get("moyasar"))
        if not prov:
            return {"received": True, "note": "no credentials"}
        try:
            inv = await prov.fetch_invoice(pay["invoice_id"])
        except pg.PaymentError:
            return {"received": True, "note": "fetch failed"}
        new_status = inv.get("status", "initiated")
        if pay.get("status") != "paid":
            await database.website_projects.update_one(
                {"id": proj["id"], "orders.id": order_id},
                {"$set": {
                    "orders.$.payment.status": new_status,
                    "orders.$.payment.verified_at": _iso_now(),
                }},
            )
        return {"received": True, "status": new_status}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 PWA MANIFEST + PAYMENT METHODS CATALOG
    # ═══════════════════════════════════════════════════════════════
    @r.get("/public/{slug}/manifest.json")
    async def _pwa_manifest(slug: str):
        p = await database.website_projects.find_one({"slug": slug}, {"_id": 0, "name": 1, "theme": 1})
        if not p:
            raise HTTPException(404, "not found")
        theme = p.get("theme") or {}
        return {
            "name": p.get("name", "موقعي"),
            "short_name": (p.get("name") or "Site")[:12],
            "start_url": f"/sites/{slug}",
            "display": "standalone",
            "background_color": theme.get("background", "#0b0f1f"),
            "theme_color": theme.get("primary", "#FFD700"),
            "lang": "ar",
            "dir": "rtl",
            "icons": [
                {"src": theme.get("logo_url") or "https://ai-cinematic-hub-2.preview.emergentagent.com/favicon.png", "sizes": "192x192", "type": "image/png"},
                {"src": theme.get("logo_url") or "https://ai-cinematic-hub-2.preview.emergentagent.com/favicon.png", "sizes": "512x512", "type": "image/png"},
            ],
        }

    @r.get("/payment-methods")
    async def _payment_methods():
        """Catalog of supported payment gateways (Arabic & international)."""
        return {
            "methods": [
                {"id": "stripe", "name": "💳 Visa/Mastercard", "status": "ready", "fee": "2.9% + 1 ر.س"},
                {"id": "mada", "name": "🏦 مدى", "status": "ready_via_stripe", "fee": "1% — البطاقة السعودية الأكثر استخداماً"},
                {"id": "applepay", "name": "🍎 Apple Pay", "status": "ready_via_stripe", "fee": "2.9%"},
                {"id": "stcpay", "name": "📱 STC Pay", "status": "coming_soon", "fee": "1.5%"},
                {"id": "tamara", "name": "🛍️ تمارا (ادفع لاحقاً)", "status": "coming_soon", "fee": "بلا رسوم للعميل"},
                {"id": "tabby", "name": "💰 Tabby (قسّم على 4)", "status": "coming_soon", "fee": "بلا رسوم للعميل"},
                {"id": "cod", "name": "💵 الدفع عند الاستلام", "status": "ready", "fee": "مجاناً"},
                {"id": "bank", "name": "🏛️ تحويل بنكي", "status": "ready", "fee": "مجاناً"},
            ],
            "note": "Stripe + Mada + Apple Pay جاهزة للاستخدام الآن. باقي البوابات جاهزة البنية التحتية وتحتاج تفعيل.",
        }

    # ═══════════════════════════════════════════════════════════════
    # 🆕 ADMIN — reply to tickets (owner side)
    # ═══════════════════════════════════════════════════════════════
    @r.get("/admin/all-tickets")
    async def _all_tickets(current_user: dict = Depends(auth_dep)):
        user_doc = await database.users.find_one({"id": current_user["user_id"]}, {"_id": 0, "role": 1})
        if (user_doc or {}).get("role") not in ("owner", "super_admin", "admin"):
            raise HTTPException(403, "غير مسموح")
        cursor = database.website_projects.find(
            {"support_tickets": {"$exists": True, "$ne": []}},
            {"_id": 0, "id": 1, "name": 1, "slug": 1, "support_tickets": 1}
        )
        out = []
        async for p in cursor:
            for t in (p.get("support_tickets") or []):
                out.append({**t, "project_id": p["id"], "project_name": p.get("name"), "project_slug": p.get("slug")})
        return {"tickets": sorted(out, key=lambda x: x.get("at") or "", reverse=True)}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 VERTICAL ENGINES — bookings / products / portfolio (simulation)
    # ═══════════════════════════════════════════════════════════════
    from .engines import register_engines as _reg_engines
    _reg_engines(r, database, _resolve_client_project, _resolve_site_customer, realtime)
    from .engines_v2 import register_engines_v2 as _reg_v2
    _reg_v2(r, database, _resolve_client_project, _resolve_site_customer)

    # 🆕 Chatbot owner config + public chat endpoints
    try:
        from .chatbot import register_owner_endpoints, init_routes as init_chatbot_routes
        register_owner_endpoints(r, database, auth_dep, resolve_client=_resolve_client_project)
        chatbot_router = init_chatbot_routes(database)
        app.include_router(chatbot_router, prefix="/api")
    except Exception as _ce:
        import logging
        logging.getLogger(__name__).error(f"chatbot module failed: {_ce}")

    # 🆕 Stories + Animated Banner + AI media generation
    try:
        from .stories import register_routes as register_stories_routes
        register_stories_routes(r, database, _resolve_client_project)
    except Exception as _se:
        import logging
        logging.getLogger(__name__).error(f"stories module failed: {_se}")

    # 🆕 AutoPilot Stories — smart suggestions + scheduled auto-publish
    try:
        from .autopilot import register_routes as register_autopilot_routes, start_scheduler as start_ap_scheduler
        register_autopilot_routes(r, database, _resolve_client_project)
        start_ap_scheduler(database, interval_seconds=3600)
    except Exception as _ae:
        import logging
        logging.getLogger(__name__).error(f"autopilot module failed: {_ae}")

    app.include_router(r)
    return r


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _chip_label(step_id: str, value: Any) -> str:
    step = get_step(step_id)
    chips = (step or {}).get("chips", [])
    if isinstance(value, list):
        labels = []
        for v in value:
            c = next((c for c in chips if c.get("id") == v or c.get("value") == v), None)
            labels.append((c or {}).get("label", str(v)))
        return "، ".join(labels)
    c = next((c for c in chips if c.get("id") == value or c.get("value") == value), None)
    return (c or {}).get("label", str(value))


def _compute_insert_position(sections: List[Dict[str, Any]], position: str) -> int:
    """Map a position keyword to an actual list index for insertion.
    Keywords: 'top'|'bottom'|'after_hero'|'before_footer'|'after:TYPE'|'before:TYPE'|numeric.
    Defaults to 'before_footer' (smart default — sections go visibly before the footer)."""
    if not sections:
        return 0
    # Numeric index
    try:
        if position and position.lstrip("-").isdigit():
            n = int(position)
            return max(0, min(n, len(sections)))
    except Exception:
        pass
    p = (position or "").strip().lower()
    if p in ("top", "first", "start", "begin"):
        # After hero (if any) — "top" visually means above-the-fold
        hero_idx = next((i for i, s in enumerate(sections) if s.get("type") == "hero"), -1)
        return hero_idx + 1 if hero_idx >= 0 else 0
    if p in ("very_top", "absolute_top", "above_hero"):
        return 0
    if p in ("bottom", "last", "end"):
        return len(sections)
    if p == "after_hero":
        hero_idx = next((i for i, s in enumerate(sections) if s.get("type") == "hero"), -1)
        return hero_idx + 1 if hero_idx >= 0 else 0
    if p.startswith("after:"):
        tgt = p.split(":", 1)[1].strip()
        idx = next((i for i, s in enumerate(sections) if s.get("type") == tgt), -1)
        if idx >= 0:
            return idx + 1
    if p.startswith("before:"):
        tgt = p.split(":", 1)[1].strip()
        idx = next((i for i, s in enumerate(sections) if s.get("type") == tgt), -1)
        if idx >= 0:
            return idx
    # Default: before footer
    footer_idx = next((i for i, s in enumerate(sections) if s.get("type") == "footer"), -1)
    return footer_idx if footer_idx >= 0 else len(sections)


def _apply_ai_action(project: Dict[str, Any], action: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Mutate project based on a directive returned by the AI."""
    if not action or not isinstance(action, dict):
        return project
    a = action.get("action")
    v = action.get("value")
    try:
        if a == "advance":
            return apply_answer(project, action.get("step") or project.get("wizard", {}).get("step"), v)
        if a == "apply_theme" and isinstance(v, dict):
            project["theme"] = {**(project.get("theme") or {}), **v}
        if a == "apply_button":
            project["theme"] = {**(project.get("theme") or {}), "radius": RADIUS_MAP.get(str(v), "medium")}
        if a == "apply_font":
            project["theme"] = {**(project.get("theme") or {}), "font": str(v) or "Tajawal"}
        if a == "inject_css" and isinstance(v, str):
            # append to existing custom_css
            existing = (project.get("theme") or {}).get("custom_css", "")
            project["theme"] = {**(project.get("theme") or {}), "custom_css": (existing + "\n" + v).strip()}
        if a == "add_section" and isinstance(v, dict):
            # 🧠 Smart dedup + positioning — NEVER create duplicates.
            # If a section of the same type already exists, UPDATE its data + move it to requested position.
            stype = v.get("type", "hero")
            new_data = v.get("data") or {}
            position = str(v.get("position") or "").lower()  # 'top' | 'bottom' | 'after_hero' | int | ''
            sections = list(project.get("sections") or [])
            existing_idx = next((i for i, s in enumerate(sections) if s.get("type") == stype), -1)
            if existing_idx >= 0:
                # Update data, then reposition if requested
                sec = sections.pop(existing_idx)
                # Merge data: new fields override, but preserve missing keys
                sec = {**sec, "data": {**(sec.get("data") or {}), **new_data}, "visible": True}
            else:
                sec = {"id": f"sec-{uuid.uuid4().hex[:8]}", "type": stype,
                       "order": 0, "visible": True, "data": new_data}
            # Compute insert index
            insert_at = _compute_insert_position(sections, position)
            sections.insert(insert_at, sec)
            project["sections"] = [{**s, "order": i} for i, s in enumerate(sections)]
        if a == "move_section" and isinstance(v, dict):
            # 🚚 Move an existing section (by section_id or section_type) to a new position.
            sid = v.get("section_id")
            stype = v.get("section_type")
            position = str(v.get("position") or "").lower()
            sections = list(project.get("sections") or [])
            idx = next((i for i, s in enumerate(sections)
                        if (sid and s.get("id") == sid) or (not sid and s.get("type") == stype)), -1)
            if idx >= 0:
                sec = sections.pop(idx)
                insert_at = _compute_insert_position(sections, position)
                sections.insert(insert_at, sec)
                project["sections"] = [{**s, "order": i} for i, s in enumerate(sections)]
        if a == "fill_section" and isinstance(v, dict):
            # Merge AI-provided data into an existing section matching section_type
            stype = v.get("section_type")
            patch = v.get("data") or {}
            sections = list(project.get("sections") or [])
            for i, s in enumerate(sections):
                if s.get("type") == stype:
                    sections[i] = {**s, "data": {**(s.get("data") or {}), **patch}}
                    break
            project["sections"] = sections
        if a == "patch_section" and isinstance(v, dict):
            # Precise edit by section_id OR section_type, can also reorder/hide/show
            sid = v.get("section_id")
            stype = v.get("section_type")
            patch_data = v.get("data")  # dict or None
            set_fields = v.get("set") or {}   # visible / order etc.
            sections = list(project.get("sections") or [])
            for i, s in enumerate(sections):
                match = (sid and s.get("id") == sid) or (not sid and s.get("type") == stype)
                if match:
                    if patch_data:
                        s = {**s, "data": {**(s.get("data") or {}), **patch_data}}
                    for k, val in set_fields.items():
                        s[k] = val
                    sections[i] = s
                    break
            project["sections"] = sections
        if a == "remove_section" and isinstance(v, dict):
            sid = v.get("section_id")
            stype = v.get("section_type")
            sections = [s for s in (project.get("sections") or [])
                        if not ((sid and s.get("id") == sid) or (not sid and s.get("type") == stype))]
            project["sections"] = [{**s, "order": i} for i, s in enumerate(sections)]
        if a == "scaffold" and isinstance(v, dict):
            # Full scaffold: replace sections + merge theme + inject custom_css
            new_sections = v.get("sections") or []
            if new_sections:
                project["sections"] = [
                    {"id": f"sec-{uuid.uuid4().hex[:8]}", "type": s.get("type", "hero"),
                     "order": i, "visible": True, "data": s.get("data") or {}}
                    for i, s in enumerate(new_sections)
                ]
            hints = v.get("theme_hints") or {}
            theme = {**(project.get("theme") or {}), **hints}
            if v.get("custom_css"):
                theme["custom_css"] = (theme.get("custom_css", "") + "\n" + v["custom_css"]).strip()
            project["theme"] = theme
            if v.get("name"):
                project["name"] = v["name"]
            # Auto-advance past brief step if currently there
            wiz = project.get("wizard") or default_wizard_state()
            if wiz.get("step") == "brief":
                wiz["answers"] = {**(wiz.get("answers") or {}), "brief": v.get("name") or "custom"}
                wiz["completed"] = list(dict.fromkeys((wiz.get("completed") or []) + ["brief"]))
                wiz["step"] = "variant"
                project["wizard"] = wiz
        if a == "custom_feature" and isinstance(v, dict):
            wizard = project.get("wizard") or default_wizard_state()
            ans = dict(wizard.get("answers") or {})
            cf = list(ans.get("custom_features") or [])
            cf.append({"title": v.get("title"), "description": v.get("description"), "section_type": v.get("section_type")})
            ans["custom_features"] = cf
            wizard["answers"] = ans
            project["wizard"] = wizard
    except Exception as e:
        logger.warning(f"apply_ai_action error: {e}")
    return project
