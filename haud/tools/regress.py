#!/usr/bin/env python3
"""M1 回歸測試：以新檔重跑既往期別，與 regress/<期別>.json 期望值比對。
  建立期望值：python3 regress.py --build <Excel> <期別>      （僅在該期裁定定案後執行）
  比對：      python3 regress.py <本期新檔>                   （對 regress/ 內全部期別）
差異分兩類回報：①月合計不同＝原始檔歷史月份被改寫 ②月合計相同但判定不同＝程式或口徑改動。exit 1 表示有差異。"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hauddata import load_raw, clean, SKUS, CLOSED
from engine import analyze

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'regress')


def snapshot(m, latest):
    R, s = analyze(m, latest)
    act = m[~m.code.isin(CLOSED)]
    mt = act[act.ym <= latest].groupby(['ym', 'sku']).qty.sum().unstack().reindex(columns=SKUS).fillna(0)
    return {
        'latest': latest,
        'monthly_totals': {ym: {k: float(v) for k, v in row.items()} for ym, row in mt.iterrows()},
        'n_active': s['n_active'],
        'recgap_total': round(s['recgap_total'], 2),
        'r_complete_haud': round(s['r_complete_haud'], 3),
        'pool_B': round(s['pool_B'], 2), 'pool_C': round(s['pool_C'], 2),
        'micro': s['micro'],
        'stores': {c: {'M': d['M'], 'N': d['N'], 'move': round(d['move'], 2)} for c, d in R.items()},
    }


def compare(exp, got):
    diffs = {'restatement': [], 'logic': []}
    for ym, row in exp['monthly_totals'].items():
        g = got['monthly_totals'].get(ym)
        if g != row:
            diffs['restatement'].append(f'{ym} 月合計：期望 {row}，新檔 {g}')
    for k in ('n_active', 'recgap_total', 'r_complete_haud', 'pool_B', 'pool_C', 'micro'):
        if exp[k] != got[k]:
            diffs['logic'].append(f'{k}：期望 {exp[k]}，現為 {got[k]}')
    for c, v in exp['stores'].items():
        if got['stores'].get(c) != v:
            diffs['logic'].append(f'店碼 {c}：期望 {v}，現為 {got["stores"].get(c)}')
    return diffs


def main(a):
    if a[0] == '--build':
        m = clean(load_raw(a[1])); os.makedirs(D, exist_ok=True)
        snap = snapshot(m, a[2])
        json.dump(snap, open(os.path.join(D, a[2] + '.json'), 'w'), ensure_ascii=False, indent=1)
        print('已建立', a[2]); return 0
    m = clean(load_raw(a[0])); bad = 0
    for f in sorted(os.listdir(D)):
        if not f.endswith('.json'): continue
        exp = json.load(open(os.path.join(D, f)))
        diffs = compare(exp, snapshot(m, exp['latest']))
        if diffs['restatement'] or diffs['logic']:
            bad = 1
            print(f'❌ {exp["latest"]}：原始檔歷史改寫 {len(diffs["restatement"])} 項、判定差異 {len(diffs["logic"])} 項')
            for x in diffs['restatement'] + diffs['logic']: print('   -', x)
        else:
            print(f'✅ {exp["latest"]}：與期望值一致')
    return bad


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
