"""V4: triangle composition with EXTREME facial accuracy focus on younger son (Abbas)."""
import asyncio
import os
import base64
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")
api_key = os.getenv("EMERGENT_LLM_KEY")

with open("/app/logo_gen/real_both_night.jpg", "rb") as f:
    father_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_father.jpg", "rb") as f:
    sons_night_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_son_solo.jpg", "rb") as f:
    sons_mall_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_both_mall.jpg", "rb") as f:
    son_juice_b64 = base64.b64encode(f.read()).decode("utf-8")

REF_DESCRIPTION = (
    "REFERENCE PHOTOS PROVIDED (4 photos):\n"
    "Photo 1 (FATHER): bearded adult man, wearing yellow hoodie, RIMLESS HALF-RIM METALLIC GOLD/SILVER EYEGLASSES "
    "(top frame visible, bottom rimless), short dark hair, round face, full dark beard, medium skin tone.\n"
    "Photo 2 (BOTH SONS AT NIGHT): TWO boys.\n"
    "  - LEFT boy = HUSSEIN (older, ~10 yrs): VERY messy/wild curly dark hair (voluminous), wider face, "
    "    bigger smile showing teeth, slightly bigger build, wearing white t-shirt with car graphic.\n"
    "  - RIGHT boy = ABBAS (younger, ~7-8 yrs): SHORTER and TIDIER curly hair (less voluminous), "
    "    SMALLER and ROUNDER face, smaller features, chubby cheeks, wearing teal green hoodie with smiley face graphic, "
    "    making thumbs-up gesture, distinctly YOUNGER and SMALLER than Hussein.\n"
    "Photo 3 (BOTH SONS AT MALL): same two boys. Hussein on left with white car t-shirt, Abbas on right with green smiley hoodie.\n"
    "Photo 4 (SOLO): the young boy drinking juice with backpack - same Abbas (younger one).\n"
)

CRITICAL_RULES = (
    "\nABSOLUTE CRITICAL RULES:\n"
    "1. ABBAS (younger son) MUST look DISTINCTLY YOUNGER, SMALLER, with ROUNDER chubbier face, "
    "   TIDIER less-voluminous curly hair, SMALLER eyes than Hussein. NOT a clone of his older brother. "
    "   He has baby-like soft features.\n"
    "2. HUSSEIN (older son) has WILDER messier voluminous curly hair, a LONGER face, BIGGER smile.\n"
    "3. The two boys must look CLEARLY DIFFERENT - one is noticeably younger than the other.\n"
    "4. The FATHER must wear the EXACT rimless half-rim metallic eyeglasses from photo 1.\n"
    "5. Father has FULL DARK BEARD, short dark hair, round face.\n"
    "6. Casual modern clothes (hoodies/T-shirts), NO traditional thobe.\n"
    "7. Faces must be RECOGNIZABLE as these specific real people in anime style.\n"
)

COMPOSITION = (
    "\nCOMPOSITION: Square 1:1 logo with TRIANGLE arrangement of three anime portraits. "
    "Father portrait at TOP CENTER. Hussein (older, messier hair) at BOTTOM LEFT. Abbas (younger, smaller, rounder face) at BOTTOM RIGHT. "
    "Each face is a clear, detailed anime portrait. "
    "Background: solid deep emerald green circular badge with subtle gold geometric Saudi-inspired border. "
    "Detailed anime style, clean line art, vibrant cel-shading. All three smiling happily, facing forward. "
    "Premium PWA app icon look."
)

VARIATIONS = {
    "triangle_v4a": REF_DESCRIPTION + CRITICAL_RULES + COMPOSITION + 
        "\nStyle emphasis: very expressive anime eyes that reflect each person's individual character. "
        "Abbas's eyes should be larger and rounder (child-like sparkle), Hussein's slightly narrower (older kid). "
        "Father's eyes calm and warm behind the glasses.",
    
    "triangle_v4b": REF_DESCRIPTION + CRITICAL_RULES + COMPOSITION + 
        "\nStyle emphasis: more semi-realistic anime (Makoto Shinkai feel) preserving real facial proportions. "
        "Make Abbas's face notably smaller and rounder than Hussein's. The age difference must be visually clear. "
        "Soft shading and detailed hair textures showing distinct curl patterns for each boy.",
    
    "triangle_v4c": REF_DESCRIPTION + CRITICAL_RULES + COMPOSITION + 
        "\nStyle emphasis: bold modern shonen anime art (sharp lineart, vibrant colors). "
        "Exaggerate the age difference: Abbas should look distinctly like a small kid (~7yrs), Hussein like a pre-teen (~11yrs). "
        "Different curl/hair textures, different face widths, different expressions.",
}


async def gen(name: str, prompt: str):
    print(f"[{name}] starting...", flush=True)
    chat = LlmChat(
        api_key=api_key,
        session_id=f"zenrex-v4-{name}",
        system_message="You are an expert anime portrait illustrator. Your priority is making distinct individual people RECOGNIZABLE from reference photos. Each person must look like themselves, not generic anime characters.",
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
    results = await asyncio.gather(*[gen(n, p) for n, p in VARIATIONS.items()])
    print("DONE:", results, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
