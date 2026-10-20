# -*- coding: utf-8 -*-
r"""번역 기록 길이 검사(빌드 전) — python tools/fitcheck.py <시트> → 예산 넘는 기록과 넘친 칸 수
  칸 = 문장부호 뒤 공백 지운 뒤 글자 수(⟪XX⟫ 0칸, ⇥XX·⏎ 1칸, ‹…› 1칸). 예산 = build.budget(원본 ELF)
"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import build, cmp3
f = open(cmp3.ISO, 'rb'); f.seek(build.ELF_LBA * 2048); elf = f.read(build.ELF_SIZE)
sheet = sys.argv[1]; over = 0
for l in open(os.path.join(build.ROOT, 'work', 'trans', 'msg_%s.tsv' % sheet), encoding='utf-8'):
    if l.startswith('#') or not l.strip(): continue
    o, t = l.rstrip('\n').split('\t')[:2]
    t = build.squeeze(t.strip())
    t = re.sub('⟪..⟫', '', t); t = re.sub('⇥..', '#', t); t = re.sub('‹[^›]*›', '#', t); t = re.sub('[{}\[\]]', '', t)
    n = len(t); cap = build.budget(elf, int(o, 16)); ptr = bool(build.ptr_refs(elf, int(o, 16)))
    if n > cap:
        over += 1; print('%s %3d > %3d (+%d)%s' % (o, n, cap, n - cap, '' if ptr else ' 포인터없음'))
print('넘침', over)
