# -*- coding: utf-8 -*-
r"""PCSX2 GS.bin(VRAM 4 MB) 읽기 — PSMT4/PSMT8/PSMCT32 스위즐 풀기 (2026-10-19)
  python tools/gsmem.py <work/mem/이름> → <이름>/vram4.png (PSMT4, dbw 16 = 1024 폭 통째)"""
import os, sys
import numpy as np
from PIL import Image

B4 = [0, 2, 8, 10, 1, 3, 9, 11, 4, 6, 12, 14, 5, 7, 13, 15, 16, 18, 24, 26, 17, 19, 25, 27, 20, 22, 28, 30, 21, 23, 29, 31]
_r0 = [0, 1, 4, 5, 8, 9, 12, 13] * 4; _r1 = [2, 3, 6, 7, 10, 11, 14, 15] * 4
_s0 = [8, 9, 12, 13, 0, 1, 4, 5] * 4; _s1 = [10, 11, 14, 15, 2, 3, 6, 7] * 4
CW4 = [_r0 + _r1 + _s0 + _s1, _s0 + _s1 + _r0 + _r1]          # 짝 열: 위 두 줄 r·아래 두 줄 s(홀 니블), 홀 열은 반대
_b = [0] * 8 + [2] * 8 + [4] * 8 + [6] * 8; _c = [1] * 8 + [3] * 8 + [5] * 8 + [7] * 8
CB4 = _b + _b + _c + _c


def mem(path):
    d = open(os.path.join(path, 'GS.bin'), 'rb').read()
    return d[425:425 + (4 << 20)]                                 # 머리 425 B(CLUT 위치로 검산, 2026-10-19)


def psmt4(m, dbp, dbw, w, h):
    """dbp(블록 단위 256 B) · dbw(64 px 단위) → 색인 배열"""
    m = np.frombuffer(m, np.uint8); out = np.zeros((h, w), np.uint8); dbw2 = max(1, dbw >> 1)
    ys, xs = np.mgrid[0:h, 0:w]
    page = (xs // 128) + (ys // 128) * dbw2
    px, py = xs % 128, ys % 128
    block = np.array(B4)[(px // 32) + (py // 16) * 4]
    bx, by = px % 32, py % 16
    col = by // 4; cy = by % 4; idx = bx + cy * 32
    cw = np.where(col & 1, np.array(CW4[1])[idx], np.array(CW4[0])[idx])
    cb = np.array(CB4)[idx]
    word = dbp * 64 + page * 2048 + block * 64 + col * 16 + cw
    addr = (word * 4 + (cb >> 1)) % len(m)
    v = m[addr]
    return np.where(cb & 1, v >> 4, v & 15).astype(np.uint8)


B8 = [0, 1, 4, 5, 16, 17, 20, 21, 2, 3, 6, 7, 18, 19, 22, 23, 8, 9, 12, 13, 24, 25, 28, 29, 10, 11, 14, 15, 26, 27, 30, 31]
_e0 = [0, 1, 4, 5, 8, 9, 12, 13] * 2; _e1 = [2, 3, 6, 7, 10, 11, 14, 15] * 2
_f0 = [8, 9, 12, 13, 0, 1, 4, 5] * 2; _f1 = [10, 11, 14, 15, 2, 3, 6, 7] * 2
CW8 = [_e0 + _e1 + _f0 + _f1, _f0 + _f1 + _e0 + _e1]
CB8 = [0] * 8 + [2] * 8 + [0] * 8 + [2] * 8 + [1] * 8 + [3] * 8 + [1] * 8 + [3] * 8


def psmt8(m, dbp, dbw, w, h):
    m = np.frombuffer(m, np.uint8); dbw2 = max(1, dbw >> 1)
    ys, xs = np.mgrid[0:h, 0:w]
    page = (xs // 128) + (ys // 64) * dbw2
    px, py = xs % 128, ys % 64
    block = np.array(B8)[(px // 16) + (py // 16) * 8]
    bx, by = px % 16, py % 16
    col = by // 4; cy = by % 4; idx = bx + cy * 16
    cw = np.where(col & 1, np.array(CW8[1])[idx], np.array(CW8[0])[idx])
    cb = np.array(CB8)[idx]
    word = dbp * 64 + page * 2048 + block * 64 + col * 16 + cw
    return m[(word * 4 + cb) % len(m)]


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '8':
        Image.fromarray(psmt8(mem(sys.argv[1]), 0, 16, 1024, 4096)).save(os.path.join(sys.argv[1], 'vram8.png')); sys.exit()
    p = sys.argv[1]; m = mem(p)
    a = psmt4(m, 0, 16, 1024, 8192)
    Image.fromarray(a * 17).save(os.path.join(p, 'vram4.png'))
