# -*- coding: utf-8 -*-
# msg_0066_00_000.tsv 생성 — 공항·활주로 반복 문장 + 고정 문장 (2026-10-20)
import os
HERE = os.path.dirname(os.path.abspath(__file__))
AP = {'新千歳空港': '신치토세 공항', '小松空港': '코마츠 공항', '東亰国際空港': '도쿄 국제공항', '名古屋空港': '나고야 공항',
      '大阪国際空港': '오사카 국제공항', '広鳥空港': '히로시마 공항', '問西国際空港': '간사이 국제공항', '福岡空港': '후쿠오카 공항',
      '那覇空港': '나하 공항', '下地鳥空港': '시모지시마 공항'}
FIXED = {
    '168A70': '{ABCDEFGHIJKLMNOPQRSTUVWXYZー통과}',
    '168AB0': '플랩을 올려 주세요', '168AD0': '플랩을 내려 주세요', '168AF0': '속도를 높여 주세요', '168B10': '속도를 낮춰 주세요',
    '168DA0': '웨이포인트 통과 실패', '168DC0': '△버튼을 눌러 주세요', '168DE0': '관제 교신 중',
    '168DF0': '랜딩 기어 UP', '168E10': '랜딩 기어 DOWN', '168E30': '좌석벨트 사인 ON', '168E50': '좌석벨트 사인 OFF',
    '168E70': '객실등 ON', '168E80': '객실등 OFF', '168E90': '도어 열림', '168EA0': '도어 닫힘',
    '168EB0': '음료 서비스 중', '168ED0': '음료 서비스 안내', '168EF0': '기내 판매 시작 안내', '168F08': '담요 배포 중',
    '168F18': '풍경 안내', '168F28': '정지', '168F30': '승객 탑승 중', '168F40': '푸시백 허가', '168F60': '푸시백 중',
    '168F80': '지상 활주 허가', '168FA0': '안전 비디오 안내', '168FC0': '안전 시연', '168FE8': '이륙 허가 중', '168FF8': '이륙 개시',
    '1690F0': '출발 관제와 교신', '169110': '순항 고도 상승 지시', '169128': '정기 보고', '169140': '항로 관제 이관',
    '169160': '순항 고도에서 강하 허가', '169180': '착륙 전 주의', '169750': '유도로 진입 지시',
    '169AD0': '3분 안에 고도 15000피트까지 상승해 주세요', '169B10': '3분 안에 고도 8000피트까지 상승해 주세요',
    '169B50': '환승 안내 중', '169D60': '부기장 승격 훈련⏎시작', '169D80': '기장 승격 훈련⏎시작',
}
rows = []
for l in open(os.path.join(HERE, 'src_all.tsv'), encoding='utf-8'):
    if l.startswith('#'): continue
    o, sh, cap, n, ja = l.rstrip('\n').split('\t')
    if sh != '0066_00_000': continue
    if o in FIXED:
        rows.append((o, FIXED[o])); continue
    br = ja.startswith('{') and ja.endswith('}')
    t = ja.strip('{}')
    if '⏎' not in t: continue
    a, b = t.split('⏎', 1)
    if a.startswith('滑走路'):
        rw = a[3:].translate(str.maketrans('０１２３４５６７８９亅ＲＬ', '0123456789 1RL'.replace(' ', '')[:10] + '1RL'))
        rw = ''.join('1' if ch == '亅' else ch for ch in a[3:])
        rw = rw.translate(str.maketrans('０１２３４５６７８９ＲＬ', '0123456789RL'))
        ko = '활주로 %s⏎%s' % (rw, {'進入許可': '진입 허가', '着陸許可': '착륙 허가'}[b])
    elif a in AP:
        ko = '%s⏎%s' % (AP[a], {'離陸': '이륙', '着陸': '착륙', '到着': '도착'}[b])
    else:
        continue
    rows.append((o, '{%s}' % ko if br else ko))
with open(os.path.join(HERE, 'msg_0066_00_000.tsv'), 'w', encoding='utf-8') as f:
    f.write('#위치\t번역 — 비행 중 지시·관제·객실 안내(시트 0066_00_000). gen_0066.py 로 생성(손대지 말고 스크립트 고칠 것)\n')
    for o, ko in rows: f.write('%s\t%s\n' % (o, ko))
print(len(rows))
