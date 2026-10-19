# -*- coding: utf-8 -*-
r"""글자 모음 시트 판독(32 px 격자) — 일본어 글꼴로 JIS 전 글자를 그려 칸마다 맞춤 (2026-10-19)
  python tools/ocr_sheet.py <시트이름…>   (work/gs/<이름>.png)
  → work/sheets_txt/<이름>.tsv : 칸번호(열×32+행) · 열 · 행 · 글자 · 점수 · 2등 글자
  ★판독은 추정 — 점수 낮은 칸·비슷한 꼴(ー一・〇Ｏ０ 등)은 사람이 확인.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', 'sheets_txt'); os.makedirs(OUT, exist_ok=True)
FONTS = [(r'C:\Windows\Fonts\msgothic.ttc', 0), (r'C:\Windows\Fonts\meiryo.ttc', 0), (r'C:\Windows\Fonts\YuGothB.ttc', 0)]
CELL = 32; N = 48


def jis_chars():
    """가나·전각 영숫자·자주 쓰는 기호·1수준 한자(그리스·키릴·2수준은 뺌 — 닮은꼴 오판)"""
    out = [chr(c) for c in range(0x3041, 0x3094)] + [chr(c) for c in range(0x30A1, 0x30F7)]
    out += [chr(c) for c in range(0xFF10, 0xFF1A)] + [chr(c) for c in range(0xFF21, 0xFF3B)] + [chr(c) for c in range(0xFF41, 0xFF5B)]
    out += list('ー－、。・（）「」『』！？：；／〜～…→←↑↓○◯×△□■☆★♂♀％＆＋＝＜＞＃＄＠々〇”“’，．')
    for hi in range(0x88, 0x99):
        for lo in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            try:
                c = bytes([hi, lo]).decode('cp932')
            except UnicodeDecodeError:
                continue
            if len(c) == 1 and c.isprintable() and c != '\u3000':
                out.append(c)
    return out


def norm(mask):
    """1비트 마스크 → (N×N 정규화 꼴, 가로, 세로, 중심 y)"""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    g = mask[y0:y1, x0:x1].astype(np.uint8) * 255
    s = max(x1 - x0, y1 - y0)
    sq = np.zeros((s, s), np.uint8); sq[(s - (y1 - y0)) // 2:(s - (y1 - y0)) // 2 + y1 - y0, (s - (x1 - x0)) // 2:(s - (x1 - x0)) // 2 + x1 - x0] = g
    v = np.asarray(Image.fromarray(sq).resize((N, N), Image.BILINEAR), np.float32) / 255
    return v, x1 - x0, y1 - y0, (y0 + y1) / 2


def templates(size=24):
    chars = jis_chars(); T = []; F = []; meta = []
    for path, idx in FONTS:
        font = ImageFont.truetype(path, size, index=idx)
        for c in chars:
            im = Image.new('L', (CELL * 2, CELL * 2)); ImageDraw.Draw(im).text((CELL // 2, CELL // 2), c, 255, font=font)
            r = norm(np.asarray(im) > 128)
            if r is None: continue
            v, w, h, cy = r
            T.append(v.ravel()); F.append((w, h, cy - CELL // 2)); meta.append(c)
    T = np.array(T); T = T - T.mean(1, keepdims=True); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-6
    return T, np.array(F, np.float32), meta


def cells(name):
    a = np.asarray(Image.open(os.path.join(ROOT, 'work', 'gs', name + '.png')).convert('L')).astype(int)
    h, w = a.shape; out = []
    for c in range(w // CELL):
        for r in range(h // CELL):
            m = a[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL] > 150
            res = norm(m)
            out.append((c, r, res))
    return out


if __name__ == '__main__':
    T, F, meta = templates()
    for name in sys.argv[1:]:
        rows = []
        for c, r, res in cells(name):
            if res is None:
                rows.append((c * 32 + r, c, r, '', 0, '')); continue
            v, w, h, cy = res
            q = v.ravel() - v.mean(); q /= np.linalg.norm(q) + 1e-6
            sc = T @ q
            # 크기 차이 벌점(작은 가나 ゃ/や 구별): 글꼴 24 px 기준, 시트 글자 크기 비율로
            sz = np.abs(F[:, 0] - w) + np.abs(F[:, 1] - h)
            sc = sc - 0.012 * sz
            o = np.argsort(-sc)
            best = meta[o[0]]; second = next((meta[i] for i in o[1:] if meta[i] != best), '')
            rows.append((c * 32 + r, c, r, best, round(float(sc[o[0]]), 3), second))
        with open(os.path.join(OUT, name + '.tsv'), 'w', encoding='utf-8') as f:
            for x in sorted(rows, key=lambda x: (x[2], x[1])):
                f.write('\t'.join(map(str, x)) + '\n')
        print(name, len(rows))
