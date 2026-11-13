import pandas as pd, sys, re, numpy as np
df=pd.read_excel(sys.argv[1]).dropna(how='all')
df.columns=['ym','sku','store','qty']
df['ym']=df['ym'].astype(str).str[:7]
print('months',sorted(df.ym.unique()))
print('skus',sorted(df.sku.unique()))
print('qty min/max',df.qty.min(),df.qty.max(), 'neg',(df.qty<0).sum(), 'zero rows',(df.qty==0).sum())
df['code']=df.store.str.extract(r'^([A-Z]?\d+)')
names=df.groupby('code').store.unique()
for c,n in names.items():
    if len(n)>1: print('ALIAS',c,list(n), df[df.store.isin(n)].groupby(['store','ym']).size().unstack(fill_value=0).to_dict('index') if False else df[df.store.isin(n)].groupby('store').ym.unique().apply(lambda x:sorted(x)).to_dict())
print('codes',len(names))
# alias rows count per month
for c,n in names.items():
    if len(n)>1:
        for s in n: print(s, df[df.store==s].groupby('ym').size().to_dict())
# skus names text with notes
for s in df.sku.unique(): 
    if re.search('缺貨|換包',s): print('NOTE',s)
for s in df.store.unique():
    if re.search('缺貨|換包',s): print('NOTE',s)
# duplicates
d=df.groupby(['ym','sku','code']).size()
dup=d[d>1]
print('dup groups by ym'); print(dup.groupby(level=0).size())
print('dup by sku for 2026-10'); 
if '2026-10' in dup.index.get_level_values(0): print(dup.loc['2026-10'])
print('max rows in a group',d.max())
# merge
m=df.groupby(['ym','sku','code'],as_index=False).qty.sum()
# check dup sums >=30
g=df.groupby(['ym','sku','code']).agg(n=('qty','size'),q=('qty','sum')).reset_index()
print('dup groups sum>=30',g[(g.n>1)&(g.q>=30)])
# stores per month
print(m.groupby('ym').code.nunique())
print('1202 after 2026-05:',m[(m.code=='1202')&(m.ym>='2026-06')])
# >=30
big=m[m.qty>=30]; print(big.sort_values('ym'))
m.to_pickle('data/m.pkl')
