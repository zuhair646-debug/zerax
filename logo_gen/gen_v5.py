"""V5: Build on approved style, add NATURE background + playful hand gestures."""
import asyncio
import os
import base64
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")
api_key = os.getenv("EMERGENT_LLM_KEY")

with open("/app/logo_gen/base_approved.png", "rb") as f:
    base_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_both_night.jpg", "rb") as f:
    father_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_father.jpg", "rb") as f:
    sons_night_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_son_solo.jpg", "rb") as f:
    sons_mall_b64 = base64.b64encode(f.read()).decode("utf-8")


PROMPT_BASE = (
    "REFERENCE IMAGES:\n"
    "Image 1: This is the APPROVED art style — KEEP THIS EXACT anime style, character design, faces, hair, and clothing. "
    "The father in center with yellow hoodie, glasses, beard. Two sons flanking him in colorful hoodies. "
    "Both sons are roughly the SAME SIZE (do NOT make one smaller than the other).\n"
    "Image 2-4: Real reference photos for facial likeness.\n\n"
    "CHANGES NEEDED FROM IMAGE 1:\n"
    "1. REPLACE the solid dark-green background and gold geometric frame with a BEAUTIFUL NATURAL OUTDOOR BACKGROUND "
    "   (anime-style nature scenery: mountains, sky, grass, trees — like a Studio Ghibli landscape).\n"
    "2. Add PLAYFUL HAND GESTURES — the boys should be doing fun cheerful poses (peace sign / thumbs up / waving / "
    "   ok-sign). Make them look JOYFUL and ENERGETIC, not just smiling staticly.\n"
    "3. Slightly DIFFERENTIATE the two boys' facial features — same age and size, but make their features distinct: "
    "   one slightly more curly hair, the other slightly wavier; one slightly rounder face, the other slightly longer. "
    "   They look like brothers but NOT identical twins.\n"
    "4. Keep the father in the center, smiling warmly, wearing the yellow hoodie and rimless half-rim metallic glasses, "
    "   full dark beard. Father can give a subtle smile or thumbs up.\n"
    "5. Keep the same anime art style (clean lineart, cel-shading, vibrant colors).\n"
    "6. Square 1:1 composition. Bust/half-body shot. All three facing forward."
)

VARIATIONS = {
    "v5_desert_sunset": PROMPT_BASE + 
        "\n\nBACKGROUND DETAIL: Warm Saudi desert at golden-hour sunset — sand dunes in distance, "
        "a few palm trees silhouetted, soft orange and pink sky with light clouds, gentle bokeh. "
        "GESTURES: Older boy giving a big peace sign with both hands raised, younger boy giving a happy thumbs-up. "
        "Father giving a warm subtle smile, hand resting on one son's shoulder.",
    
    "v5_green_nature": PROMPT_BASE + 
        "\n\nBACKGROUND DETAIL: Lush green nature scenery in Ghibli style — rolling green hills, soft sky with fluffy clouds, "
        "a tree on the side, sunny daylight. Vibrant and fresh. "
        "GESTURES: Both boys waving cheerfully with one hand and giving peace sign with the other. "
        "Father smiling broadly, doing a gentle thumbs up.",
    
    "v5_sky_clouds": PROMPT_BASE + 
        "\n\nBACKGROUND DETAIL: Beautiful anime sky with fluffy white clouds, soft blue gradient, "
        "rays of warm sunlight breaking through. Dreamy uplifting feel. "
        "GESTURES: Older boy doing an OK sign with one hand and peace with the other, younger boy "
        "raising both arms up cheering. Father chuckling, eyes squinted with joy.",
}


async def gen(name: str, prompt: str):
    print(f"[{name}] starting...", flush=True)
    chat = LlmChat(
        api_key=api_key,
        session_id=f"zenrex-v5-{name}",
        system_message="You are an expert anime illustrator. Maintain the established character design and art style from the approved reference image while applying the requested changes.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    msg = UserMessage(
        text=prompt,
        file_contents=[
            ImageContent(base_b64),  # PRIMARY reference - approved style
            ImageContent(father_b64),
            ImageContent(sons_night_b64),
            ImageContent(sons_mall_b64),
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
    results = await asyncio.gather(*[gen(n, p) for n, p in VARIATIONS.items()])
    print("DONE:", results, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
