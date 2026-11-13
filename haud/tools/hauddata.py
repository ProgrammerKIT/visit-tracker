#!/usr/bin/env python3
"""佑全 HAUD Offtake 讀檔與清理（規則主檔 第零步、第一步；歷史裁定第 1、2、5、6、12 條）。
不含任何資料；原始 Excel 由使用者每期上傳，不得推送至 repo。"""
import re
import pandas as pd

SKUS = ['HAUD', 'HAMD', 'Ultra UD', 'Ultra MD', 'Complete', 'TN', 'TNF']
BASE = ['2025-09', '2025-10', '2025-11']          # 固定基期（不滾動）
CLOSED = {'1202': '2026-06'}                       # 歇業店：自該月起退出（歷史裁定第 1 條）
JOINED = {'1703': '2025-12'}                       # 新加入店：加入前月份不在體系（第 2、7 條）
ALT_BASE = {'1703': ['2025-12', '2026-01', '2026-02']}  # 替代基期（第 7 條；HAUD 為 0 時成長率標不適用）
TN_EXCLUDED = {'A1107'}                            # 門市特註：TN 池不列為轉單素材（事實表〈門市特註〉①）


def load_raw(path):
    df = pd.read_excel(path).dropna(how='all')
    df = df.iloc[:, :4]
    df.columns = ['ym', 'sku', 'store', 'qty']
    df['ym'] = df['ym'].astype(str).str[:7]
    df['code'] = df['store'].astype(str).str.extract(r'^([A-Z]?\d+)')[0]
    return df


def names(raw):
    """店碼→中文名稱（優先取含「佑全」者；去店碼前綴）。"""
    out = {}
    for c, s in raw.groupby('code')['store'].unique().items():
        s = sorted(s, key=lambda x: ('佑全' not in x))
        out[c] = s[0][len(c):]
    return out


def short(name):
    return name[:-2] if name.endswith('藥局') else name


def clean(raw):
    """同店＋同 SKU＋同年月加總合併（第 5 條）；同店異名以店碼合併（第 12 條，第零步須先經 Kit 確認）。"""
    return raw.groupby(['ym', 'sku', 'code'], as_index=False)['qty'].sum()


def step0_report(raw):
    """第零步機械性檢查；結果交決策表由 Kit 確認（不在此自動裁定）。"""
    m = clean(raw)
    months = sorted(raw.ym.unique())
    g = raw.groupby(['ym', 'sku', 'code']).agg(n=('qty', 'size'), q=('qty', 'sum')).reset_index()
    dup = g[g.n > 1]
    alias = {c: list(s) for c, s in raw.groupby('code')['store'].unique().items() if len(s) > 1}
    latest, prev = months[-1], months[-2]
    act = m[~m.code.isin(CLOSED)]
    piv = act.pivot_table(index=['sku', 'code'], columns='ym', values='qty', aggfunc='sum')
    zero = []
    if prev in piv.columns and latest in piv.columns:
        z = piv[(piv[prev] >= 4) & (piv[latest].fillna(0) == 0)]
        zero = [(s, c, float(z.loc[(s, c), prev])) for s, c in z.index]
    # S6：前後月有量而本月為 0（含缺列）
    s6 = []
    if len(months) >= 2:
        for (s, c), row in piv.iterrows():
            if row.get(prev, 0) and row.get(prev, 0) > 0 and not (row.get(latest, 0) > 0):
                s6.append((s, c, float(row.get(prev, 0))))
    return {
        'months': months, 'latest': latest, 'skus': sorted(raw.sku.unique()),
        'unknown_skus': sorted(set(raw.sku.unique()) - set(SKUS)),
        'stores_per_month': m.groupby('ym').code.nunique().to_dict(),
        'active_latest': int(act[act.ym == latest].code.nunique()),
        'negatives': int((raw.qty < 0).sum()),
        'dup_groups_by_month': dup.groupby('ym').size().to_dict(),
        'dup_latest': dup[dup.ym == latest][['sku', 'code', 'n', 'q']].values.tolist(),
        'dup_max_rows': int(g.n.max()),
        'alias': alias,
        'big30_latest': m[(m.ym == latest) & (m.qty >= 30)][['sku', 'code', 'qty']].values.tolist(),
        'closed_reappeared': m[m.code.isin(CLOSED) & (m.ym >= min(CLOSED.values()))][['ym', 'code', 'qty']].values.tolist(),
        'zero_ge4_to_0': zero,
        'S6_zero_after_sales': s6,
        'notes': sorted({x for x in list(raw.sku.unique()) + list(raw.store.unique()) if re.search('缺貨|換包', str(x))}),
    }
