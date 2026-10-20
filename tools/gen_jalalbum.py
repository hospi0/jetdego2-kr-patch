# -*- coding: utf-8 -*-
r"""JAL 역사 앨범(3088~3128) 그림 표 생성 — work/gfx/src_jalalbum.txt → work/gfx/gfx_jalalbum.tsv
  아래 설명(파란 글자 잉크 13 px = 나눔고딕 볼드 14, 줄 간격 18) 또는 오른쪽 설명 + 필름 띠 세로 글자 昭·和·年 → 쇼·와·년(숫자는 원본)
  python tools/gen_jalalbum.py  (폭 넘치는 줄·줄 수 넘침을 알림)
"""
import os, re
from PIL import ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'gfx', 'src_jalalbum.txt')
OUT = os.path.join(ROOT, 'work', 'gfx', 'gfx_jalalbum.tsv')
FONT = ImageFont.truetype(r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf', 14)
P = ',.!?:;)\'"~、。，．！？：；）」』】〉》”’…‥・·～〜♪♥'
LH = 18
BOTTOM = (115, 319, 632, 8)                       # x0, y0, x1, 최대 줄 수
SIDE = {3091: (382, 64, 9), 3101: (383, 64, 9), 3104: (428, 54, 13), 3106: (382, 64, 11), 3108: (428, 54, 12),
        3112: (428, 54, 12), 3116: (382, 64, 10), 3119: (428, 54, 11), 3123: (382, 64, 10)}   # 아래 사진·구름 전까지
TXT = 'fill=#061481;edge=none;shadow=0;erase=inpaint;align=l;font=b;size=14;lh=18'
ERA = [('쇼', '27,347,55,373'), ('와', '27,375,55,401'), ('년', '65,404,93,431')]
ERA_ST = 'fill=#ffffff;edge=none;shadow=0;erase=fill;align=c;font=m;size=21'

rows = ['#그림\t상자\t한글\t꼴 — JAL 역사 앨범 41장(gen_jalalbum.py 로 생성, 원고 src_jalalbum.txt)']
bad = 0
for l in open(SRC, encoding='utf-8'):
    if l.startswith('#') or not l.strip(): continue
    b, n0, text = l.rstrip('\n').split('\t'); b = int(b); n0 = int(n0)
    lines = text.split('⏎')
    if b in SIDE:
        x0, y0, nmax = SIDE[b]; x1 = 634
    else:
        x0, y0, x1, nmax = BOTTOM
    for ln in lines:
        w = FONT.getlength(re.sub('([' + re.escape(P) + '])[ 　]+', r'\1', ln))
        if w > x1 - x0 - 4:
            print('폭 넘침', b, int(w), '>', x1 - x0 - 4, ln); bad += 1
    if len(lines) > nmax:
        print('줄 넘침', b, len(lines), '>', nmax); bad += 1
    n = max(n0, len(lines))                        # 지우는 칸은 원문 줄까지, 글은 위부터
    rows.append('%d_00_000\t%d,%d,%d,%d\t%s\t%s' % (b, x0, y0, x1, y0 + LH * n, '⏎'.join(lines + [''] * (n - len(lines))), TXT))
    for ch, box in ERA:
        rows.append('%d_00_000\t%s\t%s\t%s' % (b, box, ch, ERA_ST))
open(OUT, 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
print(OUT, len(rows) - 1, '줄 · 문제', bad)
