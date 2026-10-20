# -*- coding: utf-8 -*-
r"""비행 중 노선 지도(일본 위성 지도) 현 이름 47개 한글화 (2026-10-20)
  지도 = 블록 64 항목 0 (이름 있는 판) · 블록 55 항목 0 (이름 없는 같은 지도, 팔레트 같음)
    [0x400 팔레트 256색 32비트][128×128 8bpp 조각 73장] — 배치표 없이 바다 칸을 건너뛴 줄 순서.
  배치: 조각 i 오른쪽 = i+1(가장자리에 땅이 있으면), 아래 = 위아래 이음새가 가장 잘 맞는 조각 → 이어 붙여 좌표(모자이크).
  라벨: 64≠55 화소 = 원문 글자 → 55 화소로 지우고 같은 중심에 한글(연한 회녹색 + 옅은 그림자)을 그려 64 팔레트로 색인화.
  python tools/jmap.py → work/gfx/prev_jmap.png (원본|새것) · build.py 가 job() 을 부름
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx, gspkt
BLK, CLEAN, N = 64, 55, 73
FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
# (모자이크 중심 x, y, 원문, 한글) — 거센소리 표기, 굳은 지명(도쿄·교토·오사카)은 굳은 꼴
LABELS = [(1154, 248, '北海道', '홋카이도'), (1017, 567, '青森', '아오모리'), (985, 680, '秋田', '아키타'),
          (1069, 681, '岩手', '이와테'), (961, 809, '山形', '야마가타'), (1027, 808, '宮城', '미야기'),
          (870, 934, '新潟', '니가타'), (976, 935, '福島', '후쿠시마'), (678, 1034, '石川', '이시카와'),
          (739, 1032, '富山', '토야마'), (875, 1046, '群馬', '군마'), (939, 1023, '栃木', '토치기'),
          (806, 1081, '長野', '나가노'), (966, 1080, '茨城', '이바라키'), (672, 1103, '福井', '후쿠이'),
          (905, 1104, '埼玉', '사이타마'), (482, 1170, '鳥取', '톳토리'), (722, 1140, '岐阜', '기후'),
          (846, 1140, '山梨', '야마나시'), (910, 1138, '東京', '도쿄'), (605, 1192, '京都', '교토'),
          (654, 1192, '滋賀', '시가'), (557, 1215, '兵庫', '효고'), (903, 1174, '神奈川', '카나가와'),
          (973, 1174, '千葉', '치바'), (368, 1224, '島根', '시마네'), (482, 1232, '岡山', '오카야마'),
          (739, 1219, '愛知', '아이치'), (802, 1219, '静岡', '시즈오카'), (398, 1259, '広島', '히로시마'),
          (599, 1265, '大阪', '오사카'), (680, 1265, '三重', '미에'), (299, 1312, '山口', '야마구치'),
          (492, 1305, '香川', '카가와'), (637, 1308, '奈良', '나라'), (583, 1335, '和歌山', '와카야마'),
          (237, 1359, '福岡', '후쿠오카'), (512, 1340, '徳島', '토쿠시마'), (187, 1410, '佐賀', '사가'),
          (397, 1375, '愛媛', '에히메'), (451, 1382, '高知', '코치'), (157, 1448, '長崎', '나가사키'),
          (297, 1431, '大分', '오이타'), (246, 1494, '熊本', '쿠마모토'), (290, 1535, '宮崎', '미야자키'),
          (224, 1595, '鹿児島', '카고시마'), (684, 1840, '沖縄', '오키나와')]
SIZE, MAXW = 18, 72


def tiles(d):
    return [np.frombuffer(d[1024 + i * 16384:1024 + (i + 1) * 16384], np.uint8).reshape(128, 128).copy() for i in range(N)]


def layout(A, pal, B):
    T = [pal[t][..., :3].astype(np.float32) for t in A]
    sea = np.median(T[51].reshape(-1, 3), 0)
    land = lambda e: (np.abs(e - sea).sum(-1) > 40).mean()
    links = []
    for i in range(N):
        if i + 1 < N and land(T[i][:, -1]) > 0.02: links.append((i, i + 1, 1, 0))
        if land(T[i][-1]) > 0.02:
            links.append((i, int(np.argmin([np.abs(T[i][-1] - T[j][0]).mean() for j in range(N)])), 0, 1))
    pos = {0: (0, 0)}; ch = True
    while ch:
        ch = False
        for i, j, dx, dy in links:
            if i in pos and j not in pos: pos[j] = (pos[i][0] + dx, pos[i][1] + dy); ch = True
            elif j in pos and i not in pos: pos[i] = (pos[j][0] - dx, pos[j][1] - dy); ch = True
    x0 = min(p[0] for p in pos.values()); y0 = min(p[1] for p in pos.values())
    W = max(p[0] for p in pos.values()) - x0 + 1; H = max(p[1] for p in pos.values()) - y0 + 1
    extra = [i for i in range(N) if i not in pos and (A[i] != B[i]).any()]   # 따로 노는 섬 조각(이름 있는 것만) = 맨 아래 줄에 차례로
    for n, i in enumerate(extra): pos[i] = (x0 + n % W, y0 + H + n // W)
    H += (len(extra) + W - 1) // W
    return {t: ((x - x0) * 128, (y - y0) * 128) for t, (x, y) in pos.items()}, W * 128, H * 128


def mosaic(T, pos, W, H):
    M = np.zeros((H, W), np.uint8)
    for t, (x, y) in pos.items(): M[y:y + 128, x:x + 128] = T[t]
    return M


def render():
    import cv2
    da, db = gfx.entry_data(BLK, 0), gfx.entry_data(CLEAN, 0)
    assert da[:1024] == db[:1024]
    pal = gspkt.pal_of(da[:1024], 0, 256)
    A, B = tiles(da), tiles(db)
    pos, W, H = layout(A, pal, B)
    MA, MB = mosaic(A, pos, W, H), mosaic(B, pos, W, H)
    diff = (MA != MB).astype(np.uint8)
    rgb = pal[MA][..., :3].astype(np.float32); clean = pal[MB][..., :3].astype(np.float32)
    out = rgb.copy(); touched = np.zeros((H, W), bool)
    font = ImageFont.truetype(FONT, SIZE * 4)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(diff, np.ones((5, 9), np.uint8)))
    for cx, cy, jp, kr in LABELS:
        k = lab[cy, cx] if lab[cy, cx] else lab[cy - 6:cy + 7, cx - 6:cx + 7].max()
        assert k, (jp, cx, cy)
        x, y, w, h = st[k][:4]
        m = cv2.dilate(((lab == k) & (diff > 0)).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        body = m & (pal[MA][..., :3].astype(int).sum(-1) > 3 * 150)
        col = np.percentile(rgb[body], 80, 0) if body.any() else np.array([190, 200, 180.])
        out[m] = clean[m]; touched |= m
        # 한글: 4배로 그려 줄임, 그림자 = 오른쪽 아래 1 px 흐린 어두운 색
        bb = font.getbbox(kr); tw, th = bb[2] - bb[0], bb[3] - bb[1]
        pw, ph = tw + 16 * 4, th + 16 * 4
        L = Image.new('L', (pw, ph)); ImageDraw.Draw(L).text((8 * 4 - bb[0], 8 * 4 - bb[1]), kr, 255, font=font)
        sc = min(1.0, MAXW * 4 / tw)
        L = L.resize((max(1, round(pw / 4 * sc)), round(ph / 4)), Image.LANCZOS)
        a = np.asarray(L, np.float32) / 255
        sh = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
        sh = np.roll(np.roll(sh, 1, 0), 1, 1) * 0.55
        ox, oy = int(round(x + w / 2 - L.width / 2)), int(round(y + h / 2 - L.height / 2))
        hh, ww = a.shape
        reg = out[oy:oy + hh, ox:ox + ww]
        reg[:] = reg * (1 - sh[..., None]) + np.array([20, 28, 22.]) * sh[..., None]
        reg[:] = reg * (1 - a[..., None]) + col * a[..., None]
        touched[oy:oy + hh, ox:ox + ww] |= (a > 0.02) | (sh > 0.02)
    # 64 팔레트로 색인화(바뀐 화소만)
    P = pal[:, :3].astype(np.float32)
    idx = MA.copy(); ys, xs = np.nonzero(touched)
    v = out[ys, xs]
    d2 = ((v[:, None, :] - P[None]) ** 2).sum(-1)
    idx[ys, xs] = d2.argmin(1).astype(np.uint8)
    keep = touched & (np.abs(out - clean).sum(-1) < 1) & (MB != MA)
    idx[keep] = MB[keep]                                        # 지운 자리 = 55 색인 그대로(팔레트 같음)
    return da, pal, pos, MA, idx


def job():
    da, pal, pos, MA, idx = render()
    d = bytearray(da)
    for t, (x, y) in pos.items():
        d[1024 + t * 16384:1024 + (t + 1) * 16384] = idx[y:y + 128, x:x + 128].tobytes()
    return {(BLK, 0): bytes(d)}


if __name__ == '__main__':
    da, pal, pos, MA, idx = render()
    a, b = pal[MA][..., :3], pal[idx][..., :3]
    cv = Image.new('RGB', (a.shape[1] * 2 + 8, a.shape[0]), (255, 0, 255))
    cv.paste(Image.fromarray(a), (0, 0)); cv.paste(Image.fromarray(b), (a.shape[1] + 8, 0))
    cv.save(os.path.join(ROOT, 'work', 'gfx', 'prev_jmap_v2.png'))
    print('조각', len(pos), '바뀐 화소', int((idx != MA).sum()))
