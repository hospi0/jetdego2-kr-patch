# -*- coding: utf-8 -*-
r"""스테이트 eeMemory 에서 «화소를 DMA REF 로 보내는» 업로드 찾기 (2026-10-19)
  패킷 머리(BITBLTBUF·TRXREG + IMAGE 태그) 뒤에 화소가 없고, 다른 곳의 REF 태그(qwc = IMAGE nloop)가 화소 주소를 가리킴.
  python tools/refups.py <work/mem/이름> → <이름>/ref/<머리주소>_<화소주소>_<가로>x<세로>.png"""
import os, re, struct, sys
import numpy as np
from PIL import Image

PAT = re.compile(rb'\x50\x00\x00\x00\x00\x00\x00\x00.{8}\x51\x00\x00\x00\x00\x00\x00\x00', re.S)


def find(d):
    refs = {}
    for o in range(0, len(d) - 16, 16):
        t0 = struct.unpack_from('<Q', d, o)[0]
        if (t0 >> 28) & 7 == 3 and t0 & 0xFFFF >= 8 and (t0 >> 32) < len(d) and not (t0 >> 16) & 0xFFF and t0 & 0x80000000 == 0:
            refs.setdefault(t0 & 0xFFFF, []).append(((t0 >> 32) & 0x7FFFFFFF, o))
    out = []
    for m in PAT.finditer(d):
        a = m.start() - 8; reg = {}; q = a
        for i in range(4):
            v, r = struct.unpack_from('<QQ', d, q); reg[r & 0xFF] = v; q += 16
        g0 = struct.unpack_from('<Q', d, q)[0]
        if (g0 >> 58) & 3 != 2: continue
        n = g0 & 0x7FFF; bb = reg.get(0x50, 0); tr = reg.get(0x52, 0)
        w, h, psm = tr & 0xFFF, (tr >> 32) & 0xFFF, (bb >> 56) & 0x3F
        for addr, at in refs.get(n, []):
            out.append((a, addr, at, (bb >> 32) & 0x3FFF, (bb >> 48) & 0x3F, psm, w, h))
    return out


if __name__ == '__main__':
    p = sys.argv[1]; d = open(os.path.join(p, 'eeMemory.bin'), 'rb').read()
    os.makedirs(os.path.join(p, 'ref'), exist_ok=True)
    for a, addr, at, dbp, dbw, psm, w, h in find(d):
        if psm == 0x14:
            raw = np.frombuffer(d[addr:addr + w * h // 2], np.uint8); img = np.stack([raw & 15, raw >> 4], 1).ravel()[:w * h].reshape(h, w) * 17
        elif psm == 0x13:
            img = np.frombuffer(d[addr:addr + w * h], np.uint8).reshape(h, w)
        else:
            continue
        print(hex(a), hex(addr), 'dbp', dbp, 'dbw', dbw, hex(psm), w, h)
        Image.fromarray(img.astype(np.uint8)).save(os.path.join(p, 'ref', '%07X_%07X_%dx%d.png' % (a, addr, w, h)))
