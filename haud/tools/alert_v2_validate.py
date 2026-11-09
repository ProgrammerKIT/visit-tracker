#!/usr/bin/env python3
"""分析端警示 JSON v2（yq-alert-2）交付前自檢，比照 App v1.5.101 匯入規則（契約 v2.0 第 2 節）。
用法：python3 alert_v2_validate.py <檔案.json> ；違規列出並 exit 1。"""
import json, re, sys
CORE = [
 {"id":"core.shelf_haud","label":"架上 HAUD 盒數","type":"number","unit":"盒","min":0,"max":999},
 {"id":"core.stock_status","label":"HAUD 庫存狀態","type":"single","options":["正常","偏低","斷貨","未確認"]},
 {"id":"core.push_sku","label":"店員現在主推哪一支","type":"single","options":["HAUD","HAMD","Complete","其他","沒特別推","未詢問"],"otherTextOption":"其他"},
 {"id":"core.main_action","label":"本店主軸動作","type":"single","options":["做了","忘了","店員不配合","不適用"]}]
L = lambda x: len(x.encode('utf-16-le')) // 2  # 比照 JavaScript 字串長度
def main(path):
    raw = open(path,'rb').read(); errs = []
    def dup_hook(pairs):
        ks = [k for k,_ in pairs]
        if len(ks) != len(set(ks)): errs.append(f'重複鍵：{ks}')
        return dict(pairs)
    d = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=dup_hook)
    e = errs.append
    if len(raw) > 2*1024*1024: e('檔案超過 2 MiB')
    if list(d) != ['format','salesMonth','visitMonth','channel','coreChecks','stores'] and set(d) != {'format','salesMonth','visitMonth','channel','coreChecks','stores'}: e(f'頂層鍵不符：{list(d)}')
    if d.get('format') != 'yq-alert-2': e('format 應為 yq-alert-2')
    for k in ('salesMonth','visitMonth'):
        if not re.fullmatch(r'(?!0000)\d{4}-(0[1-9]|1[0-2])', str(d.get(k))): e(f'{k} 格式錯誤')
    if d.get('channel') != '佑全': e('channel 應為「佑全」')
    if d.get('coreChecks') != CORE: e('coreChecks 與固定定義不完全一致')
    st = d.get('stores', [])
    if not 1 <= len(st) <= 500: e('stores 列數須 1–500')
    codes, ids = set(), set()
    for i, s in enumerate(st):
        w = f'stores[{i}]'
        if set(s) != {'name','storeCode','channel','reason','checkpoints','checks','previousResult'}: e(f'{w} 鍵不符：{list(s)}'); continue
        if not s['name'].strip() or L(s['name']) > 500: e(f'{w}.name 空白或過長')
        if not re.fullmatch(r'[A-Z]?\d{3,4}', s['storeCode']): e(f'{w}.storeCode 格式錯誤')
        if s['storeCode'] in codes: e(f'{w}.storeCode 重複')
        codes.add(s['storeCode'])
        if s['channel'] != '佑全': e(f'{w}.channel 應為「佑全」')
        if L(s['reason']) > 50000: e(f'{w}.reason 過長')
        if not isinstance(s['checkpoints'], list) or len(s['checkpoints']) > 100 or any(not isinstance(c,str) or L(c) > 20000 for c in s['checkpoints']): e(f'{w}.checkpoints 不合')
        pr = s['previousResult']
        if pr is not None and (not isinstance(pr,str) or L(pr) > 600): e(f'{w}.previousResult 須為 ≤600 字串或 null')
        if len(s['checks']) > 20: e(f'{w}.checks 超過 20 題')
        for j, c in enumerate(s['checks']):
            cw = f'{w}.checks[{j}]'; t = c.get('type')
            m = re.fullmatch(r'c\.(\d{4}-\d{2})\.([A-Z]?\d{3,4})\.([1-9]\d*)', c.get('id',''))
            if not m or m.group(1) != d['visitMonth'] or m.group(2) != s['storeCode'] or L(c['id']) > 100: e(f'{cw}.id 格式或期別／店碼不符')
            if c.get('id') in ids: e(f'{cw}.id 重複')
            ids.add(c.get('id'))
            if not str(c.get('label','')).strip() or L(c['label']) > 300: e(f'{cw}.label 空白或過長')
            allowed = {'yesno':{'id','label','type'}, 'single':{'id','label','type','options'},
                       'number':{'id','label','type','unit','min','max'}, 'text':{'id','label','type','maxLength'}}.get(t)
            if allowed is None: e(f'{cw}.type 不合：{t}'); continue
            if not set(c) <= allowed: e(f'{cw} 含不屬此題型之鍵：{set(c)-allowed}')
            if t == 'single':
                o = c.get('options', [])
                if not 2 <= len(o) <= 8 or len(set(o)) != len(o) or any(not x.strip() or L(x) > 300 for x in o): e(f'{cw}.options 不合')
            if t == 'number':
                if not str(c.get('unit','')).strip() or L(c['unit']) > 100: e(f'{cw}.unit 不合')
                if 'min' in c and 'max' in c and c['min'] > c['max']: e(f'{cw} min > max')
            if t == 'text' and 'maxLength' in c and not (isinstance(c['maxLength'], int) and 1 <= c['maxLength'] <= 2000): e(f'{cw}.maxLength 不合')
    if errs:
        print('❌ v2 自檢失敗：'); [print(' -', x) for x in errs]; sys.exit(1)
    print(f'✅ v2 自檢通過（{len(st)} 家）')
main(sys.argv[1])
