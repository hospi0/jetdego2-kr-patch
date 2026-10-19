# -*- coding: utf-8 -*-
r"""그림에서 글자 상자 추정 — 주변 중앙값과 크게 다른 화소 묶음의 경계 (2026-10-20)
  python tools/textbox.py <그림이름> x0 x1 [y0 y1]  → 상자 x0,y0,x1,y1"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def box(name, x0, x1, y0=0, y1=None):
    im = Image.open(os.path.join(ROOT, 'work', 'gs', name + '.png')).convert('RGBA')
    a = np.asarray(im).astype(int); y1 = y1 or a.shape[0]
    med = np.asarray(im.convert('RGB').filter(ImageFilter.MedianFilter(15))).astype(int)
    diff = np.abs(a[..., :3] - med).sum(-1)
    m = (diff > 90) & (a[..., 3] > 40)
    sub = m[y0:y1, x0:x1]; ys, xs = np.nonzero(sub)
    if not len(xs): return None
    return (x0 + xs.min() - 2, y0 + ys.min() - 2, x0 + xs.max() + 3, y0 + ys.max() + 3)


if __name__ == '__main__':
    a = [int(v) for v in sys.argv[2:]]
    print(sys.argv[1], ','.join(map(str, box(sys.argv[1], *a))))
