"""Generate v3 - real photos, casual outfits, father MUST have glasses."""
import asyncio
import os
import base64
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")
api_key = os.getenv("EMERGENT_LLM_KEY")

# Correct mapping (verified):
# WA0000 (real_both_night.jpg, 111KB) = FATHER (yellow hoodie, glasses, beard)
# WA0003 (real_father.jpg, 56KB) = Both sons together at night (peace signs)
# WA0004 (real_son_solo.jpg, 67KB) = Both sons on couch at mall
# WA0001 (real_both_mall.jpg, 54KB) = Single son with juice/backpack

with open("/app/logo_gen/real_both_night.jpg", "rb") as f:
    father_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_father.jpg", "rb") as f:
    sons_night_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_son_solo.jpg", "rb") as f:
    sons_mall_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_both_mall.jpg", "rb") as f:
    son_juice_b64 = base64.b64encode(f.read()).decode("utf-8")


SHARED = (
    "I am providing 4 reference photos. "
    "Photo 1: The FATHER - bearded man, wearing a yellow hoodie, with rimless metallic eyeglasses (half-rim style, "
    "metallic gold/silver frames on top, frameless on bottom), short dark hair, round face, medium skin tone. "
    "Photo 2 & 3: Both SONS together - two boys aged ~7-11, with dark curly hair (one slightly more wavy), brown eyes, "
    "happy smiles, medium skin tone, casual modern kids clothes (NOT traditional thobes - they wear T-shirts and hoodies). "
    "Photo 4: One of the sons solo with curly hair drinking juice. "
    "\n\nCRITICAL INSTRUCTIONS:\n"
    "1. The father MUST wear the EXACT same rimless/half-rim metallic eyeglasses from the reference photo. This is non-negotiable.\n"
    "2. The father has a FULL DARK BEARD and short dark hair - match exactly.\n"
    "3. Both sons have curly dark hair, medium-light skin tones, happy bright faces.\n"
    "4. ALL THREE wear CASUAL MODERN CLOTHES (hoodies, T-shirts) - NO traditional Saudi thobe or ghutra.\n"
    "5. The faces must be RECOGNIZABLE as these specific real people - same face shapes, same eye shapes, same noses.\n"
    "6. Style: anime art style, but the people must clearly look like the references.\n"
)

STYLES = {
    "triangle_v3": (
        SHARED +
        "\nCOMPOSITION: Square 1:1 portrait logo with three anime-style portraits arranged in a TRIANGLE - "
        "father at the TOP center, two sons side-by-side at the bottom. Each face is a clear anime portrait. "
        "Background: solid deep emerald green circular badge with subtle gold geometric border (Saudi-inspired). "
        "Detailed anime style with clean line art and vibrant cel-shading. "
        "Father wearing yellow hoodie. Sons wearing colorful modern kid hoodies/tees. "
        "ALL THREE smiling happily, facing forward. Premium app icon look."
    ),
    "shinkai_v3": (
        SHARED +
        "\nSTYLE: Makoto Shinkai semi-realistic anime (Your Name, Weathering With You). "
        "Highly detailed faces preserving real likeness. Warm golden hour lighting. Cinematic. "
        "COMPOSITION: Square 1:1. Father standing in center-back smiling, his two sons side-by-side in front. "
        "All in casual modern clothes (father yellow hoodie + glasses, sons in T-shirts/hoodies). "
        "Soft warm sunset background with subtle bokeh. Bust/half-body shot. Faces must be 90% photorealistic anime."
    ),
    "modern_logo_v3": (
        SHARED +
        "\nSTYLE: Modern vibrant anime logo (think shonen anime character art - sharp clean lineart, cel-shaded). "
        "COMPOSITION: Square 1:1 family portrait. Father in center holding both shoulders of his sons who stand on either side. "
        "Father wearing yellow hoodie + the metallic half-rim glasses. Sons in casual modern hoodies. "
        "Background: clean circular gradient (deep blue to gold) with subtle starry pattern. "
        "All smiling with confident expressions. Detailed faces clearly recognizable. Bust shot."
    ),
}


async def gen(name: str, prompt: str):
    print(f"[{name}] starting...", flush=True)
    chat = LlmChat(
        api_key=api_key,
        session_id=f"zenrex-v3-{name}",
        system_message="You are an expert anime illustrator who captures EXACT facial likeness from photographs. People MUST be recognizable.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    msg = UserMessage(
        text=prompt,
        file_contents=[
            ImageContent(father_b64),
            ImageContent(sons_night_b64),
            ImageContent(sons_mall_b64),
            ImageContent(son_juice_b64),
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
