#!/usr/bin/env python3
"""佑全 HAUD 分析引擎（參數化；規則主檔 第一～四步）。
用法：
  from hauddata import load_raw, clean, names; from engine import analyze
  R = analyze(clean(load_raw(xlsx)), latest='2026-10')
只計算規則定義之數值與 M／N 判定；鎖定表、特註覆寫與人工裁定不在此套用（見事實表）。"""
import numpy as np
import pandas as pd
from hauddata import SKUS, BASE, CLOSED, JOINED, TN_EXCLUDED


def _window(months, latest):
    ms = [x for x in months if x <= latest]
    return ms, ms[-3:], ms[-6:-3]


def grids(m, latest):
    act = m[~m.code.isin(CLOSED)]
    months = sorted(m.ym.unique())
    ms, _, _ = _window(months, latest)
    codes = sorted(act.code.unique())
    G = {}
    for s in SKUS:
        p = act[act.sku == s].pivot_table(index='code', columns='ym', values='qty', aggfunc='sum') \
            .reindex(index=codes, columns=ms).fillna(0)
        for c, start in JOINED.items():
            if c in p.index:
                p.loc[c, [x for x in ms if x < start]] = np.nan
        G[s] = p
    return G, codes, ms


def analyze(m, latest):
    G, codes, ms = grids(m, latest)
    _, rec, pri = _window(ms, latest)
    H, C, T = G['HAUD'], G['Complete'], G['TN'] + G['TNF']
    R = {}
    for c in codes:
        h = H.loc[c].dropna()
        new = c in JOINED and any(b < JOINED[c] for b in BASE)
        d = {'series': [float(x) for x in h.values]}
        d['mean'] = float(h.mean())
        d['cv'] = float(h.std(ddof=0) / h.mean()) if h.mean() > 0 else float('nan')
        d['peak'] = float(h.max())
        d['micro'] = bool(h.mean() < 3)
        d['new'] = new
        for k, w in (('rec', rec), ('pri', pri)):
            d[k + '_m'] = float(H.loc[c, w].mean()); d[k + '_md'] = float(H.loc[c, w].median())
        d['base_m'] = float('nan') if new else float(H.loc[c, BASE].mean())
        d['base_md'] = float('nan') if new else float(H.loc[c, BASE].median())
        d['c_m'] = float(C.loc[c, rec].mean()); d['c_md'] = float(C.loc[c, rec].median())
        d['t_m'] = float(T.loc[c, rec].mean()); d['t_md'] = float(T.loc[c, rec].median())

        def stage(med):
            r = d['rec_md'] if med else d['rec_m']; p = d['pri_md'] if med else d['pri_m']
            b = d['base_md'] if med else d['base_m']
            cm = d['c_md'] if med else d['c_m']; tm = d['t_md'] if med else d['t_m']
            Bc = cm >= 4 and cm - r >= 2
            Cc = tm >= max(r, 2)
            if d['micro'] or new:
                return 'C' if Cc else ('B' if Bc else 'E')
            if not med:
                if r < p - 0.8 and r < b and max(b, p) >= 3: return 'A'
                if r > p + 0.8 and r >= b and d['cv'] < 0.7: return 'D'
            else:
                if r <= b * 0.85 and abs(b - r) >= 1.5 and r < p + 0.5 and b >= 3: return 'A'
                if r >= p + 1 and r >= b and d['cv'] < 0.7: return 'D'
            if Bc: return 'B'
            if Cc: return 'C'
            return 'E'
        d['M'] = stage(False); d['N'] = stage(True)
        d['Bcond'] = d['c_m'] >= 4 and d['c_m'] - d['rec_m'] >= 2
        d['Ccond'] = d['t_m'] >= max(d['rec_m'], 2)
        d['recgap'] = 0.0 if new else max(0.0, d['peak'] * 0.85 - d['rec_m'])
        d['cgap'] = max(0.0, d['c_m'] - d['rec_m'])
        d['mult'] = d['t_m'] / d['rec_m'] if d['rec_m'] > 0 else float('inf')
        d['tnterm'] = 0.0 if c in TN_EXCLUDED else 0.25 * d['t_m'] * min(d['mult'] / 2, 1)
        d['move'] = d['recgap'] + 0.4 * d['cgap'] + d['tnterm']
        R[c] = d
    act_m = m[~m.code.isin(CLOSED)]
    tot = act_m[act_m.ym == latest].groupby('sku').qty.sum().reindex(SKUS).fillna(0)
    xs = [R[c]['c_m'] for c in codes]; ys = [R[c]['rec_m'] for c in codes]
    summary = {
        'latest': latest, 'rec': rec, 'pri': pri, 'n_active': len(codes),
        'sku_totals_latest': {k: float(v) for k, v in tot.items()},
        'recgap_total': sum(R[c]['recgap'] for c in codes),
        'r_complete_haud': float(np.corrcoef(xs, ys)[0, 1]),
        'pool_B': sum(R[c]['c_m'] - R[c]['rec_m'] for c in codes if R[c]['Bcond']),
        'pool_C': sum(R[c]['t_m'] for c in codes if R[c]['Ccond']),
        'n_pool_B': sum(1 for c in codes if R[c]['Bcond']),
        'n_pool_C': sum(1 for c in codes if R[c]['Ccond']),
        'micro': [c for c in codes if R[c]['micro']],
        'top10_move': sorted(((c, R[c]['move']) for c in codes), key=lambda x: -x[1])[:10],
    }
    return R, summary
