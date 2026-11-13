#!/usr/bin/env python3
"""到店檢查點時效把關（主檔 v2.24 歷史裁定第 16 條）

用法：python3 timeliness_check.py <最新月YYYY-MM> <App匯入JSON> [index.html] [期別帳本.md]
有違規即列出並以 exit code 1 結束；產出流程遇 1 必須停止交付。

規則：到店事項（JSON checkpoints、index.html「這次最該優先談的一件事」與優先序卡到店事項、
期別帳本〈交接必查點〉）不得要求詢問或查核「最新月以前」的月份。
最新月、往後月份（未來追蹤）與現況可用；reason 與背景說明不在掃描範圍。
"""
import json, re, sys, html

MONTH = re.compile(r'(?<![\d.])(1[0-2]|[1-9])\s*(?:[–\-~～至到]\s*(1[0-2]|[1-9]))?\s*月(?!均)')
OLD_WORDS = re.compile(r'首單|首批|上一次低點|當時')


def months_in(text):
    out = []
    for m in MONTH.finditer(text):
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
        out += list(range(a, b + 1)) if a <= b else [a, b]
    return out


def is_past(month, latest_m):
    # 以「最新月往前 6 個月內」視為過去；最新月之後（含跨年）視為未來追蹤
    diff = (latest_m - month) % 12
    return 1 <= diff <= 6


def check_text(label, text, latest_m):
    bad = [m for m in months_in(text) if is_past(m, latest_m)]
    hits = []
    if bad:
        hits.append(f'{label}：提到最新月以前的 {sorted(set(bad))} 月 → {text}')
    elif OLD_WORDS.search(text):
        hits.append(f'{label}：疑似回溯舊事件（{OLD_WORDS.search(text).group(0)}）→ {text}')
    return hits


def main():
    latest = sys.argv[1]; latest_m = int(latest[5:7])
    hits = []
    d = json.load(open(sys.argv[2], encoding='utf-8'))
    for s in d['stores']:
        for i, c in enumerate(s['checkpoints'], 1):
            hits += check_text(f'JSON {s["name"]} 第{i}條', c, latest_m)
        for c in s.get('checks', []):
            hits += check_text(f'JSON {s["name"]} 客製題 {c["id"]}', c['label'], latest_m)
    if len(sys.argv) > 3:
        raw = open(sys.argv[3], encoding='utf-8').read()
        raw = re.sub(r'<script.*?</script>|<style.*?</style>', '', raw, flags=re.S)
        lines = [l.strip() for l in html.unescape(re.sub(r'<[^>]+>', '\n', raw)).split('\n') if l.strip()]
        for i, l in enumerate(lines):
            if l.startswith('這次最該優先談的一件事') and i + 1 < len(lines):
                hits += check_text('index 優先談', lines[i + 1], latest_m)
        # 優先序卡／下滑卡之到店事項欄：以動詞開頭之短句
        for l in lines:
            if len(l) <= 40 and re.match(r'^(問|查|確認|核對|請)', l):
                hits += check_text('index 到店事項', l, latest_m)
    if len(sys.argv) > 4:
        md = open(sys.argv[4], encoding='utf-8').read()
        # v3.0 起交接必查點位於期別帳本「### 交接必查點」；相容舊主檔「## 上期交接必查點」
        if '### 交接必查點' in md:
            sec = md.split('### 交接必查點', 1)[1].split('\n### ', 1)[0]
        else:
            sec = md.split('## 上期交接必查點', 1)[1].split('\n## ', 1)[0]
        for l in sec.split('\n'):
            if re.match(r'^\d+\. ', l):
                for part in re.split(r'[；;]', l):
                    if re.search(r'(問|查證|查核|確認)', part):
                        hits += check_text('主檔必查點', part.strip(), latest_m)
    hits = list(dict.fromkeys(hits))
    if hits:
        print('❌ 到店檢查點時效違規 %d 處：' % len(hits))
        for h in hits:
            print(' -', h)
        sys.exit(1)
    print('✅ 到店檢查點時效：無違規')


if __name__ == '__main__':
    main()
