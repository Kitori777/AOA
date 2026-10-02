from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "AOA" / "assets" / "brand"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        Path("C:/Windows/Fonts/seguisb.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def build_png() -> Image.Image:
    size = 512
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((16, 16, 496, 496), radius=104, fill="#071b2b")
    draw.rounded_rectangle(
        (24, 24, 488, 488), radius=96, outline="#164866", width=10
    )

    # A rising production/optimization path: input -> decision -> optimal output.
    points = [(104, 238), (214, 174), (310, 212), (408, 112)]
    draw.line(points, fill="#36c7f4", width=28, joint="curve")
    for index, (x, y) in enumerate(points):
        radius = 30 if index in (0, 3) else 24
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill="#0d79d5" if index < 3 else "#42d69a",
            outline="#eaf8ff",
            width=9,
        )
    draw.polygon([(390, 92), (438, 96), (430, 144)], fill="#42d69a")

    font = _font(132)
    text = "AOA"
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text(((size - width) / 2, 292), text, font=font, fill="#f4fbff")
    draw.rounded_rectangle((106, 439, 406, 451), radius=6, fill="#0d79d5")
    return image


def build_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect x="16" y="16" width="480" height="480" rx="104" fill="#071b2b"/>
  <rect x="24" y="24" width="464" height="464" rx="96" fill="none" stroke="#164866" stroke-width="10"/>
  <path d="M104 238 L214 174 L310 212 L408 112" fill="none" stroke="#36c7f4" stroke-width="28" stroke-linecap="round" stroke-linejoin="round"/>
  <g stroke="#eaf8ff" stroke-width="9">
    <circle cx="104" cy="238" r="30" fill="#0d79d5"/>
    <circle cx="214" cy="174" r="24" fill="#0d79d5"/>
    <circle cx="310" cy="212" r="24" fill="#0d79d5"/>
    <circle cx="408" cy="112" r="30" fill="#42d69a"/>
  </g>
  <path d="M390 92 L438 96 L430 144 Z" fill="#42d69a"/>
  <text x="256" y="408" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-weight="700" font-size="132" fill="#f4fbff">AOA</text>
  <rect x="106" y="439" width="300" height="12" rx="6" fill="#0d79d5"/>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    image = build_png()
    image.save(OUT / "aoa_logo.png", optimize=True)
    image.save(
        OUT / "aoa.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    (OUT / "aoa_logo.svg").write_text(build_svg(), encoding="utf-8")


if __name__ == "__main__":
    main()
