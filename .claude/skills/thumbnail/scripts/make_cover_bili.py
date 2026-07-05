#!/usr/bin/env python
"""B站 16:9 封面合成（设计版，给 Cos 跳舞用）。

不是"白字压渐变"的廉价字幕条，而是：
  人物主体居一侧 + 虚化氛围底 + 超大粗描边标题 + 身份标签色块。
高级感来自：文字最大最突出、强描边对比、克制的元素、从画面取的点缀色。

用法:
  python make_cover_bili.py --frame 高光帧.jpg --tag "俄国萝莉" --title "和服宅舞" \
      --out cover_bili.png [--accent "#E63946"] [--subject right|left] [--size 1280x720]
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"   # 微软雅黑 Bold


def fit_cover(img, size):
    """缩放裁切填满 size（不留边）。"""
    tw, th = size
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    img2 = img.resize((int(sw * scale) + 1, int(sh * scale) + 1), Image.LANCZOS)
    x = (img2.width - tw) // 2
    y = (img2.height - th) // 2
    return img2.crop((x, y, x + tw, y + th))


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def fit_font(text, max_w, max_size, min_size=48):
    """挑最大的、能让最长行宽 ≤ max_w 的字号。"""
    for s in range(max_size, min_size, -4):
        f = ImageFont.truetype(FONT_BOLD, s)
        w = f.getbbox(text)[2] - f.getbbox(text)[0]
        if w <= max_w:
            return f, s
    return ImageFont.truetype(FONT_BOLD, min_size), min_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", required=True)
    ap.add_argument("--tag", default="俄国萝莉", help="身份标签（色块里）")
    ap.add_argument("--title", required=True, help="主标题（\\n 手动换行，否则自动）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--accent", default="#E63946", help="点缀色（标签底色）")
    ap.add_argument("--subject", choices=["right", "left"], default="right")
    ap.add_argument("--size", default="1280x720")
    args = ap.parse_args()

    W, H = (int(x) for x in args.size.lower().split("x"))
    accent = hex2rgb(args.accent)
    frame = Image.open(args.frame).convert("RGB")

    # 1) 氛围底：虚化+压暗的整帧填满 16:9
    bg = fit_cover(frame, (W, H)).filter(ImageFilter.GaussianBlur(28))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    canvas = Image.blend(bg, dark, 0.45).convert("RGBA")

    # 2) 人物主体：竖帧按高度铺满，贴在一侧，带柔和投影
    subj_h = H
    subj_w = int(frame.width * subj_h / frame.height)
    subj = frame.resize((subj_w, subj_h), Image.LANCZOS)
    if args.subject == "right":
        sx = W - subj_w
    else:
        sx = 0
    # 投影
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle([sx - 30, 0, sx + subj_w + 30, H], fill=(0, 0, 0, 120))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(25)))
    canvas.paste(subj, (sx, 0))
    # 主体内侧加一道渐变，让文字区与人物自然过渡
    grad_w = 220
    grad = Image.new("RGBA", (grad_w, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(grad_w):
        a = int(160 * (1 - i / grad_w)) if args.subject == "right" else int(160 * (i / grad_w))
        gd.line([(i, 0), (i, H)], fill=(0, 0, 0, a))
    gx = sx - grad_w if args.subject == "right" else sx + subj_w
    canvas.alpha_composite(grad, (gx, 0))

    # 3) 文字区：标签色块 + 超大粗描边主标题
    draw = ImageDraw.Draw(canvas)
    text_left = 70 if args.subject == "right" else (W - subj_w) + 70
    text_w = (sx - 70) - text_left if args.subject == "right" else (W - 70) - text_left

    # 标签 pill
    tag = args.tag.strip()
    if tag:
        tag_font = ImageFont.truetype(FONT_BOLD, 46)
        tb = tag_font.getbbox(tag)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        pad = 22
        pill = [text_left, 70, text_left + tw + pad * 2, 70 + th + pad * 2]
        draw.rounded_rectangle(pill, radius=16, fill=accent + (255,))
        draw.text((text_left + pad - tb[0], 70 + pad - tb[1]), tag, font=tag_font, fill=(255, 255, 255, 255))
        title_top = pill[3] + 40
    else:
        title_top = 90

    # 主标题：自动换行 + 自适应字号 + 粗描边
    title = args.title.replace("\\n", "\n")
    if "\n" in title:
        lines = title.split("\n")
    else:
        # 4字以内一行；超过按一半折行
        lines = [title] if len(title) <= 5 else [title[:len(title)//2], title[len(title)//2:]]
    longest = max(lines, key=len)
    font, fsize = fit_font(longest, text_w, max_size=150)
    line_gap = int(fsize * 0.18)
    stroke = max(8, fsize // 14)
    y = title_top
    for ln in lines:
        bb = font.getbbox(ln)
        lh = bb[3] - bb[1]
        draw.text((text_left - bb[0], y - bb[1]), ln, font=font,
                  fill=(255, 255, 255, 255), stroke_width=stroke, stroke_fill=(26, 26, 26, 255))
        y += lh + line_gap

    canvas.convert("RGB").save(args.out, "PNG")
    print(f"[ok] B站封面({W}x{H}) 字号{fsize} -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
