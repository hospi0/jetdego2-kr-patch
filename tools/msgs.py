# -*- coding: utf-8 -*-
r"""ELF 안 메시지 기록 뽑기·시트 짝짓기 (2026-10-19)
  기록 = u16 폭(= 글자 수 × G px) + u16 글자 칸 번호(열×32 + 행) …, 마지막 글자에 0x8000.
  글자 칸 번호는 «그 화면의 글자 모음 시트»(work/sheets_txt/*.tsv, 32 px 격자) 기준.
  python tools/msgs.py → work/msgs.tsv (위치·G·글자 수·시트·일본어(판독))
"""
import os, struct, glob, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ELF = os.path.join(ROOT, 'work', 'SLPM_651.08')
VA0, FO0 = 0x100000, 0x80
NL = 0x401A                     # 줄바꿈 제어 코드(쪽 4)


def sheets():
    out = {}
    for p in glob.glob(os.path.join(ROOT, 'work', 'sheets_txt', '*.tsv')):
        m = {}; cols = rows = 0
        for l in open(p, encoding='utf-8'):
            k, c, r, ch, sc, s2 = l.rstrip('\n').split('\t')
            m[int(k)] = ch; cols = max(cols, int(c) + 1); rows = max(rows, int(r) + 1)
        out[os.path.basename(p)[:-4]] = (m, cols, rows)
    return out


def records(e=None):
    e = e or open(ELF, 'rb').read()
    N = len(e) // 2; a = struct.unpack('<%dH' % N, e[:N * 2]); i = FO0 // 2; out = []
    while i < N - 2:
        w = a[i]; hit = None
        for G in (26,):                        # 다른 폭은 우연 일치뿐(2026-10-20)
            if w and w % G == 0:
                n = w // G
                if 1 <= n <= 200 and i + n < N:
                    cs = a[i + 1:i + 1 + n]
                    if cs[-1] & 0x8000 and all(not c & 0x8E00 for c in cs[:-1]) and not (cs[-1] & 0x0E00):
                        hit = (i * 2, G, [c & 0x7FFF for c in cs]); break
        if hit:
            out.append(hit); i += len(hit[2]) + 1
        else:
            i += 1
    return out


def clusters(recs):
    cl = []
    for o, G, cs in recs:
        if cl and o - cl[-1][-1][0] - 2 * (len(cl[-1][-1][2]) + 1) < 40 and cl[-1][-1][1] == G:
            cl[-1].append((o, G, cs))
        else:
            cl.append([(o, G, cs)])
    return cl


COMMON = ('して ます です くだ ださ さい しま ませ ルー ート ショ ョン モー ード 操作 設定 空港 滑走 走路 航空 飛行 着陸 離陸 '
          'ている てい いま する ると この その れて され ます。 です。 さい。 ことが こと ない たら ンを ので から まで '
          'ボタ タン 押し 選択 ゲー ーム 機長 副操 訓練 フラ ライ イト パイ イロ ロッ ット スピ ピー 高度 速度 時間 マイ イル').split()


def score(t):
    return sum(t.count(w) * len(w) for w in COMMON) + t.count('。') * 2 - t.count('□') * 3


def decode(cs, combo, S):
    """칸 번호(쪽 비트 12‥14) → 판독 글자. combo = {쪽: 시트}"""
    out = []
    for c in cs:
        if c == NL:
            out.append('⏎'); continue
        pg, k = (c >> 12) & 7, c & 0x1FF
        m = S.get(combo.get(pg), ({},))[0]
        out.append(m.get(k) or '□')
    return ''.join(out)


def best_sheet(cl, S):
    """묶음 하나 = 시트 하나(쪽 비트 0x1000·0x2000 = 색 속성, 0x401A = 줄바꿈) → [(점수, {쪽: 시트})]"""
    ks = {c & 0x1FF for _, _, cs in cl for c in cs if c != NL}
    pages = sorted({(c >> 12) & 7 for _, _, cs in cl for c in cs if c != NL})
    res = []
    for n, (m, cols, rows) in S.items():
        if not all((k >> 5) < cols and (k & 31) < rows for k in ks): continue
        cb = {p: n for p in pages}
        t = ''.join(decode(cs, cb, S) for _, _, cs in cl)
        res.append((score(t) / max(1, len(t)), cb))
    res.sort(key=lambda x: -x[0])
    return res or [(0, {})]


if __name__ == '__main__':
    S = sheets(); recs = records(); cls = clusters(recs)
    with open(os.path.join(ROOT, 'work', 'msgs.tsv'), 'w', encoding='utf-8') as f:
        for cl in cls:
            bs = best_sheet(cl, S); sc, cb = bs[0]
            name = '+'.join('%d=%s' % kv for kv in sorted(cb.items()))      # 쪽=시트
            for o, G, cs in cl:
                f.write('%06X\t%d\t%d\t%s\t%s\t%.2f\n' % (o, G, len(cs), name, decode(cs, cb, S), sc))
    print('기록', len(recs), '묶음', len(cls))
