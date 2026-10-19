# -*- coding: utf-8 -*-
r"""JET2.BIN 전체 → TIM2 텍스처 PNG (2026-10-19)
  python tools/dump_tex.py → work/tex/<블록번호>_<항목>_<TIM2위치hex>_<그림>.png · work/tex/list.tsv
  항목 안 어디든 'TIM2' 가 있으면 그 자리부터 읽음(모델 묶음 속 텍스처 포함)."""
import os, re, sys, pickle
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import cmp3, tim2

OUT = os.path.join(ROOT, 'work', 'tex'); os.makedirs(OUT, exist_ok=True)
offs = cmp3.blocks(); offs.append(cmp3.SIZE)
f = open(cmp3.ISO, 'rb'); rows = []; ent = []
for k in range(len(offs) - 1):
    f.seek(cmp3.BASE + offs[k]); blk = f.read(offs[k + 1] - offs[k])
    if blk[16:20] == b'CMP3':
        es, _ = cmp3.entries(blk)
    else:
        es = [(16, len(blk) - 16, blk[16:])]
    for j, (p, n, d) in enumerate(es):
        ent.append((k, offs[k], j, p, n, d[:4].hex()))
        for m in re.finditer(b'TIM2', d):
            t = m.start()
            try:
                pics = tim2.pictures(d[t:])
            except Exception as e:
                continue
            for q, (w, h, bpp, img, ip, cp) in enumerate(pics):
                if not (0 < w <= 2048 and 0 < h <= 2048): continue
                nm = '%04d_%02d_%06X_%d.png' % (k, j, t, q)
                try: Image.fromarray(img, 'RGBA').save(os.path.join(OUT, nm))
                except Exception: continue
                rows.append((nm, k, hex(offs[k]), j, hex(t), q, w, h, bpp))
    if k % 200 == 0:
        print(k, len(offs) - 1, len(rows), flush=True)
with open(os.path.join(OUT, 'list.tsv'), 'w', encoding='utf-8') as w:
    for r in rows: w.write('\t'.join(map(str, r)) + '\n')
with open(os.path.join(ROOT, 'work', 'jet2_entries.tsv'), 'w', encoding='utf-8') as w:
    for r in ent: w.write('\t'.join(map(str, r)) + '\n')
print('텍스처', len(rows), '항목', len(ent))
