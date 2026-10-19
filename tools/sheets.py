# -*- coding: utf-8 -*-
r"""텍스처 중복 제거 + 모아 보기 시트 (2026-10-19)
  python tools/sheets.py [tex|gs] → work/sheets_<종류>/sheet_NNN.png (칸 아래 파일 이름 앞부분) · work/tex/uniq.tsv
  같은 화소는 첫 것만. 시트는 블록 순."""
import os, hashlib
import numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
SRC = sys.argv[1] if len(sys.argv) > 1 else 'tex'                       # tex(TIM2) · gs(전송 패킷)
TEX = os.path.join(ROOT, 'work', SRC); OUT = os.path.join(ROOT, 'work', 'sheets_' + SRC); os.makedirs(OUT, exist_ok=True)
rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(TEX, 'list.tsv'), encoding='utf-8')]
seen = {}; uniq = []
for r in rows:
    a = np.asarray(Image.open(os.path.join(TEX, r[0])))
    h = hashlib.md5(a.tobytes()).hexdigest()
    if h in seen: continue
    seen[h] = r[0]
    al = a[..., 3]; trans = float((al < 128).mean())
    ncol = len(np.unique(a.reshape(-1, 4), axis=0))
    uniq.append(r + ['%.2f' % trans, str(ncol)])
with open(os.path.join(TEX, 'uniq.tsv'), 'w', encoding='utf-8') as w:
    for r in uniq: w.write('\t'.join(r) + '\n')
CELL = 192; COLS = 8; ROWS = 6
for s in range(0, len(uniq), COLS * ROWS):
    sh = Image.new('RGB', (COLS * CELL, ROWS * (CELL + 12)), (60, 60, 90)); d = ImageDraw.Draw(sh)
    for i, r in enumerate(uniq[s:s + COLS * ROWS]):
        im = Image.open(os.path.join(TEX, r[0])).convert('RGBA'); im.thumbnail((CELL, CELL))
        x, y = (i % COLS) * CELL, (i // COLS) * (CELL + 12)
        bg = Image.new('RGBA', im.size, (60, 60, 90, 255)); bg.alpha_composite(im)
        sh.paste(bg.convert('RGB'), (x, y)); d.text((x + 2, y + CELL), r[0][:14], fill=(255, 255, 0))
    sh.save(os.path.join(OUT, 'sheet_%03d.png' % (s // (COLS * ROWS))))
print('고유', len(uniq), '시트', (len(uniq) + COLS * ROWS - 1) // (COLS * ROWS))
