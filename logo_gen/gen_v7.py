"""V7: Father in white thobe + ghutra, sons in casual modern hoodies (like approved style)."""
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
with open("/app/logo_gen/father.jpg", "rb") as f:
    thobe_ref_b64 = base64.b64encode(f.read()).decode("utf-8")


PROMPT = (
    "I am providing 4 reference images:\n\n"
    "Image 1 (PRIMARY STYLE REFERENCE): The APPROVED anime art style + triangle composition + "
    "natural background + playful hand gestures. KEEP EVERYTHING from this image EXCEPT swap only the father's clothing.\n\n"
    "Image 2 (FATHER FACE): The father with RIMLESS HALF-RIM METALLIC eyeglasses and full dark beard.\n\n"
    "Image 3 (SONS FACES): Two boys ~7-11 with dark curly hair, similar size, look like brothers.\n\n"
    "Image 4 (THOBE REFERENCE): Shows a Saudi man in traditional WHITE THOBE with RED-AND-WHITE checkered "
    "GHUTRA (shemagh) and BLACK AGAL (cord). Use exactly this attire for the FATHER ONLY.\n\n"
    "===========================================\n"
    "CRITICAL INSTRUCTIONS:\n"
    "1. FATHER: dress him in TRADITIONAL SAUDI ATTIRE — white thobe + red-and-white checkered ghutra + black agal "
    "   (match Image 4). Keep his RIMLESS METALLIC GLASSES on. Keep his full dark beard. NO yellow hoodie.\n"
    "2. SONS (both Hussein and Abbas): Keep them wearing their CASUAL MODERN HOODIES exactly as in Image 1 — "
    "   colorful modern kids hoodies/T-shirts. NO traditional thobe for the kids. They wear normal casual clothes.\n"
    "3. ABBAS (right side son): Slightly slimmer/narrower face compared to Hussein, but same body size. "
    "   Slim down the cheeks a bit.\n"
    "4. HUSSEIN (left side son): Slightly fuller rounder face than Abbas.\n"
    "5. KEEP the same triangle composition (father center, sons flanking).\n"
    "6. KEEP the warm Saudi desert sunset background with palm trees from Image 1.\n"
    "7. KEEP the playful hand gestures (peace sign / thumbs up) and joyful smiles.\n"
    "8. KEEP the same anime art style — clean lineart, vibrant cel-shading.\n"
    "9. Square 1:1 composition, bust/half-body shot.\n"
    "10. So the final look: father in TRADITIONAL THOBE+GHUTRA+GLASSES standing between two sons in CASUAL HOODIES."
)


async def gen(name: str, prompt: str):
    print(f"[{name}] starting...", flush=True)
    chat = LlmChat(
        api_key=api_key,
        session_id=f"zenrex-v7-{name}",
        system_message="You are an expert anime illustrator. Apply ONLY the clothing change to the father while preserving everything else from the reference image.",
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
            ImageContent(thobe_ref_b64),
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
    VARIATIONS = {
        "v7_thobe_dad_a": PROMPT,
        "v7_thobe_dad_b": PROMPT + "\nVariation B: very natural anime expression on father (soft warm smile, gentle eyes).",
        "v7_thobe_dad_c": PROMPT + "\nVariation C: father with a wider proud smile, showing slight teeth, looking warm and happy.",
    }
    results = await asyncio.gather(*[gen(n, p) for n, p in VARIATIONS.items()])
    print("DONE:", results, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
