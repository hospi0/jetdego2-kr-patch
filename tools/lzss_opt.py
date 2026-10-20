# -*- coding: utf-8 -*-
r"""CMP3 LZSS 최적 분할 압축기(2026-10-20) — anearth-kr-patch/tools/lzss_enc.py encode_opt 를 이 게임 규약(창 0 초기화·시작 0xFEE)으로.
  리터럴 9비트·참조 17비트 최소 비용 DP. 결과는 tools/lzss.decompress 로 되풀어 확인. 같은 내용은 work/cache/lz 에 캐시.
"""
import os, sys, bisect, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lzss
W, R0, MINL, MAXL = 4096, 0xFEE, 3, 18


def encode_opt(data):
    data = bytes(data); n = len(data)
    H = bytes(W) + data; end = len(H)                   # H[i] 의 창 위치 = (R0 + i - W) % W, 앞 W = 0 창
    idx = {}
    for p in range(W - MAXL, end - 2):
        idx.setdefault(H[p:p + 3], []).append(p)
    best = [(0, 0)] * n
    for i in range(n):
        cur = W + i
        if cur + 3 > end: continue
        lst = idx.get(H[cur:cur + 3], []); k = bisect.bisect_left(lst, cur); bl = bm = 0
        for j in range(k - 1, -1, -1):
            m = lst[j]
            if cur - m > W - 1: break
            L = 0
            while L < MAXL and cur + L < end and H[m + L] == H[cur + L]: L += 1
            if L > bl:
                bl, bm = L, m
                if L == MAXL: break
        best[i] = (bl, bm)
    INF = 1 << 60; cost = [INF] * (n + 1); cost[n] = 0; choice = [1] * n
    for i in range(n - 1, -1, -1):
        c = 9 + cost[i + 1]; ch = 1; bl = best[i][0]
        for L in range(MINL, bl + 1):
            v = 17 + cost[i + L]
            if v < c: c, ch = v, L
        cost[i] = c; choice[i] = ch
    out = bytearray(); i = 0
    while i < n:
        fp = len(out); out.append(0); fl = 0
        for bit in range(8):
            if i >= n: break
            L = choice[i]
            if L >= MINL:
                off = (R0 + best[i][1] - W) % W
                out.append(off & 0xFF); out.append(((off >> 4) & 0xF0) | (L - 3)); i += L
            else:
                fl |= 1 << bit; out.append(data[i]); i += 1
        out[fp] = fl
    return bytes(out)


def compress(data):
    d = os.path.join(os.path.dirname(HERE), 'work', 'cache', 'lz'); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, hashlib.md5(bytes(data)).hexdigest() + '.bin')
    if os.path.exists(p): return open(p, 'rb').read()
    enc = encode_opt(data)
    assert lzss.decompress(enc)[:len(data)] == bytes(data), 'LZSS 되풀기 불일치'
    open(p, 'wb').write(enc); return enc
