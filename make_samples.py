#!/usr/bin/env python3
"""Creates dark placeholder images so the layout can be previewed. Delete the samples afterwards."""
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).parent / "content" / "works"
random.seed(3)


def make(path, w, h, tint):
    im = Image.new("RGB", (w, h), (4, 4, 6))
    d = ImageDraw.Draw(im)
    for _ in range(3):
        x0 = random.randint(0, w // 2)
        d.rectangle([x0, random.randint(0, h // 3), x0 + random.randint(w // 8, w // 3), h], fill=tint)
    im = im.filter(ImageFilter.GaussianBlur(w // 40))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=88)


for name, tint in {"2026-rendering-the-invisible": (120, 60, 200),
                   "2024-blink": (210, 210, 230),
                   "2023-lightshadow": (200, 120, 60)}.items():
    for i, (w, h) in enumerate([(1600, 1000), (1000, 1400), (1600, 900)], 1):
        make(ROOT / name / f"{i:02d}.jpg", w, h, tint)
