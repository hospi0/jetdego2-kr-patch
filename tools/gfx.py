# -*- coding: utf-8 -*-
r"""그림 글자 한글화 (GS 전송 패킷 그림, 4/8bpp) — 2026-10-19
  표 work/gfx/gfx.tsv : 그림이름  상자(x0,y0,x1,y1 또는 band:N = 위에서 N번째 불투명 줄 띠)  한글  꼴(키=값;…)
    꼴: fill=#rrggbb|auto  edge=#rrggbb|auto|none  shadow=1|0  size=px  align=l|c|r  erase=clear|inpaint  bold=1  slant=0.15
       auto = 지운 자리 원래 글자에서 색 뽑음(채움 = 가장 채도 높은/밝은 색, 테두리 = 글자 둘레 색)
  python tools/gfx.py preview → work/gfx/prev_<그림>.png (원본 | 새것, 3배)
  build.py 가 jobs() 를 불러 항목 bytes 를 고침
"""
import os, sys, struct, colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import cmp3, gspkt
FONTS = {'eb': r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf',
         'b': r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'}
SPEC = os.path.join(ROOT, 'work', 'gfx', 'gfx.tsv')
_blk = {}


def entry_data(k, j):
    if k not in _blk:
        offs = cmp3.blocks.__wrapped__() if hasattr(cmp3.blocks, '__wrapped__') else None
    if (k, j) not in _blk:
        f = open(cmp3.ISO, 'rb'); offs = _offs()
        f.seek(cmp3.BASE + offs[k]); es, _ = cmp3.entries(f.read(offs[k + 1] - offs[k]))
        for jj, (p, n, d) in enumerate(es): _blk[(k, jj)] = d
    return _blk[(k, j)]


_O = []


def _offs():
    if not _O:
        _O.extend(cmp3.blocks()); _O.append(cmp3.SIZE)
    return _O


def indexed(d, ui):
    """→ (색인 배열, 팔레트 RGBA, 업로드)"""
    us = gspkt.uploads(d); u = us[ui]; w, h, psm = u[4], u[5], u[3]
    n = 16 if psm == 0x14 else 256
    cl = [x for x in us if x[3] in (0, 2) and x[4] * x[5] == n]
    # gspkt.images 와 같은 짝: n색 그림의 순번 → 같은 순번 CLUT
    order = [x for x in us if x[3] == psm and not (x[3] in (0, 2))]
    k = [i for i, x in enumerate(us) if x[3] == psm and x is not u and us.index(x) < ui]
    pal = gspkt.pal_of(cl[min(len(k), len(cl) - 1)][6], cl[0][3], n) if cl else None
    if psm == 0x14:
        b = np.frombuffer(u[6][:w * h // 2], np.uint8); idx = np.stack([b & 15, b >> 4], 1).ravel().reshape(h, w)
    else:
        idx = np.frombuffer(u[6][:w * h], np.uint8).reshape(h, w)
    return idx.copy(), pal, u


def store(d, u, idx):
    d = bytearray(d); flat = idx.ravel()
    nb = (flat[0::2] | (flat[1::2] << 4)).astype(np.uint8).tobytes() if u[3] == 0x14 else flat.astype(np.uint8).tobytes()
    d[u[7]:u[7] + len(nb)] = nb
    return bytes(d)


def bands(alpha):
    rows = alpha.max(1) > 40; out = []; s = None
    for y, v in enumerate(list(rows) + [False]):
        if v and s is None: s = y
        if not v and s is not None:
            if y - s > 2: out.append((s, y))
            s = None
    return out


def parse_style(s):
    st = dict(fill='auto', edge='auto', shadow='1', size='0', align='l', erase='clear', font='eb', slant='0', pad='0')
    for kv in s.split(';'):
        if '=' in kv:
            k, v = kv.split('=', 1); st[k.strip()] = v.strip()
    return st


def hexc(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


def render(img, box, text, st):
    """img RGBA(np) 위 box 에 한글 — 반환 RGBA"""
    x0, y0, x1, y1 = box; W, H = x1 - x0, y1 - y0
    region = img[y0:y1, x0:x1].astype(int)
    op = region[..., 3] > 128
    # 색 뽑기
    if st['fill'] == 'auto':
        px = region[op][:, :3]
        if len(px):
            sat = np.array([colorsys.rgb_to_hsv(*(p / 255))[1] * 2 + colorsys.rgb_to_hsv(*(p / 255))[2] for p in px])
            fill = tuple(int(v) for v in np.median(px[sat >= np.percentile(sat, 80)], 0))
        else:
            fill = (255, 255, 255)
    else:
        fill = hexc(st['fill'])
    if st['edge'] == 'auto':
        px = region[op][:, :3]
        lum = px.sum(1) if len(px) else np.array([0])
        edge = tuple(int(v) for v in np.median(px[lum <= np.percentile(lum, 25)], 0)) if len(px) else (0, 0, 0)
    else:
        edge = None if st['edge'] == 'none' else hexc(st['edge'])
    # 지우기
    out = img.copy()
    if st['erase'] == 'clear':
        out[y0:y1, x0:x1] = 0
    elif st['erase'] == 'fill':                         # 단색 칸: 상자 안 가장 흔한 색으로 칠함
        reg = out[y0:y1, x0:x1].reshape(-1, 4)
        vals, cnt = np.unique(reg, axis=0, return_counts=True)
        out[y0:y1, x0:x1] = vals[cnt.argmax()]
    else:
        import cv2
        rgb = np.ascontiguousarray(out[..., :3]); mask = np.zeros(rgb.shape[:2], np.uint8)
        if st['erase'] == 'inpaint':                    # 글자 화소만(주변 중앙값과 다른 곳 + 2 px 늘림) — 바탕 무늬 살림
            med = cv2.medianBlur(rgb, 15)
            diff = np.abs(rgb.astype(int) - med.astype(int)).sum(-1)
            m = np.zeros(rgb.shape[:2], np.uint8); m[y0:y1, x0:x1] = (diff[y0:y1, x0:x1] > int(st.get('th', '70'))) * 255
            mask = cv2.dilate(m, np.ones((5, 5), np.uint8))
            mask[:y0] = 0; mask[y1:] = 0; mask[:, :x0] = 0; mask[:, x1:] = 0
        elif st['erase'] == 'bright':                   # 밝은 글자(흰 글씨)만 — 어두운 사진 바탕
            lum = rgb.astype(int).sum(-1) // 3
            m = np.zeros(rgb.shape[:2], np.uint8); m[y0:y1, x0:x1] = (lum[y0:y1, x0:x1] > int(st.get('th', '140'))) * 255
            mask = cv2.dilate(m, np.ones((5, 5), np.uint8))
            mask[:y0] = 0; mask[y1:] = 0; mask[:, :x0] = 0; mask[:, x1:] = 0
        else:                                           # inpaint_box: 상자 통째
            mask[y0:y1, x0:x1] = 255
        rgb = cv2.inpaint(rgb, mask, 7, cv2.INPAINT_TELEA); out[..., :3] = rgb
    # 글자
    core, core2 = layout(W, H, text, st, both=True)
    a = np.zeros((H, W, 4), np.float32)
    if st['shadow'] == '1':
        sh = np.roll(np.roll(core, 2, 0), 2, 1)
        sh = np.asarray(Image.fromarray((sh * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
        a = comp(a, (20, 20, 30), sh * 0.7)
    if edge:
        ring = np.asarray(Image.fromarray((core * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), np.float32) / 255
        a = comp(a, edge, ring)
    a = comp(a, fill, core)
    if core2.any():                                   # {…} 강조색
        a = comp(a, hexc(st.get('fill2', '#40c080')), core2)
    base = out[y0:y1, x0:x1].astype(np.float32)
    al = a[..., 3:4]
    rgb = a[..., :3] * al + base[..., :3] * (1 - al)
    alpha = np.maximum(base[..., 3:4], al * 255)
    out[y0:y1, x0:x1] = np.concatenate([rgb, alpha], -1).clip(0, 255).astype(np.uint8)
    return out


def layout(W, H, text, st, both=False):
    """상자 W×H 에 글자 그린 0‥1 배열 — ⏎ 줄바꿈(줄 간격 lh px), 넘치면 가로만 줄임, 세로 가운데. {…} = 강조(both=True 면 강조 글자만 따로)"""
    S = 4; lines = text.split('⏎'); n = len(lines)
    lay2 = Image.new('L', (W * S, H * S)); d2 = ImageDraw.Draw(lay2)
    lh = int(st.get('lh', '0')) or H // n
    size = int(st['size']) or int(lh * 0.82); pad = int(st['pad'])
    lay = Image.new('L', (W * S, H * S)); d = ImageDraw.Draw(lay)
    top = (H - lh * n) * S // 2
    for i, raw in enumerate(lines):
        ln = raw.replace('{', '').replace('}', '')
        font = ImageFont.truetype(FONTS[st['font']], size * S)
        bb = d.textbbox((0, 0), ln, font=font); tw = bb[2] - bb[0]
        if tw > (W - 2 * pad - 4) * S:                  # 상자 넘치면 가로만 줄임
            tmp = Image.new('L', (tw + 8 * S, lh * S)); dt = ImageDraw.Draw(tmp)
            asc, desc = font.getmetrics()
            dt.text((4 * S - bb[0], (lh * S - (asc + desc)) // 2), ln, 255, font=font)
            tmp = tmp.resize(((W - 2 * pad - 4) * S, lh * S), Image.LANCZOS)
            lay.paste(tmp, ((pad + 2) * S, top + i * lh * S), tmp); continue
        ax = {'l': pad * S + 2 * S, 'c': (W * S - tw) // 2, 'r': W * S - tw - pad * S - 2 * S}[st['align']]
        asc, desc = font.getmetrics()
        yy = top + i * lh * S + (lh * S - (asc + desc)) // 2
        d.text((ax - bb[0], yy), ln, 255, font=font)
        pre = ''; hi = False; seg = ''
        for ch in raw + '{':                          # 강조 조각만 lay2 에
            if ch in '{}':
                if hi and seg: d2.text((ax - bb[0] + font.getlength(pre), yy), seg, 255, font=font)
                pre += seg; seg = ''; hi = ch == '{'
            else:
                seg += ch
    sl = float(st['slant'])
    if sl:
        lay = lay.transform(lay.size, Image.AFFINE, (1, sl, -sl * H * S / 2, 0, 1, 0), Image.BICUBIC)
    core = np.asarray(lay.resize((W, H), Image.LANCZOS), np.float32) / 255
    if both:
        return core, np.asarray(lay2.resize((W, H), Image.LANCZOS), np.float32) / 255
    return core


def render_idx(idx, box, text, st):
    """색인 직접: 몸 body(+안티에일리어싱 ramp), 테두리 edge/soft, 바탕 = 상자 안 최빈 색인 — 팔레트가 밝기=알파 식일 때"""
    x0, y0, x1, y1 = box; W, H = x1 - x0, y1 - y0
    bg = int(np.bincount(idx[y0:y1, x0:x1].ravel()).argmax()) if st.get('bg', 'auto') == 'auto' else int(st['bg'], 16)
    ramp = [int(c, 16) for c in st['ramp'].split(',')]          # 진한→옅은 (몸 쪽부터)
    edge, soft = int(st['edge'], 16), int(st['soft'], 16)
    S = 4; size = int(st['size']) or int(H * 0.8); pad = int(st['pad'])
    font = ImageFont.truetype(FONTS[st['font']], size * S)
    lay = Image.new('L', (W * S, H * S)); d = ImageDraw.Draw(lay)
    bb = d.textbbox((0, 0), text, font=font); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    if tw > (W - 2 * pad - 4) * S:
        font = ImageFont.truetype(FONTS[st['font']], int(size * S * (W - 2 * pad - 4) * S / tw))
        bb = d.textbbox((0, 0), text, font=font); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    ax = {'l': pad * S + 2 * S, 'c': (W * S - tw) // 2, 'r': W * S - tw - pad * S - 2 * S}[st['align']]
    d.text((ax - bb[0], (H * S - th) // 2 - bb[1]), text, 255, font=font)
    core = np.asarray(lay.resize((W, H), Image.LANCZOS), np.float32) / 255
    ring = np.asarray(Image.fromarray((core * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.5)), np.float32) / 255
    out = np.full((H, W), bg, np.uint8)
    out[ring > 0.2] = soft; out[ring > 0.5] = edge
    n = len(ramp)
    for i, v in enumerate(reversed(ramp)):                      # 옅은 것부터 덮음
        th_ = 0.15 + (0.8 - 0.15) * i / max(1, n - 1)
        out[core > th_] = v
    idx[y0:y1, x0:x1] = out
    return idx


def comp(a, col, m):
    m = m[..., None]; c = np.array(col, np.float32)[None, None]
    rgb = c * m + a[..., :3] * a[..., 3:4] * (1 - m)
    al = m + a[..., 3:4] * (1 - m)
    rgb = np.where(al > 0, rgb / np.maximum(al, 1e-6), 0)
    return np.concatenate([rgb, al], -1)


def quantize(img, pal, box, idx):
    x0, y0, x1, y1 = box
    reg = img[y0:y1, x0:x1].astype(np.float32); P = pal.astype(np.float32)
    w = np.array([1, 1.2, 0.8, 1.5], np.float32)
    dist = (((reg[:, :, None, :] - P[None, None]) * w) ** 2).sum(-1)
    # 투명은 투명 색인으로
    tr = reg[..., 3] < 64
    best = dist.argmin(-1)
    tidx = int(np.argmin(P[:, 3]))
    best[tr] = tidx
    idx[y0:y1, x0:x1] = best
    return idx


def jobs():
    """→ {(블록, 항목): 새 bytes}, 미리보기 목록"""
    import glob, re
    rows = [l.rstrip('\n').split('\t') for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'gfx', 'gfx*.tsv')))
            for l in open(p, encoding='utf-8') if l.strip() and not l.startswith('#')]
    P = ',.!?:;)\'"~、。，．！？：；）」』】〉》”’…‥・·～〜♪♥'
    for r in rows:                                  # 문장부호 뒤 공백 지움(전 프로젝트 규칙)
        r[2] = re.sub('([' + re.escape(P) + '])[ 　]+', lambda m: m.group(1), r[2])
    out = {}; prev = []
    for r in rows:
        name, boxs, text = r[0], r[1], r[2]; st = parse_style(r[3] if len(r) > 3 else '')
        k, j, ui = int(name[:4]), int(name[5:7]), int(name[8:11])
        d = out.get((k, j)) or entry_data(k, j)
        idx, pal, u = indexed(d, ui)
        img = pal[idx]
        if boxs.startswith('band:'):
            b = bands(img[..., 3]); y0, y1 = b[int(boxs[5:])]
            xs = np.nonzero(img[y0:y1, :, 3].max(0) > 40)[0]
            box = (max(0, xs.min() - 1), max(0, y0 - 1), min(img.shape[1], xs.max() + 2), min(img.shape[0], y1 + 1))
        elif boxs.startswith('seg:'):                   # 가로 덩어리(틈 6 px 이상) N번째 — 영문 뒤 일본어 라벨
            cols = list(img[..., 3].max(0) > 40) + [False]; segs = []; s0 = None; gap = 0
            for x, v in enumerate(cols):
                if v:
                    if s0 is None: s0 = x
                    gap = 0; e0 = x
                elif s0 is not None:
                    gap += 1
                    if gap >= 6 or x == len(cols) - 1: segs.append((s0, e0 + 1)); s0 = None
            segs = [g for g in segs if g[1] - g[0] >= 8]
            x0, x1 = segs[int(boxs[4:])]
            ys = np.nonzero(img[:, x0:x1, 3].max(1) > 40)[0]
            box = (max(0, x0 - 1), max(0, ys.min() - 1), min(img.shape[1], x1 + 1), min(img.shape[0], ys.max() + 2))
        else:
            box = tuple(int(v) for v in boxs.split(','))
        if st.get('mode') == 'idx':
            idx2 = render_idx(idx.copy(), box, text, st)
        else:
            new = render(img, box, text, st)
            idx2 = quantize(new, pal, box, idx.copy())
        out[(k, j)] = store(d, u, idx2)
        prev.append((name, img, pal[idx2]))
    return out, prev


if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'work', 'gfx'), exist_ok=True)
    _, prev = jobs()
    for name, a, b in prev:
        h, w = a.shape[:2]
        cv = Image.new('RGBA', (w * 2 + 8, h), (60, 60, 90, 255))
        cv.alpha_composite(Image.fromarray(a), (0, 0)); cv.alpha_composite(Image.fromarray(b), (w + 8, 0))
        cv = cv.resize((cv.width * 3, cv.height * 3), Image.NEAREST)
        cv.save(os.path.join(ROOT, 'work', 'gfx', 'prev_%s.png' % name))
    print('미리보기', len(prev))
