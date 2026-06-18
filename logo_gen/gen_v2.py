"""Regenerate with STRONG facial likeness emphasis."""
import asyncio
import os
import base64
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")
api_key = os.getenv("EMERGENT_LLM_KEY")

with open("/app/logo_gen/father.jpg", "rb") as f:
    father_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/son1.jpg", "rb") as f:
    son1_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/son2.jpg", "rb") as f:
    son2_b64 = base64.b64encode(f.read()).decode("utf-8")

# Stronger prompts emphasizing EXACT facial match
SHARED_FACE_INSTRUCTION = (
    "CRITICAL: I am providing 3 reference photos. Photo 1 is the father, Photo 2 is the younger son, "
    "Photo 3 is the older son. You MUST replicate their EXACT facial features in anime style: "
    "same face shape, same eye shape and color (dark brown), same nose, same mouth, same eyebrows, "
    "same skin tone, same hair color. The father has a specific beard shape - match it exactly. "
    "The boys have distinct individual faces - DO NOT make them look like generic anime characters. "
    "They must be RECOGNIZABLE as the same people from the photos, just drawn in anime style. "
    "Keep their traditional Saudi attire (white thobe, red-and-white checkered shemagh, black agal). "
)

STYLES = {
    "ghibli_v2": (
        SHARED_FACE_INSTRUCTION +
        "Render in Studio Ghibli anime style: soft watercolor textures, warm gentle lighting, "
        "expressive but realistic anime faces (NOT chibi, NOT cartoony). "
        "Composition: father in center-back, two sons in front, warm desert sunset background with subtle palm silhouettes. "
        "Square 1:1, headshot/bust framing. Faces clearly visible and recognizable."
    ),
    "shonen_v2": (
        SHARED_FACE_INSTRUCTION +
        "Render in modern shonen anime style (like Jujutsu Kaisen or Demon Slayer): "
        "sharp clean lineart, vibrant cel-shaded colors, slightly serious heroic expressions, detailed eyes with highlights. "
        "Realistic anime proportions (NOT chibi). The faces must look like an anime adaptation of the real photos. "
        "Background: deep royal blue circular badge with subtle gold Arabic geometric pattern. "
        "Composition: all three facing forward, bust shot, square 1:1. Faces front-and-center, recognizable."
    ),
    "realistic_anime_v2": (
        SHARED_FACE_INSTRUCTION +
        "Render in semi-realistic anime style (like Makoto Shinkai films - Your Name, Weathering With You): "
        "highly detailed faces preserving real likeness, cinematic lighting, soft skin shading, accurate beard texture on father, "
        "warm natural skin tones. The faces must be 90% photorealistic with a 10% anime touch (large expressive eyes, smooth shading). "
        "Background: warm golden hour Saudi desert with soft bokeh. Square 1:1, bust composition with family side-by-side."
    ),
    "portrait_v2": (
        SHARED_FACE_INSTRUCTION +
        "Render in detailed anime portrait style with HEAVY emphasis on facial likeness. "
        "Three close-up anime portraits arranged in triangle: father at top, two sons below side-by-side. "
        "Each face must be a clear anime portrait of the EXACT person in the reference photo. "
        "Use detailed anime art with realistic proportions, sharp eyes that match each person's actual eye shape. "
        "Solid clean background in deep emerald green with subtle gold border. Square 1:1."
    ),
}


async def gen(name: str, prompt: str):
    print(f"[{name}] starting...", flush=True)
    chat = LlmChat(
        api_key=api_key,
        session_id=f"zenrex-{name}",
        system_message="You are an expert anime illustrator who specializes in capturing exact facial likeness from reference photos. Your goal is to make people recognizable.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    msg = UserMessage(
        text=prompt,
        file_contents=[
            ImageContent(father_b64),
            ImageContent(son1_b64),
            ImageContent(son2_b64),
        ],
    )
    try:
        text, images = await chat.send_message_multimodal_response(msg)
        if images:
            out_path = f"/app/frontend/public/logo_previews/logo_{name}.png"
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(images[0]["data"]))
            print(f"[{name}] OK -> {out_path}", flush=True)
            return name
    except Exception as e:
        print(f"[{name}] FAIL: {str(e)[:200]}", flush=True)
    return None


async def main():
    results = await asyncio.gather(*[gen(n, p) for n, p in STYLES.items()])
    print("DONE:", results, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
