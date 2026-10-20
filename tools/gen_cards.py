# -*- coding: utf-8 -*-
r"""추천 상품 카드(2904~2999 _00_000) — work/gfx/src_cards.txt → work/gfx/gfx_cards.tsv
  머리 띠 «추천 상품»(3085 와 같은 꼴) + 아래 설명(그러데이션 바탕 → erase=pp, 검정 18 px, 원문 줄 간격). 원문 줄 = work/def/cards.tsv
"""
import os, re
from PIL import ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = ImageFont.truetype(r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf', 18)
P = ',.!?:;)\'"~、。，．！？：；）」』】〉》”’…‥・·～〜♪♥'
C = {}                                                  # 블록 → (원문 줄 수, 첫 줄 위, 끝 줄 아래)
for l in open(os.path.join(ROOT, 'work', 'def', 'cards.tsv')):
    f = l.rstrip('\n').split('\t'); C[f[0]] = tuple(map(int, f[1:4]))
HEAD = 'fill=#ffffff;edge=#3154fe;shadow=1;erase=fill;align=l;font=eb;size=23'
BODY = 'fill=#111111;edge=none;ex0=24;shadow=0;erase=pp;tc=#010101,#3a3c38,#707270;th=120;wt=256;dil=5;dither=1;align=l;font=b;size=18;lh=%d'
rows = ['#그림\t상자\t한글\t꼴 — 추천 상품 카드 96장(gen_cards.py, 원고 src_cards.txt)']; bad = 0
for l in open(os.path.join(ROOT, 'work', 'gfx', 'src_cards.txt'), encoding='utf-8'):
    if l.startswith('#') or not l.strip(): continue
    b, t = l.rstrip('\n').split('\t'); lines = t.split('⏎')
    for ln in lines:
        w = F.getlength(re.sub('([' + re.escape(P) + '])[ 　]+', r'\1', ln))
        if w > 572: print('폭 넘침', b, int(w), ln); bad += 1
    k, y0, y1 = C[b]
    lh = max(20, min(24, round((y1 - y0 + 1 + 6) / k))) if k > 1 else 24
    n = max(k, len(lines)); top = y0 - 4; bot = max(y1 + 4, top + lh * n)
    if bot > 448: print('줄 넘침', b, n, lh); bad += 1
    rows.append('%s_00_000\t86,13,242,47\t추천 상품\t%s' % (b, HEAD))
    rows.append('%s_00_000\t40,%d,612,%d\t%s\t%s' % (b, top, min(448, bot), '⏎'.join(lines + [' '] * (n - len(lines))), BODY % lh))
open(os.path.join(ROOT, 'work', 'gfx', 'gfx_cards.tsv'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
print(len(rows) - 1, '줄 · 문제', bad)
