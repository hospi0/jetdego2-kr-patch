# -*- coding: utf-8 -*-
r"""Jet de Go! 2 — JET2.BIN 풀기 (2026-10-19)
  JET2.BIN = «-RA-» 블록(2048 정렬) 연속. 블록 머리 16 B: '-RA-' u32 0x01010008 u32 유닉스시각 u32 0
    뒤에 CMP3 항목이 머리 없이 이어 붙음(개수·크기 표 없음 — 다음 'CMP3' 까지). 머리 0 이면 무압축 블록.
  CMP3 = 'CMP3' u32 풀린크기 + LZSS(Okumura: 고리 4096·0 초기화·r=0xFEE·플래그 LSB 먼저 1=리터럴·
         복사 2 B: 위치 = b1 | (b2&0xF0)<<4, 길이 = (b2&15)+3).
  python tools/cmp3.py scan   → work/jet2_index.tsv (블록·항목·압축 위치·크기·풀린 크기·첫 4바이트)
"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISO = r'C:\claude\roms\ps2\Jet de Go! 2 (Japan).iso'
BASE, SIZE = 1717 * 2048, 1230028800


def unlzss(src, pos, outlen):
    """→ (풀린 bytes, 다음 위치)"""
    ring = bytearray(4096); r = 0xFEE; out = bytearray(); flags = 0
    while len(out) < outlen:
        flags >>= 1
        if not flags & 0x100:
            flags = src[pos] | 0xFF00; pos += 1
        if flags & 1:
            c = src[pos]; pos += 1
            out.append(c); ring[r] = c; r = (r + 1) & 0xFFF
        else:
            b1, b2 = src[pos], src[pos + 1]; pos += 2
            p = b1 | (b2 & 0xF0) << 4
            for k in range((b2 & 15) + 3):
                c = ring[(p + k) & 0xFFF]
                out.append(c); ring[r] = c; r = (r + 1) & 0xFFF
    return bytes(out[:outlen]), pos


def blocks():
    f = open(ISO, 'rb'); offs = []
    pos = 0; CH = 64 << 20
    while pos < SIZE:
        f.seek(BASE + pos); d = f.read(min(CH, SIZE - pos))
        offs += [pos + o for o in range(0, len(d), 2048) if d[o:o + 4] == b'-RA-']
        pos += CH
    return offs


def entries(blk):
    """블록 bytes → [(위치, 풀린 크기, 데이터)]"""
    out = []; p = 16
    while p + 8 <= len(blk) and blk[p:p + 4] == b'CMP3':
        n = struct.unpack_from('<I', blk, p + 4)[0]
        d, q = unlzss(blk, p + 8, n)
        out.append((p, n, d))
        i = blk.find(b'CMP3', q, q + 8)                # 항목 사이 1 B(뜻 모름 — 검사합?)
        p = i if i >= 0 else q
    return out, p


if __name__ == '__main__':
    f = open(ISO, 'rb'); offs = blocks(); offs.append(SIZE)
    rows = []
    for k in range(len(offs) - 1):
        f.seek(BASE + offs[k]); blk = f.read(offs[k + 1] - offs[k])
        if blk[16:20] != b'CMP3':
            rows.append((k, offs[k], -1, 16, len(blk) - 16, len(blk) - 16, blk[16:20].hex())); continue
        es, end = entries(blk)
        for j, (p, n, d) in enumerate(es):
            rows.append((k, offs[k], j, p, 0, n, d[:4].hex()))
        if blk[end:].strip(b'\0'):
            print('블록', k, hex(offs[k]), '끝 뒤 남은 바이트', len(blk) - end, blk[end:end + 8].hex())
    with open(os.path.join(ROOT, 'work', 'jet2_index.tsv'), 'w', encoding='utf-8') as w:
        for r in rows: w.write('\t'.join(str(x) if not isinstance(x, int) or x < 0 else str(x) for x in r) + '\n')
    print('블록', len(offs) - 1, '항목', len(rows))
