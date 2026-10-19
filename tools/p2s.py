"""PCSX2 .p2s 세이브스테이트 멤버 꺼내기 (zip + zstd method 93).
사용: python tools/p2s.py <state.p2s> <outdir> [member ...]
"""
import os, struct, sys
import zstandard


def members(path):
    d = open(path, 'rb').read()
    eocd = d.rfind(b'PK\x05\x06')
    n = struct.unpack('<H', d[eocd + 10:eocd + 12])[0]
    p = struct.unpack('<I', d[eocd + 16:eocd + 20])[0]
    for _ in range(n):
        (sig, vm, vn, fl, meth, t, dt, crc, cs, us, fnl, exl, cml, dn, ia, ea,
         lho) = struct.unpack('<IHHHHHHIIIHHHHHII', d[p:p + 46])
        name = d[p + 46:p + 46 + fnl].decode()
        p += 46 + fnl + exl + cml
        lfn, lex = struct.unpack('<HH', d[lho + 26:lho + 30])
        raw = d[lho + 30 + lfn + lex:lho + 30 + lfn + lex + cs]
        if meth == 93:
            raw = zstandard.ZstdDecompressor().decompress(raw, max_output_size=us)
        elif meth != 0:
            raise ValueError(f'{name}: method {meth}')
        yield name, raw


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    want = set(sys.argv[3:])
    os.makedirs(out, exist_ok=True)
    for name, raw in members(src):
        if want and name not in want:
            continue
        open(os.path.join(out, name), 'wb').write(raw)
        print(name, len(raw))
