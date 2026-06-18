"""Resize approved logo to PWA icon sizes."""
from PIL import Image
import os

SRC = "/app/frontend/public/logo_previews/logo_v9_corniche_evening.png"
OUT_DIR = "/app/logo_gen/final_icons"
os.makedirs(OUT_DIR, exist_ok=True)

img = Image.open(SRC).convert("RGB")
print(f"Source: {img.size}")

# Ensure square - if not, center-crop to square
w, h = img.size
side = min(w, h)
left = (w - side) // 2
top = (h - side) // 2
img_sq = img.crop((left, top, left + side, top + side))
print(f"Square: {img_sq.size}")

# Generate sizes
for size in [192, 512, 1024]:
    resized = img_sq.resize((size, size), Image.LANCZOS)
    out = f"{OUT_DIR}/icon-{size}.png"
    resized.save(out, "PNG", optimize=True)
    print(f"  -> {out} ({os.path.getsize(out)} bytes)")

# Also save a high-quality JPEG master for sharing
img_sq.save(f"{OUT_DIR}/master.jpg", "JPEG", quality=95)
print(f"  -> {OUT_DIR}/master.jpg")
