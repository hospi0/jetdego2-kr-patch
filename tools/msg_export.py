# -*- coding: utf-8 -*-
r"""메시지 원문 뽑기(시트 대응표 work/msg_sheets.tsv 기준) → work/trans/src_all.tsv (2026-10-20)
  열: 위치 · 시트 · 칸예산(뒤 0 채움까지) · 원문 글자 수 · 원문(판독). 표기: {…} = 색 속성 0x1000, [ … ] = 0x2000, ⏎ = 줄바꿈(0x401A)
  번역 파일 work/trans/msg_<시트>.tsv 도 같은 표기를 쓴다."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import msgs


def sheet_map():
    out = []
    for l in open(os.path.join(ROOT, 'work', 'msg_sheets.tsv'), encoding='utf-8'):
        if l.startswith('#') or not l.strip(): continue
        a, b, s = l.rstrip('\n').split('\t'); out.append((int(a, 16), int(b, 16), s))
    return out


def sheet_of(o, sm):
    for a, b, s in sm:
        if a <= o <= b: return s
    return None


def marked(cs, m):
    out = []; cur = 0
    for c in cs:
        if c == msgs.NL:
            out.append('⏎'); continue
        at = c & 0x3000
        if at != cur:
            if cur: out.append({0x1000: '}', 0x2000: ']'}[cur])
            if at: out.append({0x1000: '{', 0x2000: '['}[at])
            cur = at
        out.append(m.get(c & 0x1FF) or '□')
    if cur: out.append({0x1000: '}', 0x2000: ']'}[cur])
    return ''.join(out)


if __name__ == '__main__':
    sys.path.insert(0, HERE); import build as B
    S = msgs.sheets(); sm = sheet_map(); elf = bytearray(open(os.path.join(ROOT, 'work', 'SLPM_651.08'), 'rb').read())
    n = 0
    with open(os.path.join(ROOT, 'work', 'trans', 'src_all.tsv'), 'w', encoding='utf-8') as f:
        f.write('#위치\t시트\t칸예산\t원문글자수\t원문(판독; {}=색 ⏎=줄바꿈)\n')
        for o, G, cs in msgs.records():
            s = sheet_of(o, sm)
            if not s: continue
            f.write('%06X\t%s\t%d\t%d\t%s\n' % (o, s, B.budget(elf, o), len(cs), marked(cs, S[s][0]))); n += 1
    print('기록', n)
