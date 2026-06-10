"""
Real AI Image Studio - powered by Gemini Nano Banana via Emergent LLM Key.
Replaces the frontend Unsplash mock pools with actual AI generation.
"""
import os
import base64
import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/image-studio", tags=["image-studio"])


class GenerateRequest(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    count: int = 1            # 1-12
    style: str = "white"      # white | lifestyle | creative | package
    bg_color: str = "white"   # white | gray | black | beige | gold | navy
    person_holding: bool = False
    angles: Optional[List[str]] = None  # ['front','back','left','right','top','package','held']


class GenerateResponse(BaseModel):
    images: List[str]  # data URIs (data:image/png;base64,...)
    prompt_used: str
    model: str
    cost: int


STYLE_DIRECTIVES = {
    "white": "isolated on pure white seamless studio background, soft even studio lighting, product photography, sharp focus, no shadows",
    "lifestyle": "natural lifestyle scene, human hand or person interacting with the product, real-world environment, soft natural lighting, depth of field",
    "creative": "dramatic cinematic lighting, artistic composition, premium luxury feel, rim lighting, shallow depth of field",
    "package": "retail product box / packaging shot, clean studio background, top-down or 3/4 angle, brand-ready",
}
BG_COLOR_MAP = {
    "white": "pure white #ffffff",
    "gray": "soft light gray #e5e7eb",
    "black": "deep matte black #1a1a1a",
    "beige": "warm beige #f5e6d3",
    "gold": "luxurious gold gradient",
    "navy": "deep navy blue #1e3a8a",
}
ANGLE_TEXT = {
    "front": "front view",
    "back": "back view",
    "left": "left side view",
    "right": "right side view",
    "top": "top-down view",
    "package": "in retail packaging box",
    "held": "held by a human hand",
}


def _build_full_prompt(req: GenerateRequest, angle: Optional[str] = None) -> str:
    parts = [req.prompt.strip()]
    if angle and angle in ANGLE_TEXT:
        parts.append(ANGLE_TEXT[angle])
    style_directive = STYLE_DIRECTIVES.get(req.style, STYLE_DIRECTIVES["white"])
    if req.style == "white" and req.bg_color != "white":
        bg = BG_COLOR_MAP.get(req.bg_color, "neutral background")
        style_directive = f"isolated on {bg} seamless studio background, soft even lighting, sharp focus, no environmental clutter"
    parts.append(style_directive)
    if not req.person_holding and req.style != "lifestyle":
        parts.append("product only, no people, no hands")
    parts.append(f"aspect ratio {req.width}:{req.height}, high resolution, ultra-detailed, professional commercial photography")
    return ", ".join(parts)


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
    if req.count < 1 or req.count > 12:
        raise HTTPException(status_code=400, detail="count must be 1..12")
    if not req.prompt or len(req.prompt.strip()) < 2:
        raise HTTPException(status_code=400, detail="prompt is required")

    from emergentintegrations.llm.chat import LlmChat, UserMessage

    images_b64: List[str] = []
    used_prompts: List[str] = []
    model_id = "gemini-3.1-flash-image-preview"

    # Build per-image prompts (vary by angle if provided)
    angles = (req.angles or [])[: req.count] if req.angles else []
    while len(angles) < req.count:
        angles.append(None)

    for i in range(req.count):
        full_prompt = _build_full_prompt(req, angle=angles[i])
        used_prompts.append(full_prompt)
        try:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"studio-{uuid.uuid4().hex[:12]}",
                system_message="You are an expert product photographer AI. Generate ONLY the requested image based on the prompt. No text, no watermarks, no extra elements unless explicitly asked.",
            )
            chat.with_model("gemini", model_id).with_params(modalities=["image", "text"])
            _text, imgs = await chat.send_message_multimodal_response(UserMessage(text=full_prompt))
            if imgs:
                img = imgs[0]
                mime = img.get("mime_type", "image/png")
                data = img["data"]
                images_b64.append(f"data:{mime};base64,{data}")
            else:
                raise HTTPException(status_code=502, detail=f"AI returned no image for variant {i+1}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Generation failed at variant {i+1}: {str(e)[:200]}")

    cost = req.count * 5
    return GenerateResponse(
        images=images_b64,
        prompt_used=used_prompts[0] if used_prompts else req.prompt,
        model=model_id,
        cost=cost,
    )


@router.get("/health")
async def health():
    has_key = bool(os.environ.get("EMERGENT_LLM_KEY"))
    return {"status": "ok", "engine": "gemini-3.1-flash-image-preview", "key_configured": has_key}


# ═══════════════════════ AI PRODUCT INFO (research + describe) ═══════════════════════
class ProductInfoRequest(BaseModel):
    name: str
    image_base64: Optional[str] = None  # data:image/...;base64,...
    official_url: Optional[str] = None
    lang: str = "ar"  # 'ar' | 'en'


class ProductInfoResponse(BaseModel):
    title: str
    description: str
    features: List[str]
    specs: dict
    benefits: List[str] = []         # فوائد المنتج (مهم للأدوية/المكملات/الأطعمة)
    usage_instructions: List[str] = []  # طريقة الاستخدام خطوة بخطوة
    whats_new: List[str] = []         # الجديد في هذا الإصدار vs السابق (مهم للجوالات)
    comparison: dict = {}             # مقارنة مع الجيل السابق
    side_effects: List[str] = []      # تحذيرات / آثار جانبية (أدوية)
    target_audience: str = ""         # الفئة المستهدفة
    official_url: str = ""            # رابط الموقع الرسمي إن وجد
    colors: list = []
    sizes: list = []
    warranty: dict = {}
    html: str
    cost: int


@router.post("/product-info", response_model=ProductInfoResponse)
async def product_info(req: ProductInfoRequest):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
    if not req.name or len(req.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="name is required")

    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

    lang_instr = "Respond in Arabic" if req.lang == "ar" else "Respond in English"
    sys_msg = (
        f"You are an elite product research expert. {lang_instr}. "
        "When given a product name, optional image, and optional official URL, you conduct DEEP research "
        "(based on the image + name + your knowledge of the product, manufacturer, generation, market positioning) "
        "and return STRICTLY a JSON object with these EXACT fields (ALL fields required; use empty array/string/object if N/A):\n"
        "- title (string, full official product name with model/generation)\n"
        "- description (string, 3-4 polished marketing sentences highlighting positioning + key value)\n"
        "- features (array of 6-10 short bullet strings, each a concrete benefit/capability)\n"
        "- specs (object key→value strings, 6-10 entries with concrete technical specs)\n"
        "- benefits (array of 4-7 strings — health/functional benefits; ESSENTIAL for medicine/supplements/food/skincare)\n"
        "- usage_instructions (array of 3-7 short step strings — how to use the product; ESSENTIAL for medicine/cosmetics/electronics setup)\n"
        "- whats_new (array of 3-6 short strings — what's NEW vs the previous generation/version; ESSENTIAL for phones/laptops/cars)\n"
        "- comparison (object: {previous_model: string, key_differences: [array of strings], upgrades: [array of strings]} — comparison to previous generation; empty object {} if N/A)\n"
        "- side_effects (array of 0-5 strings — warnings/contraindications; ONLY for medicine/supplements, empty otherwise)\n"
        "- target_audience (string — who is this product for, 1 sentence)\n"
        "- official_url (string — best-guess official manufacturer URL like apple.com, royalcanin.com, samsung.com; empty string if unsure)\n"
        "- colors (array of {name, hex} objects — available colors; empty if N/A)\n"
        "- sizes (array of strings — sizes/capacities; empty if N/A)\n"
        "- warranty (object {duration_text, url}; both can be empty strings)\n"
        "Output ONLY the JSON object, no markdown, no code fences."
    )
    user_parts = [f"Product name: {req.name.strip()}"]
    if req.official_url:
        user_parts.append(f"Official URL: {req.official_url.strip()}")
    user_parts.append("Generate the JSON now.")
    user_text = "\n".join(user_parts)

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"prodinfo-{uuid.uuid4().hex[:10]}",
            system_message=sys_msg,
        )
        # Use Gemini (multimodal-capable, fast)
        chat.with_model("gemini", "gemini-2.5-flash")
        msg = UserMessage(text=user_text)
        if req.image_base64 and req.image_base64.startswith("data:"):
            # Extract mime + base64 data
            try:
                head, b64 = req.image_base64.split(",", 1)
                mime = head.split(";")[0].split(":")[1]
                msg.file_contents = [ImageContent(image_base64=b64)]
            except Exception:
                pass
        result_text = await chat.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI research failed: {str(e)[:200]}")

    # Parse JSON from response
    import json as _json
    text = (result_text or "").strip()
    # Strip code fences if any
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text[3:] else text
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        data = _json.loads(text)
    except Exception:
        # Best-effort extract
        import re as _re
        m = _re.search(r"\{.*\}", text, _re.DOTALL)
        if m:
            try:
                data = _json.loads(m.group(0))
            except Exception:
                raise HTTPException(status_code=502, detail="AI returned non-JSON")
        else:
            raise HTTPException(status_code=502, detail="AI returned non-JSON")

    title = str(data.get("title", req.name)).strip()
    description = str(data.get("description", "")).strip()
    features = [str(f).strip() for f in (data.get("features") or []) if str(f).strip()][:10]
    specs = {str(k): str(v) for k, v in (data.get("specs") or {}).items()}
    benefits = [str(b).strip() for b in (data.get("benefits") or []) if str(b).strip()][:7]
    usage_instructions = [str(u).strip() for u in (data.get("usage_instructions") or []) if str(u).strip()][:7]
    whats_new = [str(w).strip() for w in (data.get("whats_new") or []) if str(w).strip()][:6]
    comparison = data.get("comparison") or {}
    side_effects = [str(s).strip() for s in (data.get("side_effects") or []) if str(s).strip()][:5]
    target_audience = str(data.get("target_audience", "")).strip()
    official_url_resp = str(data.get("official_url", req.official_url or "")).strip()
    colors = data.get("colors") or []
    sizes = [str(s) for s in (data.get("sizes") or [])][:8]
    warranty = data.get("warranty") or {"duration_text": "", "url": ""}
    # Build a clean HTML rendering for direct insertion
    html_parts = [
        f"<h2 style='font-size:18px;font-weight:900;margin-bottom:8px;color:#0a0a0a'>{title}</h2>",
        f"<p style='font-size:13px;line-height:1.8;color:#374151;margin-bottom:12px'>{description}</p>",
    ]
    if features:
        html_parts.append("<h3 style='font-size:14px;font-weight:900;margin:12px 0 6px;color:#7c3aed'>المميزات الرئيسية</h3><ul style='padding-inline-start:18px;margin-bottom:12px'>" +
                          "".join(f"<li style='font-size:12px;line-height:1.8;color:#0a0a0a;margin-bottom:3px'>{f}</li>" for f in features) + "</ul>")
    if specs:
        html_parts.append("<h3 style='font-size:14px;font-weight:900;margin:12px 0 6px;color:#7c3aed'>المواصفات</h3><div style='display:grid;grid-template-columns:1fr 1fr;gap:6px'>" +
                          "".join(f"<div style='background:#faf5ff;border-radius:8px;padding:8px'><b style='display:block;font-size:10px;color:#7c3aed'>{k}</b><span style='font-size:12px;color:#0a0a0a'>{v}</span></div>" for k, v in specs.items()) + "</div>")
    if req.official_url:
        html_parts.append(f"<p style='font-size:11px;margin-top:14px'><a href='{req.official_url}' target='_blank' style='color:#7c3aed'>الرابط الرسمي ↗</a></p>")

    return ProductInfoResponse(
        title=title,
        description=description,
        features=features,
        specs=specs,
        benefits=benefits,
        usage_instructions=usage_instructions,
        whats_new=whats_new,
        comparison=comparison,
        side_effects=side_effects,
        target_audience=target_audience,
        official_url=official_url_resp,
        colors=colors,
        sizes=sizes,
        warranty=warranty,
        html="".join(html_parts),
        cost=10,
    )

