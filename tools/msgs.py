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
        for G in (26, 32, 24, 20, 22, 28, 30, 16, 18):
            if w and w % G == 0:
                n = w // G
                if 1 <= n <= 200 and i + n < N:
                    cs = a[i + 1:i + 1 + n]
                    if cs[-1] & 0x8000 and all(not c & 0x8000 and c < 0x200 for c in cs[:-1]) and (cs[-1] & 0x7FFF) < 0x200:
                        hit = (i * 2, G, [c & 0x7FFF for c in cs]); break
        if hit:
            out.append(hit); i += len(hit[2]) + 1
        else:
            i += 1
    return out


def clusters(recs):
    cl = []
    for o, G, cs in recs:
        if cl and o - cl[-1][-1][0] - 2 * (len(cl[-1][-1][2]) + 1) < 96 and cl[-1][-1][1] == G:
            cl[-1].append((o, G, cs))
        else:
            cl.append([(o, G, cs)])
    return cl


COMMON = ('して ます です くだ ださ さい しま ませ ルー ート ショ ョン モー ード 操作 設定 空港 滑走 走路 航空 飛行 着陸 離陸 '
          'ている てい いま する ると この その れて され ます。 です。 さい。 ことが こと ない たら ンを ので から まで '
          'ボタ タン 押し 選択 ゲー ーム 機長 副操 訓練 フラ ライ イト パイ イロ ロッ ット スピ ピー 高度 速度 時間 マイ イル').split()


def score(t):
    return sum(t.count(w) * len(w) for w in COMMON) + t.count('。') * 2 - t.count('□') * 3


def best_sheet(cl, S):
    res = []
    for name, (m, cols, rows) in S.items():
        if any((c >> 5) >= cols or (c & 31) >= rows for _, _, cs in cl for c in cs):
            continue
        t = ''.join(''.join(m.get(c) or '□' for c in cs) for _, _, cs in cl)
        res.append((score(t) / max(1, len(t)), name))
    res.sort(reverse=True)
    return res or [(0, '?')]


if __name__ == '__main__':
    S = sheets(); recs = records(); cls = clusters(recs)
    with open(os.path.join(ROOT, 'work', 'msgs.tsv'), 'w', encoding='utf-8') as f:
        for cl in cls:
            bs = best_sheet(cl, S); name = bs[0][1]; m = S.get(name, ({},))[0]
            amb = ','.join('%s:%.2f' % (n, s) for s, n in bs[:3])
            for o, G, cs in cl:
                t = ''.join(m.get(c) or '□' for c in cs)
                f.write('%06X\t%d\t%d\t%s\t%s\t%s\n' % (o, G, len(cs), name, t, amb))
    print('기록', len(recs), '묶음', len(cls))
