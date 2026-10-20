# -*- coding: utf-8 -*-
r"""기체 앨범 설명 상자(2782~2899 _00_002) — work/gfx/src_album2.txt → work/gfx/gfx_album2.tsv
  파란 바탕 흰 글자, 줄 간격 24, 위에서부터. 지우는 칸 = 원문 줄 수와 번역 줄 수 중 큰 쪽(work/def/panels.tsv). 폭 넘침 알림
"""
import os, re
from PIL import ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = ImageFont.truetype(r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf', 18)
P = ',.!?:;)\'"~、。，．！？：；）」』】〉》”’…‥・·～〜♪♥'
n0 = {l.split('\t')[0][:4]: int(l.split('\t')[1]) for l in open(os.path.join(ROOT, 'work', 'def', 'panels.tsv'))}
rows = ['#그림\t상자\t한글\t꼴 — 기체 앨범 설명 상자 94장(gen_album2.py, 원고 src_album2.txt)']; bad = 0
for l in open(os.path.join(ROOT, 'work', 'gfx', 'src_album2.txt'), encoding='utf-8'):
    if l.startswith('#') or not l.strip(): continue
    b, t = l.rstrip('\n').split('\t'); lines = t.split('⏎')
    for ln in lines:
        w = F.getlength(re.sub('([' + re.escape(P) + '])[ 　]+', r'\1', ln))
        if w > 612: print('폭 넘침', b, int(w), ln); bad += 1
    n = max(n0[b], len(lines))
    if n > 7: print('줄 넘침', b, n); bad += 1
    rows.append('%s_00_002\t16,18,632,%d\t%s\tfill=#ffffff;edge=none;shadow=0;erase=fill;align=l;font=b;size=18;lh=24' % (b, 18 + 24 * n, '⏎'.join(lines + [' '] * (n - len(lines)))))
open(os.path.join(ROOT, 'work', 'gfx', 'gfx_album2.tsv'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
print(len(rows) - 1, '줄 · 문제', bad)
