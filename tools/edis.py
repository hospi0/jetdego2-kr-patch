# -*- coding: utf-8 -*-
r"""SLPM_651.08 EE 디스어셈블(capstone MIPS64) — 적재 0x100000, 파일 0x80 = 0x100000 (2026-10-19)
  python tools/edis.py <주소hex> [명령 수]"""
import os, sys, capstone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ELF = open(os.path.join(ROOT, 'work', 'SLPM_651.08'), 'rb').read()
VA, FO = 0x100000, 0x80
md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS64 + capstone.CS_MODE_LITTLE_ENDIAN)
md.skipdata = True


def dis(a, n=60):
    o = a - VA + FO
    return ['%08X  %s %s' % (i.address, i.mnemonic, i.op_str) for i in md.disasm(ELF[o:o + n * 4], a)][:n]


if __name__ == '__main__':
    print('\n'.join(dis(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 60)))
