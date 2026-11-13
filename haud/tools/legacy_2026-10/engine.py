import pandas as pd, numpy as np
m=pd.read_pickle('/home/claude/data/m.pkl')
m=m[m.code!='1202']
raw=pd.read_excel('/home/claude/data/offtake_202610.xlsx'); raw.columns=['ym','sku','store','qty']
raw['code']=raw.store.str.extract(r'^([A-Z]?\d+)')
NAME={}
for c,s in raw.groupby('code').store.unique().items():
    s=sorted(s,key=lambda x:('佑全' not in x)); NAME[c]=s[0][len(c):]
CODES=sorted(m.code.unique())
ALLM=sorted(m.ym.unique())
SKUS=['HAUD','HAMD','Ultra UD','Ultra MD','Complete','TN','TNF']
def short(c):  # name without 藥局
    n=NAME[c]; return n[:-2] if n.endswith('藥局') else n
def grid(sku,upto):
    ms=[x for x in ALLM if x<=upto]
    p=m[m.sku==sku].pivot_table(index='code',columns='ym',values='qty',aggfunc='sum').reindex(index=CODES,columns=ms).fillna(0)
    p.loc['1703',[x for x in ms if x<'2025-12']]=np.nan
    return p
def prevm(ym,k):
    i=ALLM.index(ym); return ALLM[i-k]
def analyze(latest):
    ms=[x for x in ALLM if x<=latest]
    rec=ms[-3:]; pri=ms[-6:-3]; base=['2025-09','2025-10','2025-11']
    G={s:grid(s,latest) for s in SKUS}
    H=G['HAUD']; C=G['Complete']; T=G['TN']+G['TNF']
    R={}
    for c in CODES:
        h=H.loc[c].dropna(); d={}
        d['series']=h
        d['mean']=h.mean(); d['cv']=h.std(ddof=0)/h.mean() if h.mean()>0 else np.nan
        d['peak']=h.max(); d['micro']=h.mean()<3
        newstore = c=='1703'
        d['new']=newstore
        d['rec_m']=H.loc[c,rec].mean(); d['rec_md']=H.loc[c,rec].median()
        d['pri_m']=H.loc[c,pri].mean(); d['pri_md']=H.loc[c,pri].median()
        d['base_m']=np.nan if newstore else H.loc[c,base].mean(); d['base_md']=np.nan if newstore else H.loc[c,base].median()
        d['c_m']=C.loc[c,rec].mean(); d['c_md']=C.loc[c,rec].median()
        d['t_m']=T.loc[c,rec].mean(); d['t_md']=T.loc[c,rec].median()
        # M
        def stage(useMed):
            r=d['rec_md'] if useMed else d['rec_m']; p=d['pri_md'] if useMed else d['pri_m']; b=d['base_md'] if useMed else d['base_m']
            cm=d['c_md'] if useMed else d['c_m']; tm=d['t_md'] if useMed else d['t_m']
            Bc = cm>=4 and cm-r>=2; Cc= tm>=max(r,2)
            if d['micro'] or newstore:
                return 'C' if Cc else ('B' if Bc else 'E')
            if not useMed:
                if r<p-0.8 and r<b and max(b,p)>=3: return 'A'
                if r>p+0.8 and r>=b and d['cv']<0.7: return 'D'
            else:
                if r<=b*0.85 and abs(b-r)>=1.5 and r<p+0.5 and b>=3: return 'A'
                if r>=p+1 and r>=b and d['cv']<0.7: return 'D'
            if Bc: return 'B'
            if Cc: return 'C'
            return 'E'
        d['M']=stage(False); d['N']=stage(True)
        d['Bcond']= d['c_m']>=4 and d['c_m']-d['rec_m']>=2
        d['Ccond']= d['t_m']>=max(d['rec_m'],2)
        d['recgap']=0 if newstore else max(0,d['peak']*0.85-d['rec_m'])
        d['cgap']=max(0,d['c_m']-d['rec_m'])
        d['mult']= d['t_m']/d['rec_m'] if d['rec_m']>0 else np.inf
        tn=0.25*d['t_m']*min(d['mult']/2,1)
        if c=='A1107': tn=0
        d['tnterm']=tn
        d['move']=d['recgap']+0.4*d['cgap']+tn
        R[c]=d
    return R,G,dict(rec=rec,pri=pri)
