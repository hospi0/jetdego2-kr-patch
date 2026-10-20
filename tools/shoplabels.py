# -*- coding: utf-8 -*-
r"""매장 지도(3067~3084) 작은 라벨 검출 — 어두운 글자 화소를 단어로 묶어 회전 사각형(중심·각도·길이·두께) + 번호 그림
  python tools/shoplabels.py <블록…> → work/shop/<블록>_det.png(번호), work/shop/<블록>_det.tsv
"""
import os, sys, cv2, numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', 'shop'); os.makedirs(OUT, exist_ok=True)
MAP = (62, 156, 498, 372)                     # 지도 판(보라 테두리 안) 대략


def isdot(m):
    """표시점 ● = 볼록(solidity ≥ 0.9)하고 꽉 찬(≥ 0.7) 둥근 덩어리 — ョ·ロ 같은 글자는 아님"""
    import cv2
    ys, xs = np.nonzero(m); pts = np.stack([xs, ys], 1).astype(np.int32)
    hull = cv2.convexHull(pts); ha = max(1.0, cv2.contourArea(hull) + len(hull) / 2)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max(); s = set(zip(xs.tolist(), ys.tolist()))
    corners = sum((x, y) in s for x in (x0, x1) for y in (y0, y1))   # 원은 네 모서리가 빔(ョ 같은 꽉 찬 글자는 모서리가 참)
    return corners == 0 and len(xs) / ha >= 0.9 and len(xs) >= 0.7 * (np.ptp(xs) + 1) * (np.ptp(ys) + 1)



def rect(xs, ys):
    pts = np.stack([xs, ys], 1).astype(np.float32)
    (cx, cy), (w, h), ang = cv2.minAreaRect(pts)
    if w < h: w, h, ang = h, w, ang + 90
    while ang > 90: ang -= 180
    while ang <= -90: ang += 180
    return (cx, cy, w + 2, h + 2, ang)


def detect(b):
    a = np.asarray(Image.open(os.path.join(ROOT, 'work', 'gs', '%d_00_000.png' % b)).convert('RGB')).astype(int)
    r, g, bl = a[..., 0], a[..., 1], a[..., 2]
    lum = a.sum(-1) // 3
    dark = (lum < 170) & (np.abs(r - bl) < 40) & (np.abs(r - g) < 40)              # 검정·진회색 글자(파랑 BLUE SKY·빨강 표시점 제외)
    red = (r > 180) & (g < 90) & (bl < 90)                  # 빨강 글자(JAL 등)
    out = []
    for col, mm in (('dark', dark), ('red', red)):
        m = mm.astype(np.uint8)
        x0, y0, x1, y1 = MAP; z = np.zeros_like(m); z[y0:y1, x0:x1] = m[y0:y1, x0:x1]; m = z
        n0, l0, s0, _ = cv2.connectedComponentsWithStats(m, connectivity=8)     # 표시점 ●(꽉 찬 둥근 덩어리) 빼기
        for i in range(1, n0):
            w_, h_, ar = s0[i, 2], s0[i, 3], s0[i, 4]
            if 6 <= w_ <= 10 and 6 <= h_ <= 10 and abs(w_ - h_) <= 1 and isdot(l0 == i): m[l0 == i] = 0
        n, lab, st, cen = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((2, 2), np.uint8)), connectivity=8)
        for i in range(1, n):
            ys, xs = np.nonzero((lab == i) & (m > 0))
            if len(xs) < 6: continue
            out.append(rect(xs, ys) + (col, int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1, xs, ys))
    return a, sorted(out, key=lambda t: (t[1] // 20, t[0]))


if __name__ == '__main__':
    for b in map(int, sys.argv[1:]):
        a, ls = detect(b)
        im = Image.fromarray(a.astype(np.uint8)).crop((MAP[0], MAP[1], MAP[2], MAP[3])); im = im.resize((im.width * 3, im.height * 3), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        with open(os.path.join(OUT, '%d_det.tsv' % b), 'w', encoding='utf-8') as f:
            for k, (cx, cy, w, h, ang, col, bx0, by0, bx1, by1, _, _) in enumerate(ls):
                f.write('%d\t%.1f\t%.1f\t%.1f\t%.1f\t%.1f\t%s\t%d,%d,%d,%d\n' % (k, cx, cy, w, h, ang, col, bx0, by0, bx1, by1))
                X, Y = (bx0 - MAP[0]) * 3, (by0 - MAP[1]) * 3
                d.rectangle(((bx0 - MAP[0]) * 3, (by0 - MAP[1]) * 3, (bx1 - MAP[0]) * 3, (by1 - MAP[1]) * 3), outline=(0, 200, 0) if col == 'dark' else (255, 140, 0))
                d.text((X, Y - 10), str(k), fill=(255, 0, 255))
        im.save(os.path.join(OUT, '%d_det.png' % b)); print(b, len(ls))
