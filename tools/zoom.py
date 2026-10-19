# -*- coding: utf-8 -*-
r"""그림 일부 확대 저장(읽기용) — python tools/zoom.py <그림> x0 y0 x1 y1 [배율=2] → work/z_t.png"""
import os, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
n = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); k = float(sys.argv[6]) if len(sys.argv) > 6 else 2
p = os.path.join(ROOT, 'work', 'gs', n + '.png')
if not os.path.exists(p): p = os.path.join(ROOT, 'work', 'gfx', 'prev_' + n + '.png')
im = Image.open(p).convert('RGBA'); bg = Image.new('RGBA', im.size, (60, 60, 90, 255)); bg.alpha_composite(im)
bg.crop((x0, y0, x1, y1)).resize((int((x1 - x0) * k), int((y1 - y0) * k)), Image.LANCZOS).convert('RGB').save(os.path.join(ROOT, 'work', 'z_t.png'))
