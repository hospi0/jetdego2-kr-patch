# -*- coding: utf-8 -*-
# 기체 제원 카드(0017_03_002~022, 168×336 8bpp) → gfx_spec.tsv (2026-10-20)
# 줄 = 「항목/값」, 항목 글자 폭 ≈ 10.3 px. 항목 칸만 바꾸고(값·/ 그대로) 끝의 단위 名·席 → 명·석(모양 대조로 위치 찾음)
import os
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
LABELS = [(2, '전폭'), (2, '전장'), (2, '전고'), (5, '수평미익 폭'), (2, '주익'), (3, '보조익'), (4, '플랩'), (5, '수평안정판'),
          (4, '순항 속도'), (4, '엔진'), (6, '운항 승무원'), (3, '승객 수')]
ST = 'fill=#f0f0f0;edge=none;shadow=0;erase=fill;align=l;font=b;size=10'
rows = []
for k in range(2, 23, 2):
    name = '0017_03_%03d' % k
    a = np.asarray(Image.open(os.path.join(ROOT, 'work', 'gs', name + '.png')).convert('L')).astype(int)
    m = a[:200] > 150
    ys = np.nonzero(m[:, :160].sum(1) > 0)[0]
    bands = []; s = ys[0]; p = ys[0]
    for y in ys[1:]:
        if y - p > 1: bands.append((s, p)); s = y
        p = y
    bands.append((s, p))
    bands = [b for b in bands if b[1] - b[0] >= 6]
    if len(bands) != 12:
        print(name, '줄 수', len(bands), bands); continue
    x0 = int(np.nonzero(m[bands[0][0]:bands[0][1] + 1].any(0))[0].min())
    for (n, ko), (b0, b1) in zip(LABELS, bands):
        rows.append((name, '%d,%d,%d,%d' % (x0 - 1, b0 - 1, int(round(x0 + n * 10.8)), b1 + 2), ko, ST))
    # 단위: 마지막 두 줄의 맨 끝 글자 모양 → 같은 줄에서 같은 모양 위치 전부
    for (b0, b1), ko in zip(bands[10:], ('명', '석')):
        ln = m[b0:b1 + 1]
        xs = np.nonzero(ln.any(0))[0]; xe = xs.max() + 1
        tpl = ln[:, xe - 10:xe]
        x = x0
        while x < xe - 9:
            if max((np.roll(ln[:, x:x + 10], dy, 0) == tpl).mean() for dy in (-1, 0, 1)) > 0.95:
                rows.append((name, '%d,%d,%d,%d' % (x - 1, b0 - 1, x + 11, b1 + 2), ko, ST.replace('align=l', 'align=c')))
                x += 10
            else:
                x += 1
rows.append(('0017_03_010', '66,177,78,190', '석', ST.replace('align=l', 'align=c')))   # 「268席〜318席」 앞쪽 席(모양이 1 px 달라 대조에서 빠짐)
with open(os.path.join(HERE, 'gfx_spec.tsv'), 'w', encoding='utf-8') as f:
    f.write('#그림\t상자\t한글\t꼴 — 기체 제원 카드(gen_spec.py 로 생성)\n')
    for r in rows: f.write('\t'.join(r) + '\n')
print(len(rows))
