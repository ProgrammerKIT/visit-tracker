import sys,pickle; sys.path.insert(0,'/home/claude/scripts')
from engine import *
R,G,w,R9=pickle.load(open('data/R.pkl','rb'))
L,P='2026-10','2026-09'
def ranks(sku):
    g=G[sku]; out=[]
    for c in CODES:
        cur=g.loc[c,L]; prv=g.loc[c,P]; hist=g.loc[c,:P].dropna()
        out.append(dict(c=c,n=short(c),prv=prv,cur=cur,inc=cur-prv,rate=(cur-prv)/prv if prv>0 else np.nan,nh=cur>hist.max() if len(hist) else False,histmax=hist.max()))
    d=pd.DataFrame(out)
    r1=d[d.prv>0].sort_values(['rate','inc','c'],ascending=[False,False,True]).head(7)
    r2=d.sort_values(['inc','rate','c'],ascending=[False,False,True]).head(7)
    r3=d.sort_values(['cur','inc','c'],ascending=[False,False,True]).head(7)
    print('==',sku); 
    for nm,r in [('R1',r1),('R2',r2),('R3',r3)]: print(nm); print(r[['c','n','prv','cur','inc','rate','nh','histmax']].to_string(index=False))
    print('newhigh all', d[d.nh][['n','cur','histmax']].to_string(index=False))
    return d
dH=ranks('HAUD'); dC=ranks('Complete')
# per-store SKU detail for some
for c in ['1318','1322','1204','1608','A1107','1601','A1118','1309']:
    print(c,short(c)); print(pd.DataFrame({s:G[s].loc[c,'2026-05':] for s in SKUS}).T.astype(int).to_string())
