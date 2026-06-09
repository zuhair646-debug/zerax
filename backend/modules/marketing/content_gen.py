"""AI content generator — Claude for copy + optional Nano Banana for image."""
import os
import json
import random
import logging
from typing import Optional, Dict, Any, List

from emergentintegrations.llm.chat import LlmChat, UserMessage
from .personas import PERSONA_MAP, CONTENT_BUCKETS

logger = logging.getLogger("zitex.marketing.content")

PLATFORM_LIMITS = {
    "twitter": 280,
    "instagram": 2200,
    "telegram": 4096,
    "discord": 2000,
    "linkedin": 3000,
    "email": 5000,
    "whatsapp": 1024,
    "tiktok": 2200,
}


def _pick_bucket() -> Dict[str, Any]:
    total = sum(b["weight"] for b in CONTENT_BUCKETS)
    r = random.uniform(0, total)
    s = 0
    for b in CONTENT_BUCKETS:
        s += b["weight"]
        if r <= s:
            return b
    return CONTENT_BUCKETS[0]


def _build_prompt(persona_id: str, platform: str, bucket: Dict[str, Any], topic_hint: Optional[str] = None) -> str:
    p = PERSONA_MAP[persona_id]
    limit = PLATFORM_LIMITS.get(platform, 1000)
    hashtags = " ".join(p["hashtags"][:3])
    extra = f"\nالموضوع المطلوب: {topic_hint}\n" if topic_hint else ""

    return f"""اكتب منشور تسويقي لـ Zerax (منصة AI سعودية تبني مواقع/تطبيقات/صور/فيديوهات).

الجمهور المستهدف: {p['name']} {p['emoji']}
وصف الجمهور: {p['description']}
الأسلوب: {p['tone']}
أمثلة Hooks: {' | '.join(p['hook_examples'])}

النوع المطلوب: {bucket['name']}
المنصة: {platform} (الحد الأقصى {limit} حرف){extra}

شروط:
- ابدأ بـ hook قوي يجذب الانتباه في أول 10 كلمات
- اللهجة سعودية طبيعية (مش عامية مبالغ فيها، مهنية ودودة)
- استخدم emojis بشكل متوازن (3-5 emojis في المنشور كله)
- اختم بـ CTA واضح يحوّل الناس لـ https://zerax.com
- أضف هاشتاقات: {hashtags}
- مهم: لا تتظاهر أنك منتج آخر. أنت Zerax. شفّاف وفخور بهويتك السعودية.

أرجع JSON فقط بهذا الشكل بدون أي نص آخر:
{{
  "text": "النص الكامل للمنشور",
  "image_prompt": "وصف بالإنجليزي لصورة احترافية تكمّل المنشور (لو ما يحتاج صورة خله null)",
  "topic": "ملخص قصير 5 كلمات بالعربي",
  "platform_tips": "نصيحة قصيرة لنشره"
}}"""


async def generate_post(
    persona_id: str = "devs",
    platform: str = "twitter",
    topic_hint: Optional[str] = None,
    generate_image: bool = False,
) -> Dict[str, Any]:
    """Generate one marketing post using Claude (text) + optional Nano Banana (image).

    Returns: dict with text, image_prompt, topic, platform_tips, persona, platform, bucket, image_url (if generated).
    """
    if persona_id not in PERSONA_MAP:
        raise ValueError(f"Unknown persona: {persona_id}")

    bucket = _pick_bucket()
    prompt = _build_prompt(persona_id, platform, bucket, topic_hint)

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY missing")

    chat = LlmChat(
        api_key=api_key,
        session_id=f"marketing-{persona_id}-{platform}",
        system_message="أنت كاتب إعلانات احترافي متخصص في السوق السعودي والـ AI. كل ردودك JSON صحيح فقط.",
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    raw = await chat.send_message(UserMessage(text=prompt))

    # Parse JSON (sometimes Claude wraps in markdown)
    text = (raw or "").strip()
    if "```" in text:
        # extract from code fence
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") and part.endswith("}"):
                text = part
                break
    try:
        parsed = json.loads(text)
    except Exception:
        # fallback: treat whole response as text
        parsed = {"text": raw, "image_prompt": None, "topic": "تسويق", "platform_tips": ""}

    image_url = None
    if generate_image and parsed.get("image_prompt"):
        try:
            from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
            img_gen = OpenAIImageGeneration(api_key=api_key)
            images = await img_gen.generate_images(
                prompt=parsed["image_prompt"],
                model="gpt-image-1",
                number_of_images=1,
            )
            if images:
                import secrets
                from pathlib import Path
                out_dir = Path("/app/backend/static/marketing")
                out_dir.mkdir(parents=True, exist_ok=True)
                fname = f"{secrets.token_hex(8)}.png"
                fpath = out_dir / fname
                fpath.write_bytes(images[0])
                image_url = f"/api/static/marketing/{fname}"
        except Exception as e:
            logger.warning(f"image gen failed: {e}")

    return {
        "persona_id": persona_id,
        "persona_name": PERSONA_MAP[persona_id]["name"],
        "platform": platform,
        "bucket": bucket["id"],
        "bucket_name": bucket["name"],
        "text": parsed.get("text", ""),
        "image_prompt": parsed.get("image_prompt"),
        "image_url": image_url,
        "topic": parsed.get("topic", ""),
        "platform_tips": parsed.get("platform_tips", ""),
        "raw_response": raw[:500] if not parsed.get("text") else None,
    }


async def generate_batch(count: int = 5, platforms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Generate `count` posts mixing personas + platforms.

    Useful for filling a queue of upcoming posts to review.
    """
    if platforms is None:
        platforms = ["twitter", "telegram", "instagram", "discord", "email"]

    personas = list(PERSONA_MAP.keys())
    out = []
    for i in range(count):
        persona_id = personas[i % len(personas)]
        platform = platforms[i % len(platforms)]
        try:
            post = await generate_post(persona_id=persona_id, platform=platform, generate_image=False)
            out.append(post)
        except Exception as e:
            logger.exception(f"batch item {i} failed")
            out.append({"error": str(e), "persona_id": persona_id, "platform": platform})
    return out
