"""V8: Father in white thobe (NO ghutra), normal hair + glasses, beach/sea background."""
import asyncio
import os
import base64
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")
api_key = os.getenv("EMERGENT_LLM_KEY")

with open("/app/logo_gen/style_ref.png", "rb") as f:
    style_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_both_night.jpg", "rb") as f:
    father_face_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_father.jpg", "rb") as f:
    sons_face_b64 = base64.b64encode(f.read()).decode("utf-8")


PROMPT = (
    "I am providing 3 reference images:\n\n"
    "Image 1 (STYLE REFERENCE): The APPROVED anime art style + triangle composition + playful hand gestures. "
    "Keep the same composition, art style, and joyful mood.\n\n"
    "Image 2 (FATHER FACE): Bearded man with RIMLESS HALF-RIM METALLIC eyeglasses, short dark hair (NO headdress in the photo), "
    "full dark beard, medium skin tone, slightly round face.\n\n"
    "Image 3 (SONS FACES): Two boys ~7-11 with dark curly hair, similar size.\n\n"
    "===========================================\n"
    "CRITICAL INSTRUCTIONS:\n"
    "1. FATHER: dress in a clean WHITE TRADITIONAL SAUDI THOBE (long white robe with collar, no headdress). "
    "   IMPORTANT: NO ghutra, NO shemagh, NO agal — just the thobe with his head bare, showing his short dark hair styled naturally. "
    "   KEEP his RIMLESS HALF-RIM METALLIC GLASSES. KEEP his full dark beard. KEEP his natural short dark hair (visible on top).\n"
    "2. SONS (Hussein and Abbas): Wearing CASUAL MODERN HOODIES (colorful kids hoodies/T-shirts) just like in Image 1.\n"
    "3. ABBAS (right side): Slightly slimmer/narrower face than Hussein. Same body size as his brother.\n"
    "4. HUSSEIN (left side): Slightly fuller rounder face than Abbas.\n"
    "5. KEEP the triangle composition (father top/center, sons flanking).\n"
    "6. NEW BACKGROUND: BEAUTIFUL BEACH / SEA scene in anime style — calm turquoise/blue sea, soft waves, "
    "   golden sand beach, warm sunset sky with gentle clouds and warm orange/pink light. "
    "   Optional: a couple of palm trees on the edges. Very serene and gorgeous.\n"
    "7. KEEP playful hand gestures (peace sign / thumbs up) and joyful smiles.\n"
    "8. KEEP the same anime art style — clean lineart, vibrant cel-shading.\n"
    "9. Square 1:1 composition, bust/half-body shot."
)

VARIATIONS = {
    "v8_beach_sunset": PROMPT,
    "v8_beach_daytime": PROMPT + "\nVARIATION: Background is a bright daytime beach — clear blue sky with white fluffy clouds, vivid turquoise sea, golden sand, cheerful and sunny.",
    "v8_beach_palms": PROMPT + "\nVARIATION: Background is a tropical beach with tall palm trees on both sides, calm sea behind, soft golden-hour light, dreamy atmosphere.",
}


async def gen(name: str, prompt: str):
    print(f"[{name}] starting...", flush=True)
    chat = LlmChat(
        api_key=api_key,
        session_id=f"zenrex-v8-{name}",
        system_message="You are an expert anime illustrator. Preserve the established character designs and art style while applying the requested changes (remove ghutra, show natural hair, change background to beach).",
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
