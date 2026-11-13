import sys, pickle
sys.path.insert(0, '/home/claude/scripts')
from engine import *
R, G, w, R9 = pickle.load(open('/home/claude/data/R.pkl', 'rb'))
L, P = '2026-10', '2026-09'

def rn(c):  # rank 名稱：去「佑全」，保留藥局
    n = NAME[c]
    return n[2:] if n.startswith('佑全') else n

def rs(c):  # 判定區短名
    n = rn(c)
    return n[:-2] if n.endswith('藥局') else n

def table(sku):
    g = G[sku]; rows = []
    for c in CODES:
        cur = g.loc[c, L]; prv = g.loc[c, P]; hist = g.loc[c, :P].dropna()
        rows.append(dict(c=c, prv=int(prv), cur=int(cur), inc=int(cur - prv),
                         rate=(cur - prv) / prv if prv > 0 else np.nan, nh=bool(cur > hist.max())))
    return pd.DataFrame(rows)

def ranks(sku):
    d = table(sku)
    r1 = d[d.prv > 0].sort_values(['rate', 'inc', 'c'], ascending=[False, False, True]).head(5)
    r2 = d.sort_values(['inc', 'rate', 'c'], ascending=[False, False, True]).head(5)
    r3 = d.sort_values(['cur', 'inc', 'c'], ascending=[False, False, True]).head(5)
    return r1, r2, r3

NH = '<span class="nh">🔥 創新高</span>'

def card(title, sub, kind, df, foot):
    o = [f'<div class="card"><div class="hd"><h2>{title}</h2><div class="sub">{sub}</div></div>\n']
    if kind == 3:
        o.append('<table><tr><th>排名</th><th>門市</th><th class="r">銷量</th></tr>\n')
    else:
        o.append(f'<table><tr><th>排名</th><th>門市</th><th class="r">上月 → 本月</th><th class="r">{"成長率" if kind==1 else "成長"}</th></tr>\n')
    for i, r in enumerate(df.itertuples()):
        tag = NH if r.nh else ''
        nmh = f'<td class="nm">{rn(r.c)}<small>{r.c}</small></td>'
        if kind == 1:
            o.append(f'<tr><td class="rk">{i+1}</td>{nmh}<td class="tr r">{r.prv} → {r.cur}</td><td class="v r">{tag}+{r.rate*100:.1f}%</td></tr>\n')
        elif kind == 2:
            o.append(f'<tr><td class="rk">{i+1}</td>{nmh}<td class="tr r">{r.prv} → {r.cur}</td><td class="v r">{tag}+{r.inc}</td></tr>\n')
        else:
            o.append(f'<tr><td class="rk">{i+1}</td>{nmh}<td class="v r">{tag}{r.cur}</td></tr>\n')
    o.append(f'</table><div class="ft">{foot}</div></div>\n')
    return ''.join(o)

def jd(rows, legend, foot):
    o = ['<div class="jd"><div class="hd"><h2>上榜門市真偽判定</h2><div class="sub">榜一＋榜二上榜店，依主檔第三步框架逐家判定（表格內只放數字，判定另列於此）</div></div>\n']
    for k, c, txt in rows:
        lab = {'ok': '✅ 真實', 'no': '❌ 虛假', 'un': '⚠️ 未驗證'}[k]
        o.append(f'<div class="row"><span class="bd {k}">{lab}</span><div class="tx"><b>{rs(c)}</b><small>{c}</small><br>{txt}</div></div>\n')
    o.append(f'<div class="lg">{legend}</div>\n<div class="ft">{foot}</div></div>\n')
    return ''.join(o)

JH = [
 ('un', '1601', '4→10 創全期新高（舊峰 9，26/03），但 10 盒為兩列各 5 盒之重複列加總；7、4、10 呈鋸齒，CV 0.50 屬波動主導，8 月 7 盒已判單月。11 月 ≥7 才認列。依 R1 先查庫存。'),
 ('no', '1602', '4→9 回到 4–12 常態擺幅，8、9 月 4 盒才是低點；峰 12 未破。'),
 ('no', '1606', '微量店 1→3，在 0–4 波動區間內；+200% 為低基期分母效應。'),
 ('no', '1703', '新加入門市 1→2 雖為在體系新高，僅 +1 盒屬微量；依主檔裁定第 7 條，基期成長率不適用。'),
 ('no', 'A1109', '13→14 在 13–24 擺幅內，近期 14.33 與基期 14.67 持平。'),
]
JC = [
 ('un', '1318', '1→9 創全期新高（舊峰 7），中位數 2、CV 0.89，屬低基期暴衝型態；E2 首月，須併列獎勵效應。同月 HAUD 7→4。11 月 ≥5 才認列。'),
 ('un', '1607', '1→8 創全期新高（舊峰 3），中位數 1.5，低基期暴衝；E2 首月，須併列獎勵效應。同月 HAUD 11→9。11 月 ≥4 才認列。'),
 ('no', '1601', '1→5 在 0–7 擺幅內，未創新高（前高 7，26/03）；增量來自 9 月 1 盒之低點。'),
 ('un', '1309', '2→7 創全期新高（舊峰 4），中位數 2，低基期暴衝；E2 首月，須併列獎勵效應。同月 HAUD 24→17。11 月 ≥4 才認列。'),
 ('no', '1310', '微量 2→5，全期月均 1.9；僅比舊峰 4 多 1 盒，成長率被分母放大。'),
 ('un', '1703', '4→9 創在體系新高（舊峰 4），4、4、4 平台後跳升；新加入門市基期不適用，E2 首月須併列獎勵效應。11 月 ≥5 才認列。'),
 ('no', 'A1118', '6→11 與 26/07 前高 11 並列、未創新高，在 2–11 擺幅內。'),
]

def build():
    src = open('/home/claude/data/rank_202609.html', encoding='utf-8').read()
    head = src[:src.find('</head>') + 7].replace('佑全 9月三榜', '佑全 10月三榜')
    o = [head, '<body>\n<div class="back"><a href="index.html">← 回 HAUD 每店深查報告</a></div>\n\n']
    o.append('<input type="radio" name="p" id="p-haud" class="pt" checked><input type="radio" name="p" id="p-comp" class="pt">\n<div class="tabs"><label for="p-haud">視舒坦玻尿酸30單支</label><label for="p-comp">Complete</label></div>\n\n')
    sub12 = '2026年10月 vs 9月（盒）'; sub3 = '2026年10月（盒）'
    fH = '佑全連鎖｜HAUD Offtake'; fC = '佑全連鎖｜Complete Offtake'
    r1, r2, r3 = ranks('HAUD')
    o.append('<div id="sec-haud">\n')
    o.append(card('《玻尿酸30入》10月銷售成長率TOP5', sub12, 1, r1, fH))
    o.append(card('《玻尿酸30入》10月銷售成長TOP5', sub12, 2, r2, fH))
    o.append(card('《玻尿酸30入》10月銷售量TOP5', sub3, 3, r3, fH))
    o.append(jd(JH, '判定分三類：✅真實（近 3 月站上高點＋前期≥基期＋非單月孤峰，或有鋪墊之回升）／❌虛假（低基期反彈、微量雜訊、單月離群、擺幅內波動）／⚠️未驗證（下期見真章，自動列入必查點）。10 月全通路僅 6 家 HAUD 成長，榜一、榜二為同一組 5 家。並列：榜二第 4–6 名增量同為 +1（中城、中山龍江二、大安健康人生），依成長率排列，大安健康人生（+7.1%）因此落榜。羅東公正 10 盒含重複列（5＋5），經 Kit 2026-11-03 裁定加總合併。', fH))
    o.append('</div>\n\n')
    c1, c2, c3 = ranks('Complete')
    o.append('<div id="sec-comp">\n')
    o.append(card('《全效型．康復力》10月銷售成長率TOP5', sub12, 1, c1, fC))
    o.append(card('《全效型．康復力》10月銷售成長TOP5', sub12, 2, c2, fC))
    o.append(card('《全效型．康復力》10月銷售量TOP5', sub3, 3, c3, fC))
    o.append(jd(JC, '判定分三類：✅真實／❌虛假／⚠️未驗證（定義同 HAUD）。<b>Complete 自 2026-10 起為 E2 店員競賽獎勵品項</b>，本月全通路 103→127（全期新高），所有成長均須併列獎勵效應，⚠️ 店於 11 月見真章。並列：榜二第 3–5 名增量同為 +5（淡水淡金、中城、信義吳興），依成長率排列，羅東公正（+4）因此落榜；榜三第 2–5 名同為 9 盒（中和景新、中城、大安健康人生、文山興隆），依增量較高者排前，大安健康人生與文山興隆增量同為 0，依店碼排列；頭城青雲（8 盒）落榜。', fC))
    o.append('</div>\n</body></html>\n')
    return ''.join(o)

if __name__ == '__main__':
    out = build()
    open('/home/claude/out/rank.html', 'w', encoding='utf-8').write(out)
    for sku in ['HAUD', 'Complete']:
        for r in ranks(sku): print(sku, [(rs(x.c), x.prv, x.cur, x.nh) for x in r.itertuples()])
