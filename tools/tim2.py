# -*- coding: utf-8 -*-
r"""TIM2 → RGBA 그림 (2026-10-19, Jet de Go! 2)
  머리 16 B('TIM2' 판 형식 u16 그림 수) + 그림마다 머리 48 B(전체·CLUT·화소 크기, 머리 크기, CLUT 색 수,
  형식, 밉맵, CLUT 종류, 화소 종류(1=16 2=24 3=32 4=4bpp 5=8bpp), 가로, 세로 …). 알파 0x80 = 불투명.
  CLUT 종류 bit7=0 이면 CSM1(8bpp 는 8색 묶음 2·3번 맞바꿈).
"""
import struct
import numpy as np


def c16(a):
    a = a.astype(np.uint32)
    r = (a & 31) << 3; g = ((a >> 5) & 31) << 3; b = ((a >> 10) & 31) << 3; al = np.where(a & 0x8000, 255, 0)
    return np.stack([r, g, b, al], -1).astype(np.uint8)


def colors(raw, kind, n):
    if kind == 1:
        return c16(np.frombuffer(raw[:n * 2], '<u2'))
    if kind == 2:
        a = np.frombuffer(raw[:n * 3], np.uint8).reshape(-1, 3); return np.concatenate([a, np.full((len(a), 1), 255, np.uint8)], 1)
    a = np.frombuffer(raw[:n * 4], np.uint8).reshape(-1, 4).copy()
    a[:, 3] = np.minimum(255, a[:, 3].astype(int) * 2)
    return a


def pictures(d):
    """→ [(가로, 세로, bpp, RGBA ndarray, 화소 위치, CLUT 위치)]"""
    n = struct.unpack_from('<H', d, 6)[0]; p = 16; out = []
    if d[4] == 4 or d[5] == 1:          # 판 4 이상 정렬 128
        pass
    for _ in range(n):
        tot, csz, isz, hsz, ccol, fmt, mip, ctype, itype, w, h = struct.unpack_from('<IIIHHBBBBHH', d, p)
        ip = p + hsz; cp = ip + isz
        if itype in (4, 5):
            k = ctype & 0x3F
            pal = colors(d[cp:cp + csz], k, ccol)
            if itype == 5 and not ctype & 0x80 and len(pal) >= 256:
                pal = pal[:256].reshape(8, 4, 8, 4)[:, [0, 2, 1, 3]].reshape(256, 4)
            if itype == 4:
                b = np.frombuffer(d[ip:ip + w * h // 2], np.uint8)
                idx = np.stack([b & 15, b >> 4], 1).ravel()
            else:
                idx = np.frombuffer(d[ip:ip + w * h], np.uint8)
            pal = np.concatenate([pal, np.zeros((max(0, 256 - len(pal)), 4), np.uint8)])
            img = pal[idx].reshape(h, w, 4)
        else:
            img = colors(d[ip:ip + isz], itype, w * h).reshape(h, w, 4)
        out.append((w, h, {1: 16, 2: 24, 3: 32, 4: 4, 5: 8}.get(itype, 0), img, ip, cp))
        p += tot
    return out
