import pandas as pd, sys
df=pd.read_excel(sys.argv[1],sheet_name=0)
print(df.columns.tolist()); print(df.head(10)); print(len(df))
df=df.dropna(how='all'); print('nonblank',len(df))
for c in df.columns: print(c, df[c].dtype, df[c].nunique())
