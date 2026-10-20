# -*- coding: utf-8 -*-
r"""계기 설명(METER INSTRUCTION, 2879~2886 _00_000) → work/gfx/gfx_meter.tsv
  라벨 = 색 테두리 상자 + 검정 안 + 흰 글자. 흰 글자 덩어리에서 «채도 낮은 화소»로 채워 상자 안쪽을 찾고(테두리가 막음),
  위에서 아래·왼쪽에서 오른쪽 순번으로 원문을 붙임(판독 2026-10-20). 영문(EADI·PFD·ND·ADI·HSI·EHSI)은 그대로.
  상자 안은 통째 검정으로(랜딩 기어 상자 오른쪽 사진 줄 위에도 원문 ー 가 걸쳐 있음). 글자 크기 = 원문 잉크 높이 + 2.
"""
import os, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx
KR = {'ワーニングライト': '경고등', 'コマンドバー': '커맨드 바', '水平儀': '수평의', '高度計': '고도계', '速度計': '속도계',
      '昇降計': '승강계', '目標速度': '목표 속도', '目標高度': '목표 고도', '機首方位': '기수 방위', '方位指示器': '방위 지시기',
      'ランディングギア・レバー': '랜딩 기어⏎레버'}
W, C, H_, T, A, V, S, L, N, D, MS, MA = 'ワーニングライト', 'コマンドバー', '水平儀', '高度計', '速度計', '昇降計', '目標速度', 'ランディングギア・レバー', '機首方位', '方位指示器', '目標速度', '目標高度'
SRC = {2879: ['EADI', C, H_, W, T, A, L, V, N, D, 'EHSI'],
       2880: [W, 'PFD', MS, N, MA, T, L, 'ND', A, C, H_],
       2881: ['EADI', C, H_, W, A, T, V, L, D, N, 'EHSI'],
       2882: [W, 'PFD', MS, N, MA, T, L, 'ND', A, C, H_],
       2883: ['ADI', C, H_, W, A, T, V, D, 'HSI'],
       2884: ['ADI', C, H_, W, A, T, V, L, 'HSI'],
       2885: ['PFD', W, MS, MA, N, T, 'ND', A, C, H_],
       2886: ['ADI', C, H_, W, T, L, A, 'HSI', V]}


def labels(img):
    c = img[..., :3].astype(int)
    free = ((c.max(-1) - c.min(-1)) <= 45).astype(np.uint8)
    wh = (c.min(-1) > 170) & (c.max(-1) - c.min(-1) < 40)
    n, lab, st, _ = cv2.connectedComponentsWithStats(wh.astype(np.uint8))
    rects = set()
    for i in range(1, n):
        if st[i, 4] < 3: continue
        ff = free.copy(); sy, sx = np.argwhere(lab == i)[0]
        cv2.floodFill(ff, np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8), (int(sx), int(sy)), 2)
        ys, xs = np.nonzero(ff == 2)
        r = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        if r[2] - r[0] < 260 and r[3] - r[1] < 70: rects.add(r)
    return sorted(rects, key=lambda r: (r[1], r[0]))


rows = ['#그림\t상자\t한글\t꼴 — 계기 설명 라벨(gen_meter.py)']
for b, src in SRC.items():
    idx, pal, u = gfx.indexed(gfx.entry_data(b, 0), 0); img = pal[idx]; c = img[..., :3].astype(int)
    rs = labels(img)
    assert len(rs) == len(src), (b, len(rs), len(src))
    for (x0, y0, x1, y1), jp in zip(rs, src):
        if jp not in KR: continue
        x0, y0, x1, y1 = x0 + 2, y0 + 2, x1 - 2, y1 - 2      # 채움이 테두리 둘레 어두운 번짐까지 먹음
        sub = c[y0:y1, x0:x1]; lum = sub.sum(-1) // 3
        ink = np.nonzero((lum > 120).any(1))[0]
        k = len(KR[jp].split('⏎')); hgt = (ink.max() - ink.min() + 1) // (2 if '⏎' in KR[jp] or jp == W and y1 - y0 > 30 else 1)
        size = max(12, min(20, int(hgt) + 2))       # 한글 잉크가 같은 px 의 한자보다 작음
        lh = (y1 - y0) // k
        rows.append('%d_00_000\t%d,%d,%d,%d\t%s\tfill=#ffffff;edge=none;shadow=0;erase=fill;align=c;font=eb;size=%d;lh=%d'
                    % (b, x0, y0, x1, y1, KR[jp], size, lh))
open(os.path.join(ROOT, 'work', 'gfx', 'gfx_meter.tsv'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
print(len(rows) - 1, '줄')
