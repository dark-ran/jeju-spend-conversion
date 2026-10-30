import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family']='Noto Sans CJK JP'; plt.rcParams['axes.spines.top']=False; plt.rcParams['axes.spines.right']=False
d=json.load(open('docs/data.json',encoding='utf-8'))['카드']; d=[c for c in d if c['등급']!='표본 작음']
W='#C2410C'; G='#A8A29E'; K='#44403C'
d.sort(key=lambda c:c['지수'][2])
f,a=plt.subplots(figsize=(7.2,8.6),dpi=170)
for i,c in enumerate(d):
    w=c['등급']=='구조적 전환 부족'
    a.plot([1,c['지수'][2]],[i,i],color=W if w else G,lw=2,solid_capstyle='round',zorder=2)
    a.plot(c['지수'][2],i,'o',ms=6,color=W if w else G,zorder=3)
a.set_yticks(range(len(d))); a.set_yticklabels([c['이름'] for c in d],fontsize=8.5,color=K)
a.axvline(1,color=K,lw=.8); a.axvline(.8,color=K,lw=.8,ls=(0,(3,3)))
a.text(1.01,-1.3,'제주 평균 1.0',fontsize=8,color=K); a.text(.79,len(d)-.2,'기준 0.8',fontsize=8,color=K,ha='right')
a.set_xlabel('방문 1회당 관광 소비 지수 (2025-08~2026-07)',fontsize=9,color=K); a.grid(axis='x',color='#E7E5E4',lw=.6); a.set_axisbelow(True); a.set_ylim(-1.8,len(d)+.3)
a.tick_params(length=0); a.spines['left'].set_visible(False)
a.text(1.0,.03,'주황: 2년 연속 0.8 미만(구조적 전환 부족)',transform=a.transAxes,ha='right',fontsize=9,color=W)
f.tight_layout(); f.savefig('figures/fig1_지수순위.png')
f,a=plt.subplots(figsize=(6,5),dpi=170)
for c in d:
    w=c['등급']=='구조적 전환 부족'
    a.plot(c['지수'][0],c['지수'][2],'o',ms=6,color=W if w else G,mec='white',mew=1)
m=max(max(c['지수'][0],c['지수'][2]) for c in d)
a.plot([0,m],[0,m],color=K,lw=.8,ls=(0,(3,3))); a.set_xlabel('2년 전 지수 (2023-08~2024-07)',fontsize=9,color=K); a.set_ylabel('최근 지수 (2025-08~2026-07)',fontsize=9,color=K)
for c in d:
    if c['이름'] in('일도1동','용담2동','이호동','이도1동','중앙동','노형동','한경면'): a.annotate(c['이름'],(c['지수'][0],c['지수'][2]),xytext=(6,3),textcoords='offset points',fontsize=8,color=K)
a.grid(color='#E7E5E4',lw=.6); a.set_axisbelow(True); f.tight_layout(); f.savefig('figures/fig2_시간분리.png')
