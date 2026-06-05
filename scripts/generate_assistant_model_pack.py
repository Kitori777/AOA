from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    assets_dir = root / "src" / "AOA" / "assets" / "assistant"
    assets_dir.mkdir(parents=True, exist_ok=True)

    src = assets_dir / "alice_white.png"
    if not src.exists():
        raise SystemExit(f"Brak pliku: {src}")

    img = Image.open(src).convert("RGBA")
    size = min(img.size)
    img = ImageOps.fit(img, (size, size), method=Image.Resampling.LANCZOS)

    # Create a moody blue tone to match app palette.
    img = ImageEnhance.Color(img).enhance(0.82)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Brightness(img).enhance(0.94)
    img = img.filter(ImageFilter.GaussianBlur(0.15))
    img.save(src)

    pack_path = assets_dir / "model_pack.json"
    if not pack_path.exists():
        payload = {
            "version": 1,
            "name": "airi-pseudo-live2d",
            "base_image": "alice_white.png",
            "idle": [
                {"rotate": -2.0, "saturation": 0.98, "brightness": 1.0, "dy": 0},
                {"rotate": 0.0, "saturation": 1.0, "brightness": 1.02, "dy": -1},
                {"rotate": 2.0, "saturation": 1.03, "brightness": 1.0, "dy": 0},
                {"rotate": 0.0, "saturation": 1.01, "brightness": 0.99, "dy": 1},
            ],
            "talk": [
                {"rotate": -4.0, "saturation": 1.05, "brightness": 1.03, "dy": -1},
                {"rotate": 0.0, "saturation": 1.08, "brightness": 1.06, "dy": -2},
                {"rotate": 4.0, "saturation": 1.06, "brightness": 1.03, "dy": -1},
                {"rotate": 0.0, "saturation": 1.1, "brightness": 1.07, "dy": -2},
            ],
        }
        pack_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {assets_dir}")


if __name__ == "__main__":
    main()
