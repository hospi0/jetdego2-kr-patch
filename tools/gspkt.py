# -*- coding: utf-8 -*-
r"""JET2.BIN 의 GS 전송 패킷 그림 뽑기 (2026-10-19)
  항목 = DMA 태그(u64: qwc | id<<28, 위 u64 = VIF 코드 … DIRECT) 연속. 안에 GIF 태그:
    PACKED A+D: 0x50 BITBLTBUF(DBP·DBW·DPSM) 0x51 TRXPOS 0x52 TRXREG(가로 bit0‥11, 세로 bit32‥43) 0x53 (게임 값)
    IMAGE(flg 2): 화소 qword nloop 개 — 선형(GS 가 스위즐).
  DPSM: 0 = 32비트 · 2 = 16비트 · 0x13 = 8bpp · 0x14 = 4bpp. CLUT 는 같은 항목의 작은 32/16비트 전송(16색 = 8×2, 256색 = 16×16).
  python tools/gspkt.py → work/gs/<블록>_<항목>_<번호>.png · work/gs/list.tsv
"""
import os, struct, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import cmp3


def uploads(d):
    """→ [(위치, dbp, dbw, dpsm, w, h, 화소 bytes, 화소 위치)]"""
    out = []; o = 0; reg = {}
    while o + 16 <= len(d):
        t0, t1 = struct.unpack_from('<QQ', d, o)
        qwc = t0 & 0xFFFF; tid = (t0 >> 28) & 7
        if (t1 >> 56) & 0x7F not in (0x50, 0x51) and t1 != 0 and (t1 >> 24) & 0x7F != 0x50:
            break
        q = o + 16; end = q + qwc * 16
        if end > len(d): break
        while q + 16 <= end:
            g0, g1 = struct.unpack_from('<QQ', d, q)
            nloop = g0 & 0x7FFF; eop = (g0 >> 15) & 1; flg = (g0 >> 58) & 3; nreg = (g0 >> 60) & 15 or 16
            q += 16
            if flg == 0:
                for i in range(nloop * nreg):
                    v, a = struct.unpack_from('<QQ', d, q); reg[a & 0xFF] = v; q += 16
            elif flg == 2:
                bb = reg.get(0x50, 0); tr = reg.get(0x52, 0)
                w, h = tr & 0xFFF, (tr >> 32) & 0xFFF
                out.append((o, (bb >> 32) & 0x3FFF, (bb >> 48) & 0x3F, (bb >> 56) & 0x3F, w, h, d[q:q + nloop * 16], q))
                q += nloop * 16
            else:
                q += (nloop * nreg * 8 + 15) & ~15
        o = end
        if tid in (0, 7) and False: break
    return out


def pal_of(raw, psm, n):
    if psm == 0:
        a = np.frombuffer(raw[:n * 4], np.uint8).reshape(-1, 4).copy(); a[:, 3] = np.minimum(255, a[:, 3].astype(int) * 2)
    else:
        v = np.frombuffer(raw[:n * 2], '<u2').astype(np.uint32)
        a = np.stack([(v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3, np.where(v & 0x8000, 255, 0)], -1).astype(np.uint8)
    if n == 256:
        a = a.reshape(8, 4, 8, 4)[:, [0, 2, 1, 3]].reshape(256, 4)
    return a


def render(u, pal=None):
    o, dbp, dbw, psm, w, h, raw, _ = u
    if psm in (0x14, 0x13):
        if psm == 0x14:
            b = np.frombuffer(raw[:w * h // 2], np.uint8); idx = np.stack([b & 15, b >> 4], 1).ravel()
            n = 16
        else:
            idx = np.frombuffer(raw[:w * h], np.uint8); n = 256
        if len(idx) < w * h: return None
        if pal is None:
            g = (idx * (255 // (n - 1))).astype(np.uint8); return np.stack([g, g, g, np.full_like(g, 255)], -1).reshape(h, w, 4)
        return pal[idx].reshape(h, w, 4)
    if psm == 0:
        a = np.frombuffer(raw[:w * h * 4], np.uint8)
        if len(a) < w * h * 4: return None
        a = a.reshape(h, w, 4).copy(); a[..., 3] = np.minimum(255, a[..., 3].astype(int) * 2); return a
    if psm == 2:
        v = np.frombuffer(raw[:w * h * 2], '<u2')
        if len(v) < w * h: return None
        return pal_of(raw, 2, w * h).reshape(h, w, 4)
    return None


def images(d):
    """항목 → [(번호, 업로드, RGBA)] — 색인 그림은 같은 항목의 CLUT(16색=8×2·256색=16×16) 를 차례로 짝지음"""
    us = uploads(d); res = []
    cl16 = [u for u in us if u[3] in (0, 2) and u[4] * u[5] == 16]
    cl256 = [u for u in us if u[3] in (0, 2) and u[4] * u[5] == 256]
    i16 = i256 = 0
    for k, u in enumerate(us):
        if u in cl16 or u in cl256: continue
        pal = None
        if u[3] == 0x14 and cl16:
            c = cl16[min(i16, len(cl16) - 1)]; pal = pal_of(c[6], c[3], 16); i16 += 1
        elif u[3] == 0x13 and cl256:
            c = cl256[min(i256, len(cl256) - 1)]; pal = pal_of(c[6], c[3], 256); i256 += 1
        img = render(u, pal)
        if img is not None: res.append((k, u, img))
    return res


if __name__ == '__main__':
    OUT = os.path.join(ROOT, 'work', 'gs'); os.makedirs(OUT, exist_ok=True)
    ents = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'work', 'jet2_entries.tsv'), encoding='utf-8')]
    want = {}
    for b, off, j, p, n, mg in ents:
        if mg.endswith('0060'): want.setdefault(int(b), int(off))
    offs = cmp3.blocks(); offs.append(cmp3.SIZE)
    f = open(cmp3.ISO, 'rb'); rows = []
    for k in sorted(want):
        f.seek(cmp3.BASE + offs[k]); blk = f.read(offs[k + 1] - offs[k])
        es, _ = cmp3.entries(blk) if blk[16:20] == b'CMP3' else ([], 0)
        for j, (p, n, d) in enumerate(es):
            if d[3] != 0x60: continue
            for i, u, img in images(d):
                nm = '%04d_%02d_%03d.png' % (k, j, i)
                Image.fromarray(img).save(os.path.join(OUT, nm))
                rows.append((nm, k, j, i, u[1], u[2], hex(u[3]), u[4], u[5], hex(u[7])))
    with open(os.path.join(OUT, 'list.tsv'), 'w', encoding='utf-8') as w:
        for r in rows: w.write('\t'.join(map(str, r)) + '\n')
    print('그림', len(rows))
