"""제주 읍면동 소비 전환 진단표 생성.
입력: 제주관광빅데이터플랫폼 데이터 픽 CSV 7종(data/). 출력: docs/index.html, docs/data.json, 결과.json
사용: python3 -I build.py  (월별 CSV를 교체하고 다시 실행하면 전체가 갱신된다)
"""
import collections as C
import csv
import json
import os
import random
import re
import time

t0 = time.perf_counter()
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
OUT = os.path.dirname(os.path.abspath(__file__))


def R(f):
    with open(os.path.join(D, f), encoding='utf-8-sig') as h:
        return list(csv.DictReader(h))


def spearman(a, b):
    def rk(x):
        s = sorted(range(len(x)), key=lambda i: x[i])
        r = [0] * len(x)
        for p, i in enumerate(s):
            r[i] = p
        return r
    ra, rb = rk(a), rk(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return cov / (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** .5


# 12개월 창 3개. 끝을 7월로 맞춘 것은 소비(~09)·방문(~08)·도착(~07)의 공통 기간이기 때문이다.
W = {'T0': ('202308', '202407'), 'T1': ('202408', '202507'), 'T2': ('202508', '202607')}


def win(m):
    return next((k for k, (a, b) in W.items() if a <= m <= b), None)


spend = C.defaultdict(float)
foreign = C.defaultdict(float)
sector = C.defaultdict(float)
region = {}
month_spend = C.defaultdict(float)
for r in R('소비.csv'):
    if r['관광객구분'] == '도민':
        continue
    n, a, k = r['읍면동명'], float(r['소비금액(원)'] or 0), win(r['기준연월'])
    region[n] = r['지역명']
    month_spend[n, r['기준연월']] += a
    if k:
        spend[k, n] += a
        sector[k, n, r['업종명']] += a
        if r['관광객구분'] == '외국인 관광객':
            foreign[k, n] += a

visit = C.defaultdict(float)
month_visit = C.defaultdict(float)
for r in R('읍면동방문.csv'):
    n, v = r['읍면동명'], int(r['총 방문객수 (내국인+외국인)'])
    month_visit[n, r['기준연월']] += v
    if win(r['기준연월']):
        visit[win(r['기준연월']), n] += v

arrive = C.defaultdict(float)
for r in R('읍면동도착.csv'):
    if win(r['주행연월(YYYYMM)']):
        arrive[win(r['주행연월(YYYYMM)']), r['읍면동명']] += int(r['도착건수'])

names = sorted({n for _, n in visit})
assert len(names) == 43 and set(names) == set(region), '세 데이터의 읍면동 이름이 어긋남'
# 추자면은 표본이 작고 소비 구조가 달라 순위 비교에서 뺀다(카드에는 표시).
EXCL = {'추자면'}
core = [n for n in names if n not in EXCL]


def per(k, n):
    return spend[k, n] / visit[k, n]


jeju = {k: sum(spend[k, n] for n in names) / sum(visit[k, n] for n in names) for k in W}
idx = {k: {n: per(k, n) / jeju[k] for n in names} for k in W}  # 1.0 = 제주 평균

# 시간 분리 검증 1: T0의 하위 10곳이 2년 뒤 T2에도 하위 10곳인가
low0 = sorted(core, key=lambda n: idx['T0'][n])[:10]
low2 = sorted(core, key=lambda n: idx['T2'][n])[:10]
hit = len(set(low0) & set(low2))
rng = random.Random(20261030)
sim = [len(set(rng.sample(core, 10)) & set(low2)) for _ in range(100000)]
pval = sum(s >= hit for s in sim) / len(sim)
chance = sum(sim) / len(sim)


# 시간 분리 검증 2: T0 전환지수만 알 때 T2 소비를 얼마나 맞추는가(방문 수는 T2 실측 사용)
def wape(pred):
    return sum(abs(pred[n] - spend['T2', n]) for n in core) / sum(spend['T2', n] for n in core)


base = {n: visit['T2', n] * jeju['T0'] for n in core}
ours = {n: visit['T2', n] * per('T0', n) for n in core}
wape_base, wape_ours = wape(base), wape(ours)

stab01 = spearman([idx['T0'][n] for n in core], [idx['T1'][n] for n in core])
stab12 = spearman([idx['T1'][n] for n in core], [idx['T2'][n] for n in core])
stab02 = spearman([idx['T0'][n] for n in core], [idx['T2'][n] for n in core])


# 순위상관 순열검정: 지역 이름을 섞어도 이만큼 상관이 나오는가
x0, x2 = [idx['T0'][n] for n in core], [idx['T2'][n] for n in core]
perm = x2[:]
ge = 0
for _ in range(10000):
    rng.shuffle(perm)
    ge += spearman(x0, perm) >= stab02
stab_p = (ge + 1) / 10001


def grade(n):
    a, b = idx['T1'][n], idx['T2'][n]
    if n in EXCL:
        return '표본 작음'
    if max(a, b) / min(a, b) >= 1.3:
        return '변동 큼'
    if a < .8 and b < .8:
        return '구조적 전환 부족'
    if a < 1 and b < 1:
        return '전환 다소 낮음'
    return '전환 양호'


SECT = ['음식점업', '소매업', '숙박업', '예술스포츠여가업', '기타서비스업']
is_eup = {n: n.endswith(('읍', '면')) for n in names}
peer_med = {}
for s in SECT:
    for e in (True, False):
        v = sorted(sector['T2', n, s] / visit['T2', n] for n in core if is_eup[n] == e)
        peer_med[s, e] = v[len(v) // 2]

# 오름: 2026년부터 티맵 집계 로직이 바뀌어 2025년 값만 쓴다. 주소의 읍면만 안정적이므로 읍면 단위로 묶는다.
orm = C.defaultdict(lambda: [0, 0])
for f in ('오름.csv', '곶자왈.csv'):
    for r in R(f):
        if r['기준연월'][:4] != '2025':
            continue
        m = re.search(r'(\S+[읍면]) ', r['목적지 주소'])
        if m and m.group(1) in names:
            t = orm[m.group(1), r['표준화 목적지명']]
            t[0] += int(r['관광객 도착수'])
            t[1] += int(r['도민 도착수'])

months = sorted({m for _, m in month_visit if '202308' <= m <= '202607'})
ipdo = {r['기준연월']: int(r['전체 입도 관광객수']) for r in R('입도.csv')}
halla = {r['기준연월(YYYYMM)']: int(r['방문객수']) for r in R('한라산.csv')}
assert all(m in ipdo for m in months)
halla_gap = [m for m in months if m not in halla]  # 플랫폼 원자료 누락 월은 채우지 않고 기록만 한다

cards = []
for n in names:
    v = [month_visit[n, m] for m in months[-12:]]
    gaps = {s: sector['T2', n, s] / visit['T2', n] / peer_med[s, is_eup[n]] for s in SECT}
    top = sorted(((k[1], x[0]) for k, x in orm.items() if k[0] == n), key=lambda p: -p[1])
    tot = sum(p[1] for p in top)
    cards.append({
        '이름': n, '권역': region[n], '등급': grade(n),
        '방문': round(visit['T2', n]), '관광소비억': round(spend['T2', n] / 1e8, 1),
        '방문당소비': round(per('T2', n)),
        '지수': [round(idx[k][n], 2) for k in W],
        '외국인비중': round(foreign['T2', n] / spend['T2', n] * 100, 1),
        '차량도착당소비': round(spend['T2', n] / arrive['T2', n]) if arrive['T2', n] else None,
        '업종': {s: round(g, 2) for s, g in gaps.items()},
        '부족업종': min(gaps, key=gaps.get),
        '성수비': round(max(v) / min(v), 2),
        '오름': top[:3], '오름합계': tot, '오름1위비중': round(top[0][1] / tot * 100) if tot else None,
    })

grades = C.Counter(c['등급'] for c in cards)
weak = [c for c in cards if c['등급'] == '구조적 전환 부족']
weak_visit = sum(c['방문'] for c in weak) / sum(c['방문'] for c in cards)
weak_spend = sum(c['관광소비억'] for c in weak) / sum(c['관광소비억'] for c in cards)


# 산술 참고치: 전환 부족 지역의 방문 1회당 소비가 제주 평균의 80%까지 오를 때 늘어나는 소비(예측이 아니다)
TARGET = .8
gap_won = sum((TARGET - idx['T2'][c['이름']]) * jeju['T2'] * visit['T2', c['이름']] for c in weak)
assert all(idx['T2'][c['이름']] < TARGET for c in weak)


def peak(d):
    return max((m for m in months[-12:] if m in d), key=lambda m: d[m])


elapsed = time.perf_counter() - t0
result = {
    '창': W, '제주평균방문당소비': {k: round(v) for k, v in jeju.items()},
    '등급수': grades, '부족_방문비중': round(weak_visit * 100, 1), '부족_소비비중': round(weak_spend * 100, 1),
    '부족목록': sorted((c['이름'] for c in weak)),
    '검증': {'T0하위10': low0, 'T2하위10': low2, '일치': hit, '우연기대': round(chance, 2), 'p': pval,
           '순위상관': {'T0-T1': round(stab01, 3), 'T1-T2': round(stab12, 3), 'T0-T2': round(stab02, 3)},
           '순위상관_T0T2_순열p': round(stab_p, 4), 'WAPE_제주평균': round(wape_base * 100, 1), 'WAPE_읍면동지수': round(wape_ours * 100, 1)},
    '80퍼센트도달산술억': round(gap_won / 1e8),
    '최근12개월정점': {'입도': peak(ipdo), '한라산': peak(halla)},
    '한라산누락월': halla_gap,
    '실행초': round(elapsed, 2),
    '입력행수': {f: len(R(f)) for f in sorted(os.listdir(D))},
}
os.makedirs(os.path.join(OUT, 'docs'), exist_ok=True)
with open(os.path.join(OUT, 'docs', 'data.json'), 'w', encoding='utf-8') as h:
    json.dump({'기준': '2025-08~2026-07', '카드': cards}, h, ensure_ascii=False, separators=(',', ':'))
with open(os.path.join(OUT, '결과.json'), 'w', encoding='utf-8') as h:
    json.dump(result, h, ensure_ascii=False, indent=1)
tpl = open(os.path.join(OUT, 'docs', 'template.html'), encoding='utf-8').read()
data = open(os.path.join(OUT, 'docs', 'data.json'), encoding='utf-8').read()
with open(os.path.join(OUT, 'docs', 'index.html'), 'w', encoding='utf-8') as h:
    h.write(tpl.replace('__DATA__', data))
print(json.dumps(result, ensure_ascii=False))
