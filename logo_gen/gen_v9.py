"""V9: Father in thobe (no ghutra) + sons casual + Jeddah Corniche background with railing."""
import asyncio
import os
import base64
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")
api_key = os.getenv("EMERGENT_LLM_KEY")

# Use best previous approved version (v8_beach_sunset) as primary style reference
with open("/app/frontend/public/logo_previews/logo_v8_beach_sunset.png", "rb") as f:
    style_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_both_night.jpg", "rb") as f:
    father_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/real_father.jpg", "rb") as f:
    sons_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/jeddah_3c68ce.jpg", "rb") as f:
    jeddah_day_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/jeddah_bdc812.jpg", "rb") as f:
    jeddah_night_b64 = base64.b64encode(f.read()).decode("utf-8")


PROMPT = (
    "I am providing 5 reference images:\n\n"
    "Image 1 (STYLE REFERENCE - PRIMARY): The APPROVED anime art style + triangle composition + characters. "
    "Keep the SAME father (with white thobe, glasses, beard, natural hair), SAME two sons (casual modern hoodies, "
    "playful peace signs and thumbs up gestures), SAME anime art style.\n\n"
    "Image 2 (FATHER FACE REF): bearded man with rimless half-rim metallic glasses.\n\n"
    "Image 3 (SONS FACES REF): two boys ~7-11 with dark curly hair.\n\n"
    "Image 4 & 5 (NEW BACKGROUND REFERENCE — JEDDAH CORNICHE): These show the Jeddah Corniche waterfront promenade "
    "in Saudi Arabia. NOTE the distinctive WHITE METAL RAILING/BARRIER along the seaside walkway (curved wave-like "
    "decorative metal fence). NOTE the palm trees, Red Sea water, modern skyline/buildings in distance.\n\n"
    "===========================================\n"
    "CRITICAL INSTRUCTIONS:\n"
    "1. KEEP everything from Image 1 (characters, art style, gestures, expressions, composition) EXCEPT replace the beach background.\n"
    "2. NEW BACKGROUND: The family is standing AT the Jeddah Corniche waterfront, with the WHITE DECORATIVE METAL "
    "   RAILING/BARRIER visible IN FRONT OF THEM (waist height, curved wave-pattern white metal fence — exactly like "
    "   in Images 4 & 5). Behind the railing is the Red Sea (calm blue water), with palm trees and a soft Jeddah "
    "   waterfront atmosphere. The family stands behind/at the railing posing for a photo with the sea behind them.\n"
    "3. The metal railing should be clearly visible in the foreground (around hip/waist level for the father), "
    "   making it obvious this is the Jeddah Corniche promenade.\n"
    "4. KEEP the father in white thobe + glasses + natural hair + beard (NO ghutra).\n"
    "5. KEEP both sons in their casual hoodies (white t-shirt with car print for older Hussein, green smiley hoodie for younger Abbas).\n"
    "6. KEEP Abbas with the slimmer face (slightly narrower than Hussein).\n"
    "7. KEEP the playful gestures (peace signs, thumbs up) and joyful smiles.\n"
    "8. Square 1:1 anime art style. Bust/half-body composition.\n"
    "9. The railing must be a key recognizable feature — it's what makes it Jeddah Corniche specifically."
)

VARIATIONS = {
    "v9_corniche_sunset": PROMPT + "\n\nLIGHTING: Warm Saudi sunset (golden hour) — soft orange and pink sky over the Red Sea, gentle warm light on the family's faces.",
    "v9_corniche_day": PROMPT + "\n\nLIGHTING: Bright daytime — clear blue sky with a few fluffy clouds, vibrant turquoise Red Sea, sunny and cheerful.",
    "v9_corniche_evening": PROMPT + "\n\nLIGHTING: Early evening twilight — sky transitioning from orange to soft purple-blue, ambient promenade lights starting to glow softly, dreamy and serene.",
}


async def gen(name: str, prompt: str):
    print(f"[{name}] starting...", flush=True)
    chat = LlmChat(
        api_key=api_key,
        session_id=f"zenrex-v9-{name}",
        system_message="You are an expert anime illustrator. Preserve character designs from the primary style reference while changing the background to match the location reference (Jeddah Corniche with white metal railing).",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    msg = UserMessage(
        text=prompt,
        file_contents=[
            ImageContent(style_b64),
            ImageContent(father_b64),
            ImageContent(sons_b64),
            ImageContent(jeddah_day_b64),
            ImageContent(jeddah_night_b64),
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
