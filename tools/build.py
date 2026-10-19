# -*- coding: utf-8 -*-
r"""Jet de Go! 2 한글 빌드 (2026-10-19)
  1) 메시지(ELF 안 기록 = u16 폭 + u16 칸번호…, 끝 0x8000) 번역 work/trans/msg_<시트>.tsv → 한글을 그 화면의 글자 모음 시트 빈 칸에 그리고 기록을 다시 씀
     · 칸 예산 = 기록 끝 뒤 0 채움까지(다른 기록을 덮지 않음) · 숫자·영문·화살표 칸은 보존(숫자 출력 코드가 칸 위치를 씀)
  2) 바뀐 JET2 항목을 LZSS(CMP3) 로 다시 압축 → 블록 재조립 → ELF 디렉터리(항목 위치·압축 크기·원래 크기·전체 크기)·섹터표 갱신
     · 블록이 원래 할당 섹터에 들어가면 제자리, 넘치면 디스크 맨 끝(마지막 파일 뒤)에 덧붙이고 섹터표를 그쪽으로(JET2 기준 섹터)
  3) ISO = 원본 복사 + ELF(LBA 309) 덮기 + JET2 블록 쓰기 + PVD 볼륨 크기
  python tools/build.py [--check]   (--check = 디스크 안 씀, 보고만)
"""
import os, sys, struct, glob, shutil, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import cmp3, gspkt, lzss

ISO = cmp3.ISO
OUT = os.path.join(ROOT, 'work', 'build', 'Jet de Go! 2 (Japan) KR.iso')
ELF_LBA, ELF_SIZE = 309, 2219440
JET2_LBA = 1717
VA0, FO0 = 0x100000, 0x80
SECTAB = 0x17D988                     # ELF 파일 위치: 섹터표 [u64 첫 섹터, u64 끝 섹터, u64 크기, u64 포인터] (JET2 기준)
FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
GLYPH = 26                            # 글자 칸(폭 머리 = 글자 수 × 26)
KEEP = set('△〇０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ↑↓←→◯○×')
OCR_FIX = {'亅': '１', 'ｌ': 'Ｉ', 'Ο': 'Ｏ', 'Ε': 'Ｅ'}
FW = {chr(c): chr(c + 0xFEE0) for c in range(0x21, 0x7F)}
ERR = []   # 반각 → 전각(보존 칸 찾기용)


# ---------------- JET2 / ELF 구조 ----------------
def sector_table(elf):
    out = {}; a = SECTAB
    while True:
        f0, z0, l0, z1, s0, z2, p0, z3 = struct.unpack_from('<8I', elf, a)
        if z0 or z1 or z2 or z3 or l0 < f0 or s0 == 0:
            break
        out[f0] = a; a += 32
    return out


def descriptors(elf):
    """이름 구조체: [항목 n×20 B][이름 0x80][항목표 VA·0·크기·n][-RA- 머리] → {첫 섹터?} 대신 머리 시각·크기로 찾음"""
    import re
    out = []
    for m in re.finditer(rb'data/[\w/]+\.dat\x00', elf):
        nm = m.start()
        if nm % 16: continue
        ptr, z, size, n = struct.unpack_from('<4I', elf, nm + 0x80)
        if z or not (VA0 <= ptr < VA0 + len(elf)): continue
        ea = ptr - VA0 + FO0
        ents = [list(struct.unpack_from('<5I', elf, ea + 20 * i)) for i in range(n)]
        out.append(dict(name=elf[nm:m.end() - 1].decode(), at=nm, ea=ea, size=size, n=n, ts=elf[nm + 0x94:nm + 0x98], ents=ents))
    return out


class Jet2:
    def __init__(self, elf):
        self.elf = elf; self.f = open(ISO, 'rb')
        self.offs = cmp3.blocks(); self.offs.append(cmp3.SIZE)
        self.st = sector_table(elf); self.desc = descriptors(elf)

    def block(self, k):
        self.f.seek(cmp3.BASE + self.offs[k]); return self.f.read(self.offs[k + 1] - self.offs[k])

    def desc_of(self, k):
        blk = self.block(k); ts = blk[8:12]
        es, _ = cmp3.entries(blk)
        for d in self.desc:
            if d['ts'] == ts and d['n'] >= len(es) and all(d['ents'][i][0] == es[i][0] and d['ents'][i][2] == es[i][1] for i in range(len(es))):
                return d
        raise KeyError('블록 %d 의 ELF 디렉터리 못 찾음' % k)


# ---------------- 글자 그리기 ----------------
def glyph_cell(ch, font):
    """32×32 4비트 칸: 글자 몸 8·B·D·E·F, 테두리 1‥4 (원본 시트와 같은 색인 쓰임)"""
    S = 4; W = 32 * S
    im = Image.new('L', (W, W)); d = ImageDraw.Draw(im)
    if ch.strip():
        bb = d.textbbox((0, 0), ch, font=font)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        x = (GLYPH * S - w) // 2 - bb[0]; y = (GLYPH * S - h) // 2 - bb[1]
        if ch in '.,':
            y = GLYPH * S - S * 6 - h - bb[1]; x = S * 3 - bb[0]
        d.text((x, y), ch, 255, font=font)
    core = np.asarray(im.resize((32, 32), Image.LANCZOS), np.float32) / 255
    halo = np.asarray(Image.fromarray((core * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
    out = np.zeros((32, 32), np.uint8)
    for th, v in ((0.12, 1), (0.3, 2), (0.5, 3), (0.75, 4)):
        out[halo > th] = v
    for th, v in ((0.15, 8), (0.3, 0xB), (0.45, 0xD), (0.65, 0xE), (0.85, 0xF)):
        out[core > th] = v
    out[GLYPH:, :] = 0; out[:, GLYPH:] = 0
    return out


# ---------------- 메시지 ----------------
def load_ocr(sheet):
    m = {}; cols = rows = 0
    for l in open(os.path.join(ROOT, 'work', 'sheets_txt', sheet + '.tsv'), encoding='utf-8'):
        k, c, r, ch, sc, s2 = l.rstrip('\n').split('\t')
        m[int(k)] = OCR_FIX.get(ch, ch); cols = max(cols, int(c) + 1); rows = max(rows, int(r) + 1)
    return m, cols, rows


def read_rec(elf, fo):
    w = struct.unpack_from('<H', elf, fo)[0]; cs = []; o = fo + 2
    while True:
        c = struct.unpack_from('<H', elf, o)[0]; o += 2; cs.append(c & 0x7FFF)
        if c & 0x8000: break
    return w, cs, o


def budget(elf, fo):
    """기록 + 뒤 0 채움 → 쓸 수 있는 글자 수(16 B 정렬 경계에서 다음 0 아닌 바이트 전까지)"""
    _, cs, end = read_rec(elf, fo); o = end
    while o < len(elf) and elf[o] == 0: o += 1
    o &= ~3                                # 다음 기록은 4 이상 정렬(실제 8·16) — 정렬 경계 앞까지만
    return max(len(cs), (o - fo - 2) // 2)


def build_sheet(sheet, elf, report):
    """→ (블록, 항목, 새 항목 bytes) · elf 제자리 수정"""
    m, cols, rows = load_ocr(sheet)
    tr = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'work', 'trans', 'msg_%s.tsv' % sheet), encoding='utf-8') if l.strip() and not l.startswith('#')]
    # 이 시트를 쓰는 다른(번역 안 한) 기록의 칸은 보존
    keep = {k for k, ch in m.items() if ch in KEEP}
    done = {int(o, 16) for o, _ in tr}
    for l in open(os.path.join(ROOT, 'work', 'msgs.tsv'), encoding='utf-8'):
        o, G, n, sh, t, amb = l.rstrip('\n').split('\t')
        sc = float(amb.split(',')[0].split(':')[1]) if ':' in amb else 0
        if sh == sheet and G == '26' and int(o, 16) not in done and sc >= 0.2:     # 점수 낮은 묶음 = 다른 시트(일본어로 안 읽힘)
            keep |= set(read_rec(elf, int(o, 16))[1])
    have = {}                                  # 글자 → 칸
    for k in sorted(keep):
        if m.get(k): have.setdefault(m[k], k)
    free = [c * 32 + r for r in range(rows) for c in range(cols) if c * 32 + r not in keep]
    font = ImageFont.truetype(FONT, 22)
    draw = {}
    blank = None

    def code(ch):
        nonlocal blank
        if ch == ' ':
            if blank is None:
                blank = free.pop(0); draw[blank] = ' '
            return blank
        f = FW.get(ch, ch)
        if f in have: return have[f]
        if ch in have: return have[ch]
        if not free: raise RuntimeError('%s: 칸 모자람(%s)' % (sheet, ch))
        k = free.pop(0); draw[k] = ch; have[ch] = k
        return k
    for o, ko in tr:
        fo = int(o, 16); n_old = len(read_rec(elf, fo)[1]); cap = budget(elf, fo)
        ko = ko.strip()
        cs = [code(ch) for ch in ko]
        if len(cs) > cap:
            ERR.append('%s %s: %d자 > 예산 %d «%s»' % (sheet, o, len(cs), cap, ko)); continue
        rec = struct.pack('<H', GLYPH * len(cs)) + struct.pack('<%dH' % len(cs), *cs[:-1], cs[-1] | 0x8000)
        old_end = read_rec(elf, fo)[2]
        span = max(old_end - fo, len(rec))     # 늘어나면 뒤 0 채움 자리(예산 안)까지 — 바이트 수는 그대로(삽입 금지)
        elf[fo:fo + span] = rec + b'\0' * (span - len(rec))
        report.append('  %s %2d→%2d/%2d «%s»' % (o, n_old, len(cs), cap, ko))
    # 시트 화소 수정
    blk, ent, ui = int(sheet[:4]), int(sheet[5:7]), int(sheet[8:11])
    return blk, ent, ui, draw, (cols, rows), len(free)


def patch_sheet_pixels(d, ui, draw):
    us = gspkt.uploads(d); u = us[ui]
    w, h = u[4], u[5]; pos = u[7]
    b = np.frombuffer(d[pos:pos + w * h // 2], np.uint8)
    idx = np.stack([b & 15, b >> 4], 1).ravel().reshape(h, w).copy()
    font = ImageFont.truetype(FONT, 22 * 4)        # glyph_cell 은 4배 캔버스에 그림
    for k, ch in draw.items():
        c, r = k >> 5, k & 31
        idx[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32] = glyph_cell(ch, font)
    flat = idx.ravel()
    nb = (flat[0::2] | (flat[1::2] << 4)).astype(np.uint8).tobytes()
    d = bytearray(d); d[pos:pos + len(nb)] = nb
    return bytes(d), idx


# ---------------- 블록 재조립 ----------------
def rebuild_block(j2, k, newents, elf):
    """newents: {항목번호: 새 원래 bytes} → 새 블록 bytes · ELF 디렉터리 갱신"""
    blk = j2.block(k); desc = j2.desc_of(k)
    out = bytearray(blk[:16])
    for i, e in enumerate(desc['ents']):
        off, comp, raw = e[0], e[1], e[2]
        if i in newents:
            data = newents[i]; piece = b'CMP3' + struct.pack('<I', len(data)) + lzss.compress(data)
            raw = len(data)
        else:
            piece = blk[off:off + comp]
        if i and off % 2048 == 0:              # 원래 섹터 정렬 항목(무압축·직접 읽기)은 정렬 유지
            out += bytes(1) * ((-len(out)) % 2048)
        e[0], e[1], e[2] = len(out), len(piece), raw
        out += piece
        struct.pack_into('<5I', elf, desc['ea'] + 20 * i, *e)
    struct.pack_into('<I', elf, desc['at'] + 0x88, len(out))
    return bytes(out)


def main(check):
    elf = bytearray(open(os.path.join(ROOT, 'work', 'SLPM_651.08'), 'rb').read())
    j2 = Jet2(bytes(elf))
    report = []; changes = {}               # 블록 → {항목: bytes}
    previews = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'trans', 'msg_*.tsv'))):
        sheet = os.path.basename(p)[4:-4]
        report.append('[%s]' % sheet)
        blk, ent, ui, draw, dims, nfree = build_sheet(sheet, elf, report)
        es, _ = cmp3.entries(j2.block(blk))
        d = changes.setdefault(blk, {}).get(ent, es[ent][2])
        d, idx = patch_sheet_pixels(d, ui, draw)
        changes[blk][ent] = d
        report.append('  새 글자 %d칸 · 남은 빈 칸 %d' % (len(draw), nfree))
        previews.append((sheet, idx))
    if ERR:
        print('\n'.join(ERR)); sys.exit(1)
    # 그림 글자(tools/gfx.py, work/gfx/gfx.tsv)
    import gfx
    gj, gprev = gfx.jobs()
    for (k, j), data in gj.items():
        if j in changes.get(k, {}):
            raise RuntimeError('블록 %d 항목 %d: 메시지 시트와 그림이 같은 항목 — 합치기 필요' % (k, j))
        changes.setdefault(k, {})[j] = data
    report.append('그림 %d장 (항목 %d개)' % (len(gprev), len(gj)))
    # 미리보기
    os.makedirs(os.path.join(ROOT, 'work', 'build'), exist_ok=True)
    for sheet, idx in previews:
        g = (idx.astype(np.uint16) * 17).clip(0, 255).astype(np.uint8)
        Image.fromarray(g).resize((idx.shape[1] * 2, idx.shape[0] * 2), Image.NEAREST).save(os.path.join(ROOT, 'work', 'build', 'sheet_%s.png' % sheet))
    # 블록
    newblocks = {}
    for k, ents in changes.items():
        newblocks[k] = rebuild_block(j2, k, ents, elf)
    # 섹터표·배치
    iso_size = os.path.getsize(ISO); end_sec = iso_size // 2048
    place = {}
    for k, nb in sorted(newblocks.items()):
        first = j2.offs[k] // 2048; rec = j2.st[first]
        f0, _, l0, _, s0, _, p0, _ = struct.unpack_from('<8I', elf, rec)
        cap = (l0 - f0 + 1) * 2048
        if len(nb) <= cap:
            nf = f0
        else:
            nf = end_sec - JET2_LBA; end_sec += (len(nb) + 2047) // 2048
        nl = nf + (len(nb) + 2047) // 2048 - 1 if len(nb) > cap else l0
        struct.pack_into('<8I', elf, rec, nf, 0, nl, 0, len(nb), 0, p0, 0)
        place[k] = (nf, len(nb), cap)
        report.append('블록 %d: %d B (원래 %d B, 할당 %d) → %s' % (k, len(nb), s0, cap, '제자리' if nf == f0 else '디스크 끝 섹터 %d' % (nf + JET2_LBA)))
    print('\n'.join(report))
    if check:
        return
    # ISO
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    shutil.copyfile(ISO, OUT)
    with open(OUT, 'r+b') as f:
        f.seek(ELF_LBA * 2048); f.write(elf)
        for k, nb in newblocks.items():
            nf, n, cap = place[k]
            f.seek((JET2_LBA + nf) * 2048); f.write(nb + b'\0' * ((-len(nb)) % 2048))
            if nf == j2.offs[k] // 2048 and n < cap:
                f.write(b'\0' * (cap - n - ((-len(nb)) % 2048)))
        f.seek(0, 2); tot = f.tell() // 2048
        f.seek(16 * 2048 + 80); f.write(struct.pack('<I', tot) + struct.pack('>I', tot))
    h = hashlib.md5(open(OUT, 'rb').read()).hexdigest()
    print('ISO', OUT, os.path.getsize(OUT), 'md5', h)


if __name__ == '__main__':
    main('--check' in sys.argv)
