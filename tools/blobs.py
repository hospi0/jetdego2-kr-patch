# -*- coding: utf-8 -*-
r"""아틀라스 그림의 글자 덩어리(라벨) 상자 — 불투명 화소를 가로로 gap px 이어 붙인 연결 요소 (2026-10-20)
  python tools/blobs.py <그림> [gap=7] [x0 y0 x1 y1]"""
import os, sys
import numpy as np, cv2
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def blobs(name, gap=7, roi=None):
    a = np.asarray(Image.open(os.path.join(ROOT, 'work', 'gs', name + '.png')).convert('RGBA'))
    m = (a[..., 3] > 40).astype(np.uint8)
    if roi:
        x0, y0, x1, y1 = roi; mm = np.zeros_like(m); mm[y0:y1, x0:x1] = m[y0:y1, x0:x1]; m = mm
    k = cv2.dilate(m, np.ones((3, gap), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(k)
    out = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if w * h < 40: continue
        out.append((y, x, x, y, x + w, y + h))
    return [o[2:] for o in sorted(out)]


if __name__ == '__main__':
    gap = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    roi = tuple(map(int, sys.argv[3:7])) if len(sys.argv) > 6 else None
    for b in blobs(sys.argv[1], gap, roi): print('%d,%d,%d,%d' % b)
