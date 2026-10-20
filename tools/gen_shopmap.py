# -*- coding: utf-8 -*-
r"""매장 지도 작은 라벨 → work/gfx/gfx_shoplabel.tsv  (원고 work/shop/labels.tsv: 블록<TAB>상자 x0,y0,x1,y1<TAB>한글(⏎ 두 줄)<TAB>[a=각도 강제])
  상자 안 회색·검정 글자 화소(표시점 ● 제외)로 회전 사각형을 구해 그 각도·길이로 다시 씀. 지도마다 지우기 줄을 먼저 다 두고 그리기 줄
"""
import os, sys, cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'shop', 'labels.tsv'); OUT = os.path.join(ROOT, 'work', 'gfx', 'gfx_shoplabel.tsv')


def isdot(m):
    """표시점 ● = 볼록(solidity ≥ 0.9)하고 꽉 찬(≥ 0.7) 둥근 덩어리 — ョ·ロ 같은 글자는 아님"""
    import cv2
    ys, xs = np.nonzero(m); pts = np.stack([xs, ys], 1).astype(np.int32)
    hull = cv2.convexHull(pts); ha = max(1.0, cv2.contourArea(hull) + len(hull) / 2)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max(); s = set(zip(xs.tolist(), ys.tolist()))
    corners = sum((x, y) in s for x in (x0, x1) for y in (y0, y1))   # 원은 네 모서리가 빔(ョ 같은 꽉 찬 글자는 모서리가 참)
    return corners == 0 and len(xs) / ha >= 0.9 and len(xs) >= 0.7 * (np.ptp(xs) + 1) * (np.ptp(ys) + 1)



def textmask(a, blue=False):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]; lum = a.sum(-1) // 3
    m = ((lum < 200) & (np.abs(r - b) < 40) & (np.abs(r - g) < 40)).astype(np.uint8)
    if blue: m = ((b > 150) & (r < 170) & (b - r > 40)).astype(np.uint8)
    n, l, s, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    for i in range(1, n):
        w_, h_, ar = s[i, 2], s[i, 3], s[i, 4]
        if 6 <= w_ <= 10 and 6 <= h_ <= 10 and abs(w_ - h_) <= 1 and isdot(l == i): m[l == i] = 0
    return m


import shoplabels
DET = {}
rows = {}
for l in open(SRC, encoding='utf-8'):
    if l.startswith('#') or not l.strip(): continue
    f = l.rstrip('\n').split('\t'); b = int(f[0]); text = f[2]
    if f[1].startswith('#'): ids = [int(v) for v in f[1][1:].split('+')]; box = (0, 0, 0, 0)
    else: ids = None; box = tuple(map(int, f[1].split(',')))
    opt = dict(kv.split('=', 1) for kv in (f[3].split(';') if len(f) > 3 and f[3] else []))
    rows.setdefault(b, []).append((box, ids, text, opt))
out = ['#그림\t상자\t한글\t꼴 — 매장 지도 작은 라벨(gen_shopmap.py, 원고 work/shop/labels.tsv). 지우기(poly) 먼저 → 회전 그리기(rot)']
for b, ls in sorted(rows.items()):
    DET[b] = shoplabels.detect(b)[1]
    a = np.asarray(Image.open(os.path.join(ROOT, 'work', 'gs', '%d_00_000.png' % b)).convert('RGB')).astype(int); M = textmask(a)
    er, dr = [], []
    for (x0, y0, x1, y1), ids, text, opt in ls:
        if ids is not None:                     # #번호+번호 = shoplabels.py 검출 덩어리
            xs = np.concatenate([DET[b][i][10] for i in ids]); ys = np.concatenate([DET[b][i][11] for i in ids])
            if float(opt.get('a', '1')) == 0 and 'nx' not in opt:   # 가로 라벨: 같은 줄에서 바로 옆(8 px 안)에 붙은 글자 덩어리도 넣음(목록에서 빠진 조각)
                n_, lab_, st_, cen_ = cv2.connectedComponentsWithStats(M, connectivity=8)
                X0, X1, Y0, Y1 = xs.min() - 8, xs.max() + 8, ys.min() - 1, ys.max() + 1
                for _ in range(3):
                    add = [i for i in range(1, n_) if st_[i, 0] <= X1 and st_[i, 0] + st_[i, 2] >= X0 and Y0 <= cen_[i][1] <= Y1 and st_[i, 3] <= Y1 - Y0 + 3]
                    sel = np.isin(lab_, add); yy, xx = np.nonzero(sel)
                    if len(xx): xs = np.concatenate([xs, xx]); ys = np.concatenate([ys, yy])
                    X0, X1 = xs.min() - 8, xs.max() + 8
        else:
            n_, lab_, st_, cen_ = cv2.connectedComponentsWithStats(cv2.dilate(M, np.ones((2, 2), np.uint8)), connectivity=8)
            keep = [i for i in range(1, n_) if x0 <= cen_[i][0] < x1 and y0 <= cen_[i][1] < y1]   # 중심이 상자 안인 덩어리만
            ys, xs = np.nonzero(np.isin(lab_, keep) & (M > 0))
            if 'raw' in opt:                    # 상자 안 글자 화소 그대로(붙어 있는 이웃 줄 덩어리를 자를 때)
                ys, xs = np.nonzero(M[y0:y1, x0:x1]); xs = xs + x0; ys = ys + y0
            if 'bl' in opt:                     # 파란 글자: 상자 안 파랑 화소 전부
                MB = textmask(a, True); nb, lb = cv2.connectedComponents(MB, connectivity=8)
                inb = np.zeros_like(MB, bool); inb[y0:y1, x0:x1] = True
                out_ = np.unique(lb[~inb & (MB > 0)]); sel = (MB > 0) & inb & ~np.isin(lb, out_)   # 상자 테두리(칸 밖으로 이어짐) 제외
                ys, xs = np.nonzero(sel)
        if len(xs) < 5: print('글자 없음', b, x0, y0, text); continue
        (cx, cy), (w, h), ang = cv2.minAreaRect(np.stack([xs, ys], 1).astype(np.float32))
        if w < h: w, h, ang = h, w, ang + 90
        while ang > 90: ang -= 180
        while ang <= -90: ang += 180
        if 'a' in opt: ang = float(opt['a'])
        th = np.radians(ang); ux, uy = np.cos(th), np.sin(th)          # 그 각도 축으로 투영해 길이·두께·중심
        p = xs * ux + ys * uy; q = -xs * uy + ys * ux
        w, h = p.max() - p.min() + 1, q.max() - q.min() + 1; pc, qc = (p.max() + p.min()) / 2, (q.max() + q.min()) / 2
        cx, cy = pc * ux - qc * uy + float(opt.get('dx', '0')), pc * uy + qc * ux + float(opt.get('dy', '0'))
        pts = cv2.boxPoints(((cx, cy), (w + 3, h + 3), ang))
        poly = '|'.join('%d,%d' % (round(px), round(py)) for px, py in pts)
        bx0, by0 = max(0, int(pts[:, 0].min()) - 3), max(0, int(pts[:, 1].min()) - 3)
        bx1, by1 = min(a.shape[1], int(pts[:, 0].max()) + 4), min(a.shape[0], int(pts[:, 1].max()) + 4)
        n = text.count('⏎') + 1; T = int(opt.get('h', h + 2)); L = int(opt.get('w', w + 4))
        er.append('%d_00_000\t%d,%d,%d,%d\t\tfill=#000000;edge=none;shadow=0;erase=poly;th=200;ir=2;bgfill=1;poly=%s%s' % (b, bx0, by0, bx1, by1, poly, (';red=1' if 'r' in opt else '') + (';blue=1' if 'bl' in opt else '')))
        dr.append('%d_00_000\t%d,%d,%d,%d\t%s\tfill=%s;edge=none;shadow=0;erase=none;align=c;font=eb;size=%s;lh=%d;rot=%.1f;cx=%.1f;cy=%.1f;L=%d;T=%d' % (
            b, bx0, by0, bx1, by1, text, opt.get('c', '#2a2a2a'), opt.get('s', str(max(8, min(12, int(h // n) + 1)))), int(T // n), ang, cx, cy, L, T))
    out += er + dr
open(OUT, 'w', encoding='utf-8').write('\n'.join(out) + '\n'); print(OUT, len(out) - 1)
