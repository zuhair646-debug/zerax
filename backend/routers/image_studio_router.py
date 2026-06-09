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
