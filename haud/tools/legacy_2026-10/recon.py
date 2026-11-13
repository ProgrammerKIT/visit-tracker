import pandas as pd, numpy as np
m=pd.read_pickle('data/m.pkl')
raw=pd.read_excel('data/offtake_202610.xlsx'); raw.columns=['ym','sku','store','qty']; raw['ym']=raw.ym.astype(str).str[:7]
raw['code']=raw.store.str.extract(r'^([A-Z]?\d+)')
print(raw[raw.qty==0])
# dup detail 2026-10
g=raw[raw.ym=='2026-10'].groupby(['sku','code'])
for k,x in g:
    if len(x)>1: print(k, x.qty.tolist(), x.store.tolist())
# HAUD dups historically?
gg=raw.groupby(['ym','sku','code']).size(); print(gg[gg>1].reset_index().groupby(['ym','sku']).size())
months=sorted(m.ym.unique())
piv=m.pivot_table(index='sku',columns='ym',values='qty',aggfunc='sum',fill_value=0)
act=m[m.code!='1202']
print(piv.to_string()); print('total',piv.sum().to_dict())
pa=act.pivot_table(index='sku',columns='ym',values='qty',aggfunc='sum',fill_value=0)
print('active HAUD',pa.loc['HAUD'].to_dict())
codes=sorted(act.code.unique()); print(len(codes),codes)
names=raw.groupby('code').store.first()
# full grid
def grid(sku,upto):
    ms=[x for x in months if x<=upto]
    p=act[act.sku==sku].pivot_table(index='code',columns='ym',values='qty',aggfunc='sum').reindex(index=codes,columns=ms).fillna(0)
    p.loc['1703',[x for x in ms if x<'2025-12']]=np.nan
    return p
# 2-b ②
for s in sorted(m.sku.unique()):
    p=grid(s,'2026-10')
    hit=p[(p['2026-09']>=4)&(p['2026-10']==0)]
    for c in hit.index: print('ZERO',s,c,names[c],p.loc[c,'2026-09'])
# recovery gap 09 window
def gap(upto,recent):
    p=grid('HAUD',upto); tot=0; rows=[]
    for c in p.index:
        if c=='1703': continue
        pk=p.loc[c].max(); r=p.loc[c,recent].mean(); v=max(0,pk*0.85-r); tot+=v; rows.append((c,pk,round(r,2),round(v,2)))
    return tot,rows
t,r=gap('2026-09',['2026-07','2026-08','2026-09']); print('gap09',round(t,4))
t2,r2=gap('2026-10',['2026-08','2026-09','2026-10']); print('gap10',round(t2,4))
# store-level HAUD 09 and 10
p=grid('HAUD','2026-10'); print(p[['2026-07','2026-08','2026-09','2026-10']].assign(name=[names[c] for c in p.index]).to_string())
