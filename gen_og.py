#!/usr/bin/env python3
"""Generate og-image.png (1200×630) for 3H지압침대 안동 구시장센터"""

from PIL import Image, ImageDraw, ImageFont
import os, math

W, H = 1200, 630
BASE = os.path.dirname(os.path.abspath(__file__))

# ── helpers ─────────────────────────────────────────────────────────────────
def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rounded_rect(draw, xy, r, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=width)

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def font(size, bold=False):
    """Try system fonts, fall back gracefully."""
    candidates = [
        '/System/Library/Fonts/AppleSDGothicNeo.ttc',
        '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
        '/Library/Fonts/NanumGothicBold.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

# ── canvas ───────────────────────────────────────────────────────────────────
img = Image.new('RGB', (W, H), (10, 15, 30))
draw = ImageDraw.Draw(img)

# Background gradient (vertical bands via paste)
for x in range(W):
    t = x / W
    c = lerp_color((10, 15, 30), (0, 26, 64), t)
    draw.line([(x, 0), (x, H)], fill=c)

# Decorative blurred circles (simulate glow with soft circles)
glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for r, a in [(220, 18), (180, 22), (120, 28), (70, 35)]:
    gd.ellipse([1050 - r, 80 - r, 1050 + r, 80 + r], fill=(0, 168, 107, a))
for r, a in [(160, 14), (120, 18), (80, 24)]:
    gd.ellipse([1100 - r, 560 - r, 1100 + r, 560 + r], fill=(0, 168, 107, a))
img = Image.alpha_composite(img.convert('RGBA'), glow).convert('RGB')
draw = ImageDraw.Draw(img)

# ── Left accent bar ───────────────────────────────────────────────────────────
for y in range(H):
    t = y / H
    c = lerp_color((0, 200, 120), (0, 120, 70), t)
    draw.line([(0, y), (7, y)], fill=c)

# ── Badge ─────────────────────────────────────────────────────────────────────
rounded_rect(draw, [58, 56, 310, 98], r=22,
             fill=(0, 168, 107, 45), outline=(0, 168, 107, 140), width=1)
draw.ellipse([74, 72, 90, 88], fill=(0, 168, 107))
draw.text((102, 66), '경북 안동 공식 대리점', font=font(16), fill=(255, 255, 255))

# ── Main title ────────────────────────────────────────────────────────────────
draw.text((60, 130), '3H 지압침대', font=font(68), fill=(255, 255, 255))

# Accent gradient text simulation (two-pass)
draw.text((60, 212), '안동 구시장센터', font=font(62), fill=(0, 220, 150))

# Divider
draw.rectangle([60, 292, 150, 297], fill=(0, 168, 107))

# ── Description ───────────────────────────────────────────────────────────────
draw.text((60, 318), '병원 · 한의원 · 노인복지시설 · 기업 B2B 납품 전문', font=font(21), fill=(200, 215, 235))
draw.text((60, 354), '전자세금계산서 발행  ·  전국 납품 가능  ·  경북 안동 직영', font=font(18), fill=(160, 180, 210))

# ── Feature pills ─────────────────────────────────────────────────────────────
pills = [('척추 건강', False), ('수면 개선', False), ('통증 완화', False), ('B2B·B2G', True)]
px = 60
for text, accent in pills:
    tw = draw.textlength(text, font=font(15))
    pw = int(tw) + 34
    bg = (0, 168, 107, 70) if accent else (255, 255, 255, 22)
    ol = (0, 200, 120, 180) if accent else (255, 255, 255, 50)
    pill_img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    pill_d = ImageDraw.Draw(pill_img)
    pill_d.rounded_rectangle([px, 406, px + pw, 444], radius=20, fill=bg, outline=ol, width=1)
    img = Image.alpha_composite(img.convert('RGBA'), pill_img).convert('RGB')
    draw = ImageDraw.Draw(img)
    fc = (0, 230, 160) if accent else (220, 230, 245)
    draw.text((px + 17, 415), text, font=font(15), fill=fc)
    px += pw + 10

# ── Phone card ────────────────────────────────────────────────────────────────
card = Image.new('RGBA', (W, H), (0, 0, 0, 0))
cd = ImageDraw.Draw(card)
cd.rounded_rectangle([58, 472, 460, 554], radius=16,
                     fill=(255, 255, 255, 18), outline=(255, 255, 255, 35), width=1)
img = Image.alpha_composite(img.convert('RGBA'), card).convert('RGB')
draw = ImageDraw.Draw(img)

draw.text((88, 484), '☎', font=font(22), fill=(0, 200, 120))
draw.text((126, 482), '054-858-8561', font=font(28), fill=(255, 255, 255))
draw.text((128, 520), '평일 08:00 ~ 16:00  (주말·공휴일 휴무)', font=font(15), fill=(160, 180, 210))

# ── Product image ──────────────────────────────────────────────────────────────
prod_path = os.path.join(BASE, 'assets', 'noblesse-bed-2.png')
if os.path.exists(prod_path):
    prod = Image.open(prod_path).convert('RGBA')
    iw, ih = prod.size
    area_x, area_y, area_w, area_h = 660, 40, 510, 560
    scale = min(area_w / iw, area_h / ih) * 0.88
    nw, nh = int(iw * scale), int(ih * scale)
    prod = prod.resize((nw, nh), Image.LANCZOS)
    dx = area_x + (area_w - nw) // 2
    dy = area_y + (area_h - nh) // 2
    base_rgba = img.convert('RGBA')
    base_rgba.paste(prod, (dx, dy), prod)
    img = base_rgba.convert('RGB')
    draw = ImageDraw.Draw(img)

# ── Bottom rule + branding ────────────────────────────────────────────────────
draw.line([(60, 575), (W - 60, 575)], fill=(255, 255, 255, 55), width=1)
draw.text((60, 585), '(주)쓰리에이치 경북 안동 공식 대리점', font=font(13), fill=(130, 150, 185))
right_text = '3H지압침대 안동 구시장센터'
rw = draw.textlength(right_text, font=font(13))
draw.text((W - 60 - rw, 585), right_text, font=font(13), fill=(130, 150, 185))

# ── Watermark-style 3H logo text (right top) ──────────────────────────────────
draw.text((1090, 38), '3H', font=font(48), fill=(255, 255, 255, 18))

# ── Save ──────────────────────────────────────────────────────────────────────
out = os.path.join(BASE, 'og-image.png')
img.save(out, 'PNG', optimize=True)
print(f'✅  Saved → {out}  ({img.size[0]}×{img.size[1]})')
