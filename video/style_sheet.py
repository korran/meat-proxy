#!/usr/bin/env python3
"""Combine style_lab.py renders into one labelled contact sheet.

  python3 video/style_sheet.py video/build/style kevin flat,toy,lowpoly
"""
import sys

from PIL import Image, ImageDraw, ImageFont

folder, prefix, styles = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
labels = {"flat": "1  FLAT GRAPHIC", "toy": "2  VINYL TOY", "lowpoly": "3  LOW-POLY", "brick": "4  BRICK-BUILT"}
imgs = [Image.open(f"{folder}/{prefix}_{s}.png").convert("RGB") for s in styles]
w, h = imgs[0].size
pad, bar = 24, 90
sheet = Image.new("RGB", (len(imgs) * w + (len(imgs) + 1) * pad, h + bar + 2 * pad), (6, 8, 18))
font = ImageFont.truetype("/usr/share/fonts/opentype/bebas-neue/BebasNeue-Regular.otf", 64)
d = ImageDraw.Draw(sheet)
for i, (s, im) in enumerate(zip(styles, imgs)):
    x = pad + i * (w + pad)
    sheet.paste(im, (x, pad + bar))
    d.text((x, pad + 8), labels.get(s, s.upper()), font=font, fill=(240, 240, 235))
out = f"{folder}/{prefix}_styles.png"
sheet.save(out)
print(out)
