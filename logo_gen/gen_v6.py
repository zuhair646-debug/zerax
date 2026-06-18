"""V6: Same approved style + Saudi traditional thobes + glasses + slimmer Abbas face + nature."""
import asyncio
import os
import base64
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")
api_key = os.getenv("EMERGENT_LLM_KEY")

# Style reference (approved triangle layout with nature background)
with open("/app/logo_gen/style_ref.png", "rb") as f:
    style_b64 = base64.b64encode(f.read()).decode("utf-8")
# Father face (with glasses)
with open("/app/logo_gen/real_both_night.jpg", "rb") as f:
    father_face_b64 = base64.b64encode(f.read()).decode("utf-8")
# Both sons casual reference (for face features)
with open("/app/logo_gen/real_father.jpg", "rb") as f:
    sons_face_b64 = base64.b64encode(f.read()).decode("utf-8")
# Traditional thobe reference (kid in thobe)
with open("/app/logo_gen/son1.jpg", "rb") as f:
    thobe1_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/son2.jpg", "rb") as f:
    thobe2_b64 = base64.b64encode(f.read()).decode("utf-8")


PROMPT = (
    "I am providing 5 reference images:\n\n"
    "Image 1 (STYLE REFERENCE): This is the APPROVED anime art style, composition, and quality. "
    "Keep the SAME triangle composition (father top center, two sons at bottom flanking him), "
    "SAME anime art style, SAME face design language, SAME natural outdoor background style, "
    "SAME playful joyful mood with hand gestures.\n\n"
    "Image 2 (FATHER FACE): Bearded man with RIMLESS HALF-RIM METALLIC eyeglasses, full dark beard, "
    "short dark hair, medium skin tone. Keep his exact glasses and beard.\n\n"
    "Image 3 (SONS FACES): Two boys ~7-11 years old, dark curly hair, brown eyes. "
    "Same height/size. They look like brothers.\n\n"
    "Images 4 & 5 (TRADITIONAL CLOTHING REFERENCE): These show kids wearing TRADITIONAL SAUDI ATTIRE — "
    "a clean WHITE THOBE (long traditional robe with collar) and a RED-AND-WHITE CHECKERED GHUTRA "
    "(shemagh headdress) held by a BLACK AGAL (cord). Use this exact clothing for the family.\n\n"
    "===========================================\n"
    "CRITICAL CHANGES from Image 1:\n"
    "1. CLOTHING: Dress ALL THREE (father + two sons) in TRADITIONAL SAUDI ATTIRE — "
    "   white thobe + red-and-white checkered ghutra + black agal. Father wears the same thobe + ghutra. "
    "   NO yellow hoodie. NO casual hoodies. ALL traditional matching Saudi outfits.\n"
    "2. FATHER KEEPS HIS RIMLESS HALF-RIM METALLIC GLASSES (very important — keep glasses ON even with thobe).\n"
    "3. FATHER KEEPS HIS FULL DARK BEARD.\n"
    "4. ABBAS (the boy on the RIGHT in the approved image — the one previously in green hoodie): "
    "   Make his face SLIGHTLY SLIMMER and more elongated, less round/chubby. Keep his body size the same as his brother. "
    "   Just slim down the face/cheeks a bit so he looks more like the slender boy in the reference photo (Image 3 right side).\n"
    "5. HUSSEIN (the boy on the LEFT): Keep his face roundness, slightly fuller cheeks than Abbas.\n"
    "6. Both boys clearly look like BROTHERS but with subtle differences in face shape.\n"
    "7. KEEP NATURAL OUTDOOR BACKGROUND (warm Saudi desert at golden hour sunset with palm trees and dunes — "
    "   matches Image 1).\n"
    "8. KEEP PLAYFUL HAND GESTURES — older boy peace sign, younger boy thumbs up, father warm smile.\n"
    "9. Square 1:1 composition. Bust shot. All smiling and joyful.\n"
    "10. Same anime art style as Image 1 — clean lineart, vibrant cel-shading, premium quality."
)

VARIATIONS = {
    "v6_thobe_sunset": PROMPT,
    "v6_thobe_palm_grove": PROMPT + "\n\nVARIATION: Background should be a beautiful Saudi palm-tree grove at warm sunset, with the orange/pink sky visible through palm leaves.",
    "v6_thobe_oasis": PROMPT + "\n\nVARIATION: Background should be a Saudi desert oasis — sand dunes in distance, a few palm trees, blue daytime sky with soft clouds, vibrant and crisp.",
}


async def gen(name: str, prompt: str):
    print(f"[{name}] starting...", flush=True)
    chat = LlmChat(
        api_key=api_key,
        session_id=f"zenrex-v6-{name}",
        system_message="You are an expert anime illustrator. Faithfully apply requested changes (clothing swap, face slimming, background) while preserving the established art style and character designs from the reference image.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    msg = UserMessage(
        text=prompt,
        file_contents=[
            ImageContent(style_b64),
            ImageContent(father_face_b64),
            ImageContent(sons_face_b64),
            ImageContent(thobe1_b64),
            ImageContent(thobe2_b64),
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
