#!/usr/bin/env python3
"""佑全 App 回報讀取器（分析端，契約 v2.0 匯出 yq-report-1）

用法：python3 report_reader.py <匯出.json> <已交付原檔資料夾> [--sync-confirmed] [--json 輸出.json]

已交付原檔資料夾：存放分析端每次交付給 Kit 的警示 JSON「原始位元組」（不得重新排版）。
任何一項核對失敗即以 exit code 2 停止，列出原因，交 Kit 核對；不猜測、不補值。
--sync-confirmed：Kit 於第零步確認「本匯出係在 Mac 同步完成後產生」；未給則 not_visited 一律列為未知。
"""
import hashlib, json, os, sys, re

ROOT = ['format', 'exportedAt', 'appVersion', 'channel', 'visitMonth', 'analysisSources', 'stores']
SRC = ['sourceId', 'salesMonth', 'file', 'blob', 'format']
STORE = ['storeCode', 'analysisName', 'appStoreId', 'appStoreName', 'mapping', 'status', 'reports']
REPORT = ['reportId', 'revisionId', 'sourceId', 'attendanceDate', 'noteDate', 'savedAt', 'answers', 'note']
STATUS = {'unmapped', 'not_visited', 'visited_no_report', 'reported'}


class Stop(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise Stop(msg)


def keys_exact(obj, keys, where):
    need(isinstance(obj, dict) and set(obj) == set(keys),
         f'{where} 欄位不符：應為 {keys}，實為 {list(obj) if isinstance(obj, dict) else type(obj).__name__}')


def ledger(folder):
    out = {}
    for name in sorted(os.listdir(folder)):
        p = os.path.join(folder, name)
        if os.path.isfile(p) and name.endswith('.json'):
            raw = open(p, 'rb').read()
            out[hashlib.sha256(raw).hexdigest()] = (name, raw)
    return out


def definitions(source_doc):
    """回傳 {storeCode: {questionId: definition}}，定義取自原檔。"""
    core = {c['id']: c for c in source_doc['coreChecks']}
    res = {}
    for s in source_doc['stores']:
        d = dict(core)
        for c in s['checks']:
            d[c['id']] = c
        res[s['storeCode']] = d
    return res


def check_value(defn, ans, where):
    v = ans.get('value')
    if v is None:
        return
    t = defn['type']
    if t == 'number':
        need(isinstance(v, (int, float)) and not isinstance(v, bool), f'{where} 數值題非數字：{v!r}')
        if defn['id'] == 'core.shelf_haud':
            need(float(v).is_integer(), f'{where} 盒數非整數：{v!r}')
        if 'min' in defn: need(v >= defn['min'], f'{where} 小於下限：{v!r}')
        if 'max' in defn: need(v <= defn['max'], f'{where} 大於上限：{v!r}')
    elif t == 'single':
        need(v in defn['options'], f'{where} 選項不在定義內：{v!r}')
    elif t == 'yesno':
        need(v in ('是', '否', '未確認'), f'{where} 是非題值不合：{v!r}')
    elif t == 'text':
        need(isinstance(v, str) and v.strip(), f'{where} 文字題為空白：{v!r}')
    if 'otherText' in ans:
        need(defn['id'] == 'core.push_sku' and v == '其他', f'{where} otherText 只能附於主推「其他」')


def _merge_latest(latest):
    """同 id 只有一種定義 → 單一值；定義不同 → 依定義分開列為清單，不合併。"""
    out = {}
    for (q, dj), v in latest.items():
        out.setdefault(q, []).append({**v, 'definition': json.loads(dj)})
    return {q: (vs[0] if len(vs) == 1 else vs) for q, vs in out.items()}


def read(export_path, ledger_dir, sync_confirmed=False):
    doc = json.load(open(export_path, encoding='utf-8'))
    keys_exact(doc, ROOT, '根物件')
    need(doc['format'] == 'yq-report-1', f'format 應為 yq-report-1，實為 {doc["format"]}')
    need(doc['channel'] == '佑全', '通路不是佑全')
    need(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', doc['visitMonth'] or ''), 'visitMonth 格式錯誤')
    led = ledger(ledger_dir)
    sources, defs = {}, {}
    for i, s in enumerate(doc['analysisSources']):
        keys_exact(s, SRC, f'analysisSources[{i}]')
        need(s['format'] == 'yq-alert-2', f'來源 {s["file"]} 非 yq-alert-2')
        need(s['blob'] in led, f'來源 {s["file"]}（SHA-256 {s["blob"][:12]}…）在分析端已交付原檔中找不到——可能是匯入了被改動或非分析端交付的檔案，請 Kit 核對')
        name, raw = led[s['blob']]
        src = json.loads(raw.decode('utf-8-sig'))
        need(src.get('visitMonth') == doc['visitMonth'], f'來源 {name} 之 visitMonth 與匯出不符')
        need(src.get('salesMonth') == s['salesMonth'], f'來源 {name} 之 salesMonth 與匯出不符')
        need(s['sourceId'] not in sources, f'sourceId 重複：{s["sourceId"]}')
        sources[s['sourceId']] = (name, src)
        defs[s['sourceId']] = definitions(src)
    rows, seen = [], set()
    for i, st in enumerate(doc['stores']):
        w = f'stores[{i}]（{st.get("analysisName")}）'
        keys_exact(st, STORE, w)
        need(st['storeCode'] not in seen, f'{w} 店碼重複'); seen.add(st['storeCode'])
        need(st['status'] in STATUS, f'{w} status 不合：{st["status"]}')
        need(st['mapping'] in ('confirmed', 'skipped'), f'{w} mapping 不合')
        need((st['status'] == 'reported') == bool(st['reports']), f'{w} status 與 reports 不一致')
        need((st['mapping'] == 'skipped') == (st['status'] == 'unmapped'), f'{w} mapping 與 status 不一致')
        reps = []
        for j, r in enumerate(st['reports']):
            rw = f'{w}.reports[{j}]'
            keys_exact(r, REPORT, rw)
            need(r['sourceId'] in sources, f'{rw} sourceId 不在 analysisSources 內')
            d = defs[r['sourceId']].get(st['storeCode'])
            need(d is not None, f'{rw} 來源原檔沒有店碼 {st["storeCode"]}')
            need(set(r['answers']) == set(d), f'{rw} 題目集合與來源原檔不符')
            for qid, ans in r['answers'].items():
                need(isinstance(ans, dict) and 'value' in ans, f'{rw}.{qid} 結構錯誤')
                if qid.startswith('c.'):
                    need(ans.get('question') == d[qid]['label'], f'{rw}.{qid} 題目文字快照與原檔不符')
                check_value(d[qid], ans, f'{rw}.{qid}')
            note = r['note']
            need(set(note) == {'included', 'text', 'next'}, f'{rw}.note 結構錯誤')
            if not note['included']:
                need(note['text'] == '' and note['next'] == '', f'{rw}.note 已勾除卻仍有文字')
            answered = [q for q, a in r['answers'].items() if a['value'] is not None]
            # 有效證據：人工到店確認、任一題有答、或附有筆記文字
            effective = bool(r['attendanceDate'] or answered or (note['included'] and note['text'].strip()))
            order = (r['attendanceDate'] or r['noteDate'] or r['savedAt'][:10], r['savedAt'], r['reportId'])  # 先依實際日期（到店→筆記→保存日），再依保存時間
            reps.append({**r, '_answered': answered, '_effective': effective, '_order': order,
                         '_defs': {q: json.dumps(d[q], ensure_ascii=False, sort_keys=True) for q in r['answers']}})
        reps.sort(key=lambda x: x['_order'])
        # 逐題取最後一次非 null；同 id 但定義不同者視為不同題，分開保留
        latest = {}
        for r in reps:
            for q, a in r['answers'].items():
                if a['value'] is not None:
                    latest[(q, r['_defs'][q])] = {'value': a['value'], **({'otherText': a['otherText']} if 'otherText' in a else {}),
                                                  'reportId': r['reportId'], 'sourceId': r['sourceId']}
        attended = sorted({r['attendanceDate'] for r in reps if r['attendanceDate']})
        if st['status'] == 'unmapped':
            evidence = '未對照（不列入成效比較）'
        elif attended:
            evidence = '人工確認到店'
        elif any(r['_effective'] for r in reps):
            evidence = '有回報、無到店確認'
        elif st['status'] == 'reported':
            evidence = '回報無有效內容（視同無紀錄）'
        elif st['status'] == 'visited_no_report':
            evidence = '有當月筆記或到店紀錄、無回報'
        else:
            evidence = '無紀錄（Kit 已確認同步完成）' if sync_confirmed else '未知（未確認同步，不得當未拜訪）'
        rows.append({'storeCode': st['storeCode'], 'analysisName': st['analysisName'], 'status': st['status'],
                     'evidence': evidence, 'attendanceDates': attended, 'reports': len(reps),
                     'latest': _merge_latest(latest),
                     'definitionSplits': sorted({q for (q, _) in latest if sum(1 for (x, _) in latest if x == q) > 1}),
                     'notes': [{'reportId': r['reportId'], 'noteDate': r['noteDate'], 'text': r['note']['text'], 'next': r['note']['next']}
                               for r in reps if r['note']['included']]})
    return {'visitMonth': doc['visitMonth'], 'exportedAt': doc['exportedAt'], 'appVersion': doc['appVersion'],
            'sources': [{'sourceId': k, 'file': v[0]} for k, v in sources.items()], 'stores': rows}


def main():
    a = sys.argv[1:]
    sync = '--sync-confirmed' in a
    out = a[a.index('--json') + 1] if '--json' in a else None
    try:
        res = read(a[0], a[1], sync)
    except Stop as e:
        print('⛔ 停止：' + str(e)); sys.exit(2)
    for s in res['stores']:
        core = {k: v['value'] for k, v in s['latest'].items() if k.startswith('core.') and isinstance(v, dict)}
        print(f"{s['analysisName']}｜{s['status']}｜{s['evidence']}｜回報 {s['reports']} 筆｜到店 {','.join(s['attendanceDates']) or '—'}｜{core}")
    if out:
        json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('✅ 讀回完成')


if __name__ == '__main__':
    main()
