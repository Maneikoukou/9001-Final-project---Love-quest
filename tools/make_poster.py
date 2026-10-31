"""
Development helper (not part of the submitted game)
===================================================

Requires Pillow.  Only used to build the Padlet cover image.

Composes the Padlet cover image out of real in-game renders, so the picture
on the board is genuinely what the program looks like.

    python3 tools/render_preview.py      # produces the shots first
    python3 tools/make_poster.py
"""

import os

from PIL import Image, ImageDraw, ImageFont

SRC = "/tmp/lq_preview"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "padlet_cover.png")

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"

W, H = 1200, 780


def gradient(size, top, bottom):
    img = Image.new("RGB", size, top)
    d = ImageDraw.Draw(img)
    t = tuple(int(top[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(bottom[i:i + 2], 16) for i in (1, 3, 5))
    for y in range(size[1]):
        k = y / (size[1] - 1)
        d.line([(0, y), (size[0], y)],
               fill=tuple(int(t[i] + (b[i] - t[i]) * k) for i in range(3)))
    return img


def heart(draw, cx, cy, r, fill):
    import math
    pts = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((cx + x * r / 16, cy - y * r / 16))
    draw.polygon(pts, fill=fill)


def card(base, path, box, radius=18):
    """Paste a screenshot with a white frame and a soft shadow."""
    shot = Image.open(path).convert("RGB")
    x, y, w, h = box
    shot = shot.resize((w, h), Image.LANCZOS)

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([x - 4, y + 8, x + w + 4, y + h + 16], radius + 6,
                         fill=(90, 60, 90, 46))
    shadow = shadow.filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"]).GaussianBlur(10))
    base.alpha_composite(shadow)

    frame = Image.new("RGBA", (w + 16, h + 16), (255, 255, 255, 255))
    mask = Image.new("L", (w + 16, h + 16), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w + 15, h + 15], radius + 6, fill=255)
    frame.putalpha(mask)
    base.alpha_composite(frame, (x - 8, y - 8))

    inner = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    imask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(imask).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    inner.paste(shot, (0, 0))
    inner.putalpha(imask)
    base.alpha_composite(inner, (x, y))


def main():
    base = gradient((W, H), "#FFE9F2", "#DCEBFF").convert("RGBA")
    d = ImageDraw.Draw(base)

    # floating hearts in the background
    for i, (hx, hy, r) in enumerate(((120, 150, 16), (1080, 120, 13),
                                     (60, 420, 11), (1140, 380, 15),
                                     (180, 700, 12), (1010, 690, 14))):
        heart(d, hx, hy, r, "#FFC2D6")

    title = ImageFont.truetype(FONT_BOLD, 82)
    sub = ImageFont.truetype(FONT_BOLD, 26)
    tag = ImageFont.truetype(FONT_REG, 22)
    small = ImageFont.truetype(FONT_BOLD, 19)

    d.text((W / 2, 92), "LOVE QUEST", font=title, fill="#4A3350", anchor="mm")
    d.text((W / 2, 156), "A  C A S T L E  F O R  T W O", font=sub,
           fill="#A97FA8", anchor="mm")
    d.text((W / 2, 198), "A Python platformer about going the long way round for someone",
           font=tag, fill="#6B5570", anchor="mm")

    card(base, os.path.join(SRC, "03_steppe.png"), (56, 240, 520, 291))
    card(base, os.path.join(SRC, "09_ending.png"), (620, 240, 520, 291))

    d.text((312, 566), "three hand-built levels", font=small, fill="#8A6A80",
           anchor="mm")
    d.text((880, 566), "a proposal at the end", font=small, fill="#8A6A80",
           anchor="mm")

    pill = Image.new("RGBA", (760, 54), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle([0, 0, 759, 53], 26, fill=(255, 255, 255, 235),
                         outline=(240, 215, 228, 255), width=2)
    base.alpha_composite(pill, (220, 610))
    d.text((600, 637), "Pure Python + tkinter  -  no installs, no assets, no libraries",
           font=small, fill="#7A6480", anchor="mm")

    for i, r in enumerate((11, 14, 11)):
        heart(d, 560 + i * 40, 700, r, "#FF7FA5")

    d.text((W / 2, 736), "COMP9001  -  Final Project", font=tag, fill="#B79BB4",
           anchor="mm")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    base.convert("RGB").save(OUT, quality=95)
    print("saved", OUT, base.size)


if __name__ == "__main__":
    main()
