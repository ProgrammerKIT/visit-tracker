#!/usr/bin/env python3
"""交付前總檢查（規則主檔〈本期交付物檢查表〉一）。任一失敗 exit 1，必須停止交付。
用法：python3 gate.py --latest 2026-11 --json <App檔> [--json <第二份>] --index index.html \
        --ledger 佑全_期別帳本.md [--facts 佑全_事實表.md] [--rules 規則主檔.md] \
        [--contract-version 2.1] [--haud-total 205] [--excel <本期Excel>]
"""
import argparse, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
CODE = re.compile(r'(?<![0-9A-Za-z.\-/`_])([A-Z]\d{4}|1\d{3})(?![0-9\-年月日盒家%．.])')  # 店碼型態；排除年份、日期與數量
CJK = re.compile(r'[一-鿿]')


def run(args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=HERE)
    return r.returncode, (r.stdout + r.stderr).strip()


def bare_codes(text):
    """回傳未與中文名稱相連之店碼（店碼後 1 字內無中文、且前方括號外無中文名稱）。"""
    hits = []
    for m in CODE.finditer(text):
        after = text[m.end():m.end() + 1]
        before = text[max(0, m.start() - 1):m.start()]
        if CJK.match(after or ' ') or before in '（(':
            continue
        hits.append(text[max(0, m.start() - 12):m.end() + 6].replace('\n', ' '))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--latest', required=True); ap.add_argument('--json', action='append', default=[])
    ap.add_argument('--index'); ap.add_argument('--ledger'); ap.add_argument('--facts'); ap.add_argument('--rules')
    ap.add_argument('--contract-version'); ap.add_argument('--haud-total'); ap.add_argument('--excel')
    a = ap.parse_args(); fails, notes = [], []

    for j in a.json:
        d = json.load(open(j, encoding='utf-8'))
        if 'format' in d:
            rc, out = run(['alert_v2_validate.py', j]); (fails if rc else notes).append(f'[v2 自檢] {os.path.basename(j)}：{out}')
        else:
            bad = [s.get('name') for s in d.get('stores', []) if set(s) != {'name', 'channel', 'reason', 'checkpoints'}]
            (fails if bad or set(d) != {'stores'} else notes).append(f'[v1 格式] {os.path.basename(j)}：' + ('鍵不符 ' + str(bad) if bad or set(d) != {'stores'} else '通過'))
        rc, out = run(['timeliness_check.py', a.latest, j] + ([a.index] if a.index else []) + ([a.ledger] if a.ledger and a.index else []))
        (fails if rc else notes).append(f'[時效] {os.path.basename(j)}：{out}')
        for s in d.get('stores', []):
            txt = s.get('reason', '') + '\n'.join(s.get('checkpoints', [])) + '\n'.join(c.get('label', '') for c in s.get('checks', [])) + (s.get('previousResult') or '')
            h = bare_codes(txt)
            if h: fails.append(f'[門市稱呼] {s.get("name")} 內文獨立店碼：{h[:5]}')
        if a.index:
            idx = open(a.index, encoding='utf-8').read()
            miss = [s.get('storeCode') or re.match(r'^[A-Z]?\d+', s['name']).group(0) for s in d.get('stores', [])]
            miss = [c for c in miss if c not in idx]
            (fails if miss else notes).append(f'[跨檔] App 名單店碼皆見於 index.html：' + ('缺 ' + str(miss) if miss else '通過'))

    for f in [a.ledger, a.facts, a.rules]:
        if not f: continue
        t = open(f, encoding='utf-8').read()
        body = t.split('# 附錄：', 1)[0].split('# 完整版本沿革', 1)[0]  # 追溯區不檢查
        if a.contract_version:
            old = sorted({v for v in re.findall(r'閉環資料契約[〉》]?[（(]v?(\d+\.\d+)', body) if v != a.contract_version})
            if old: fails.append(f'[版號引用] {os.path.basename(f)} 引用過期契約版號 {old}（現行 {a.contract_version}）')
        if a.haud_total and f == a.ledger and a.haud_total not in body:
            fails.append(f'[跨檔] 期別帳本未見本期 HAUD 月總量 {a.haud_total}')
    if a.haud_total and a.index and a.haud_total not in open(a.index, encoding='utf-8').read():
        fails.append(f'[跨檔] index.html 未見本期 HAUD 月總量 {a.haud_total}')
    if a.excel:
        rc, out = run(['regress.py', a.excel]); (fails if rc else notes).append(f'[回歸] {out}')

    for n in notes: print('✅', n)
    for f in fails: print('❌', f)
    print('總檢查：' + ('失敗，停止交付' if fails else '通過'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
