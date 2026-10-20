# -*- coding: utf-8 -*-
r"""PCSX2 GS 덤프(.gs, xz 푼 것) 읽기 — 한 프레임 동안의 GIF 전송에서 텍스처 업로드·TEX0 뽑기 (2026-10-20)
  머리: ffffffff · u32 머리크기 · (상태 버전·상태 크기·이름 위치/크기·crc·스샷 폭/높이/위치/크기) … 뒤에 상태(상태 크기) + 레지스터 8192 + 패킷
  패킷: 0 전송(u8 경로, u32 크기, 데이터) · 1 VSync(u8) · 2 ReadFIFO(u32) · 3 레지스터(8192)
  python tools/gsdump.py <x.gs> → 업로드 목록(순번·dbp·dbw·psm·폭×높이·바이트)
"""
import struct, sys


def packets(d):
    hs = struct.unpack_from('<I', d, 4)[0]; ss = struct.unpack_from('<I', d, 12)[0]
    p = 8 + hs + ss + 8192
    while p < len(d):
        t = d[p]; p += 1
        if t == 0:
            sz = struct.unpack_from('<I', d, p + 1)[0]; yield d[p + 5:p + 5 + sz]; p += 5 + sz
        elif t == 1: p += 1
        elif t == 2: p += 4
        elif t == 3: p += 8192


def gif(d):
    """→ [('reg', 주소, 값) | ('img', bytes)] — 경로 3 데이터 이어 붙인 것"""
    p = 0; out = []
    while p + 16 <= len(d):
        lo, hi = struct.unpack_from('<QQ', d, p); p += 16
        nloop = lo & 0x7fff; flg = (lo >> 58) & 3; nreg = (lo >> 60) or 16
        regs = [(hi >> (4 * i)) & 15 for i in range(nreg)]
        if flg == 0:
            for _ in range(nloop):
                for r in regs:
                    a, b = struct.unpack_from('<QQ', d, p); p += 16
                    if r == 0xE: out.append(('reg', b & 0xff, a))
        elif flg == 1:
            n = nloop * nreg; p += ((n + 1) // 2) * 16
        else:
            out.append(('img', d[p:p + nloop * 16])); p += nloop * 16
    return out


def uploads(d):
    st = {}; ups = []; cur = None
    data = b''.join(packets(d))
    for ev in gif(data):
        if ev[0] == 'reg':
            st[ev[1]] = ev[2]
            if ev[1] == 0x53:
                bb = st.get(0x50, 0); tr = st.get(0x52, 0)
                cur = dict(dbp=(bb >> 32) & 0x3fff, dbw=(bb >> 48) & 0x3f, psm=(bb >> 56) & 0x3f,
                           w=tr & 0xfff, h=(tr >> 32) & 0xfff, data=bytearray()); ups.append(cur)
            if ev[1] in (6, 7): ups.append(dict(tex0=ev[2]))
        elif cur is not None:
            cur['data'] += ev[1]
    return ups


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    for i, u in enumerate(uploads(d)):
        if 'tex0' in u:
            t = u['tex0']; continue
        print(i, u['dbp'], u['dbw'], hex(u['psm']), '%dx%d' % (u['w'], u['h']), len(u['data']))
