"""Generate 4 different anime-style PWA logos featuring father + 2 sons in Khaleeji attire."""
import asyncio
import os
import base64
import sys
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")
api_key = os.getenv("EMERGENT_LLM_KEY")

# Load reference images
with open("/app/logo_gen/father.jpg", "rb") as f:
    father_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/son1.jpg", "rb") as f:
    son1_b64 = base64.b64encode(f.read()).decode("utf-8")
with open("/app/logo_gen/son2.jpg", "rb") as f:
    son2_b64 = base64.b64encode(f.read()).decode("utf-8")

STYLES = {
    "ghibli": (
        "Studio Ghibli inspired anime style logo. A warm, gentle anime portrait of a "
        "bearded Saudi Arabian father in white thobe with red-and-white checkered shemagh and black agal, "
        "standing protectively behind his two young sons (around 7 and 9 years old), both also in white thobes "
        "and red-checkered ghutras. They look like the people in the reference photos but in soft Ghibli anime style. "
        "Warm desert sunset background with palm trees in the distance, gold and amber tones, soft watercolor texture. "
        "Square 1:1 composition. Family love, heritage, warmth. Headshot composition focused on faces and shoulders."
    ),
    "modern": (
        "Modern vibrant anime style logo, like My Hero Academia or Demon Slayer character art. "
        "Heroic portrait of a Saudi Arabian father (bearded, white thobe, red-checkered shemagh with black agal) "
        "with his two sons (around 7 and 9 years old in matching white thobes and red ghutras) standing in front of him, "
        "all looking confidently forward. Faces should resemble the reference photos. "
        "Bold clean line art, vibrant saturated colors, dramatic lighting, slight cel-shading. "
        "Simple geometric circular background in deep emerald green and gold. Square 1:1 composition. Bust shot."
    ),
    "chibi": (
        "Cute chibi anime style mascot logo. Three adorable chibi characters: a bearded father (smiling) in white thobe "
        "with red-checkered ghutra and black agal, and his two young sons (huge sparkly eyes, big smiles, around 7-9 years old) "
        "in matching mini white thobes and red ghutras. Faces inspired by the reference photos. "
        "All three standing together waving. Soft pastel circular background, kawaii style, rounded shapes, bright happy colors. "
        "Perfect for a kids app icon. Square 1:1 composition. Full body chibi proportions."
    ),
    "minimalist": (
        "Minimalist flat anime / vector illustration style logo. Clean stylized portrait of a Saudi Arabian father "
        "with neat beard, white thobe and red-checkered shemagh, alongside his two young sons in matching attire "
        "(around 7 and 9 years old). Faces inspired by reference photos but heavily stylized and simplified. "
        "Flat colors, no gradients, bold outlines. Solid royal blue circular badge background with subtle gold border. "
        "Looks like a premium app icon. Square 1:1. Bust composition with smiling faces."
    ),
}


async def gen(style_name: str, prompt: str):
    print(f"[{style_name}] starting...", flush=True)
    chat = LlmChat(
        api_key=api_key,
        session_id=f"zenrex-logo-{style_name}",
        system_message="You are a master anime illustrator creating PWA app icons.",
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
            for i, img in enumerate(images):
                out_path = f"/app/logo_gen/logo_{style_name}.png"
                with open(out_path, "wb") as f:
                    f.write(base64.b64decode(img["data"]))
                print(f"[{style_name}] saved -> {out_path}", flush=True)
                return out_path
        else:
            print(f"[{style_name}] NO IMAGES returned. Text: {text[:200]}", flush=True)
    except Exception as e:
        print(f"[{style_name}] ERROR: {e}", flush=True)
    return None


async def main():
    tasks = [gen(name, prompt) for name, prompt in STYLES.items()]
    results = await asyncio.gather(*tasks)
    print("\nDONE. Results:", results, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
