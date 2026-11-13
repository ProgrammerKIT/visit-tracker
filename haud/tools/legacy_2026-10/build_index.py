import sys, pickle, html
sys.path.insert(0, '/home/claude/scripts')
from engine import *
from store_text import T, PRIO_TEXT

R, G, w, R9 = pickle.load(open('/home/claude/data/R.pkl', 'rb'))
L = '2026-10'; P = '2026-09'
MS = [x for x in ALLM if x <= L]
lab = lambda ym: ym[2:]                # 25-09
slab = lambda ym: ym[2:].replace('-', '/')  # 25/09
H = G['HAUD']; C = G['Complete']
SKUC = {'HAUD': '#1F3864', 'HAMD': '#7B3F9D', 'Ultra UD': '#3B9FD1', 'Ultra MD': '#C0392B',
        'Complete': '#2E8B7A', 'TN': '#6B7280', 'TNF': '#A8AEB6'}
STC = {'A': '#B93030', 'Q': '#7B3F9D', 'B': '#2B8577', 'C': '#D68910', 'D': '#2E7D3A', 'E': '#5B6C7F'}
STN = {'A': '止跌救量', 'B': '乘Complete勢', 'C': 'TN/TNF升級', 'D': '守成長', 'E': '穩節奏'}

LOCK = {'1322': 'A', '1701': 'D', 'A1106': 'D', 'A1114': 'D', '1318': 'E', 'A1109': 'D', 'A1308': 'D',
        '1309': 'D', 'A1118': 'D', '1308': 'C', 'A1113': 'C', '1601': 'C', '1607': 'D', '1320': 'B',
        'A1312': 'E', '1310': 'E', '1316': 'E', '1204': 'E'}
RULED = {'1607': 'Kit 2026-11-03 裁定 C→D', '1318': 'Kit 2026-11-03 裁定 D→E（解鎖）',
         '1601': 'Kit 2026-11-03 裁定維持 C', 'A1312': 'Kit 2026-11-03 裁定維持 E',
         'A1118': 'Kit 2026-11-03 裁定維持 D', '1322': 'Kit 2026-11-03 裁定維持 A',
         'A1107': 'Kit 2026-11-03 裁定接受自動 A'}
SUBC = {'A1114': '＋副C動作', 'A1308': '＋副C動作'}

def final_stage(c):
    if c in LOCK: return LOCK[c]
    d = R[c]
    return d['M'] if d['M'] == d['N'] else 'Q'

FS = {c: final_stage(c) for c in CODES}
ORDER = sorted(CODES, key=lambda c: -R[c]['move'])
RANK = {c: i + 1 for i, c in enumerate(ORDER)}

def fmt(v, nd=2):
    s = f'{v:.{nd}f}'
    return s.replace('-', '−')

def sgn(v, nd=0, pct=False):
    s = (f'{v:+.{nd}f}' if nd else f'{v:+.0f}')
    s = s.replace('-', '−')
    return s + ('%' if pct else '')

def cell(v):
    if pd.isna(v) or v == 0: return '·'
    return str(int(v))

def full(c):  # code + 全名（含藥局）
    return c + NAME[c]

# ---------- SVG ----------
def svg(vals, labels, hgt, gid):
    base = hgt - 40; top = 40; span = base - top
    mx = max([v for v in vals if v is not None] + [1])
    n = len(vals); xs = [40 + i * (1090 / (n - 1)) for i in range(n)]
    pts = [(x, base - (v / mx) * span) for x, v in zip(xs, vals) if v is not None]
    o = [f'<svg viewBox="0 0 1160 {hgt}" style="width:100%;height:auto"><defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1F3864" stop-opacity="0.20"/><stop offset="1" stop-color="#1F3864" stop-opacity="0.02"/></linearGradient></defs>']
    if pts:
        d = f'M{pts[0][0]:.1f},{base} ' + ' '.join(f'L{x:.1f},{y:.1f}' for x, y in pts) + f' L{pts[-1][0]:.1f},{base} Z'
        o.append(f'<path d="{d}" fill="url(#{gid})"/>')
        o.append('<polyline points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) + '" fill="none" stroke="#1F3864" stroke-width="2.4"/>')
    for x, v, lb in zip(xs, vals, labels):
        if v is not None:
            y = base - (v / mx) * span
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#1F3864"/><text x="{x:.1f}" y="{y-10:.1f}" text-anchor="middle" font-size="15" font-weight="800" fill="#1F3864">{int(v)}</text>')
        o.append(f'<text x="{x:.1f}" y="{hgt-12}" text-anchor="middle" font-size="13" fill="#94A0AC">{lb}</text>')
    o.append('</svg>')
    return ''.join(o)

# ---------- SKU table ----------
def skutable(rows, months):
    o = ['<table class="sku"><tr><th>SKU</th>' + ''.join(f'<th>{lab(m)}</th>' for m in months) + '<th>合計</th></tr>']
    tot = [0] * len(months)
    for s in SKUS:
        vals = rows[s]
        cls = ' class="haud"' if s == 'HAUD' else ''
        o.append(f'<tr{cls}><td style="color:{SKUC[s]};text-align:left;font-weight:700">{s}</td>' +
                 ''.join(f'<td>{cell(v)}</td>' for v in vals) + f'<td>{int(np.nansum(vals))}</td></tr>')
        tot = [a + (0 if pd.isna(b) else b) for a, b in zip(tot, vals)]
    o.append('<tr class="tot"><td style="text-align:left">每月合計</td>' + ''.join(f'<td>{int(v)}</td>' for v in tot) + f'<td>{int(sum(tot))}</td></tr></table>')
    return ''.join(o)

# ---------- overview numbers ----------
tot = {s: G[s][L].sum() for s in SKUS}
haud = H.sum()
hL, hP = int(haud[L]), int(haud[P])
TARGET = 235; NEXT = 235
d = H[L] - H[P]
up = d[d > 0]; dn = d[d < 0]
nm = lambda c: short(c)

core5 = ['HAUD', 'HAMD', 'Ultra UD', 'Ultra MD', 'Complete']
p1 = sum(G[s].sum() for s in core5)
p1L = int(p1[L]); p1prev = p1[:P]; p1pk = int(p1prev.max()); p1pkm = p1prev.idxmax()

same = [c for c in CODES if c != '1703']
yoy = {s: (int(G[s].loc[same, '2025-10'].sum()), int(G[s].loc[same, L].sum())) for s in SKUS}
xs = [R[c]['c_m'] for c in CODES]; ys = [R[c]['rec_m'] for c in CODES]
rr = np.corrcoef(xs, ys)[0, 1]

def build():
    src = open('/home/claude/data/index_202609.html', encoding='utf-8').read()
    head = src[:src.find('</head>') + 7].replace('（資料至 2026-09）', '（資料至 2026-10）')
    scripts = src[src.find('<script>'):]
    o = [head, '<body><div class="wrap">\n']
    o.append('<div class="link"><a href="rank.html">查看《視舒坦玻尿酸30單支》10月三榜排名 →</a></div>\n')
    o.append('<h1>佑全連鎖體系｜HAUD 每店獨立深查（資料至 2026-10）</h1>\n')
    o.append('<div class="meta">資料區間 2025-09～2026-10（14 個月）｜現役 26 家（佑全基隆麥金 2026-06 歇業；佑全中城 2025-12 加入；佑全三重正義異名已合併）｜基期 25/09–11 固定／前期 26/05–07／近期 26/08–10｜鎖定表 v1.5（18 家，2026-11-03 裁定）｜10 月實績 198 vs 目標 235（84.3%）｜依據主檔 v2.20、深查版式 SOP v1.0i、三榜 SOP v1.0j｜點門市名展開</div>\n')
    o.append('<div class="w5" style="background:#EEF2F7;border-color:#C9D5E3"><b>ℹ️ 10 月檔資料說明：</b>重複列 6 組，其中 3 組為全期首次出現於 HAUD（佑全羅東公正 5＋5、大安健康人生 8＋7、淡水清水 1＋5），Kit 2026-11-03 裁定照歷史裁定第 5 條加總合併；匯出完整性兩條自動判準均未觸發（重複組數 4→6；單 SKU ≥4→0 共 3 筆、2 家，未達 3 家門檻），檔案視為完整。</div>\n')
    o.append('<div class="searchbar"><input type="search" id="q" enterkeyhint="search" placeholder="輸入門市名後按 Enter 或「搜尋」" autocomplete="off" aria-label="搜尋門市"><button type="button" id="qg" aria-label="搜尋">搜尋</button><button type="button" id="qc" aria-label="清除">✕</button><div id="qr"></div></div>\n')

    # ---- overview
    o.append('<div class="card"><h2>通路總覽</h2><div class="kpi">')
    o.append(f'<div><small>10 月實績</small><b>{hL}</b></div><div><small>目標達成率</small><b>{hL/TARGET*100:.1f}%</b></div><div><small>淨增長 vs 9 月</small><b>{sgn(hL-hP)}</b></div>')
    o.append(f'<div class="up"><small>上升腿（{len(up)} 家）</small><b>{sgn(up.sum())}</b></div><div class="dn"><small>下滑腿（{len(dn)} 家）</small><b>{sgn(dn.sum())}</b></div><div><small>11 月目標</small><b>{NEXT}</b></div></div>')
    o.append(svg([int(haud[m]) for m in MS], [lab(m) for m in MS], 300, 'g0'))
    o.append('<div class="note"><b>11 月達標路徑（目標 235，需較 10 月 +37）：</b>10 月下滑腿 −49 分散在 14 家，前四大為佑全淡水淡金 −7、信義吳興 −7、康和 −6、淡水清水 −4（合計 −24），四家 9 月都在常態高位，回到 9 月水準即可補回約三分之二缺口；上升腿 +16 中佑全羅東公正 +6 為 ⚠️ 未驗證（含重複列），不宜當成可依賴的增量。上期點名的大店下滑腿五家（大安健康人生、佑全永和中山、文山興隆、佑全淡水新市一、大安羅斯福）本月僅回補 +1。結論：<b>收復 9 月高位店（成本低、皆為既有拜訪路線）優先於衝新增量</b>。<b>⚠️ E2 首月訊號：</b>獎勵品項 HAUD 231→198，同為獎勵品項之 Complete 103→127（全期新高），已退出獎勵之 HAMD 98→138；店層級 HAUD 增減與 Complete 增減相關 −0.25，HAUD 降、Complete 同月 ≥+3 者 5 家（候選 P-03）。獎勵前基準（現役口徑 25-09～26-05 月均）<b>172.9</b>，10 月高出 14.5%。</div>')
    rows = {s: [G[s][m].sum() for m in MS] for s in SKUS}
    o.append('<div class="tw">' + skutable(rows, MS) + '</div>')
    o.append('<h4>YoY（同口徑 25 家：排除佑全中城與已歇業佑全基隆麥金）</h4><div class="tw"><table class="pk"><tr><th>SKU</th><th>2025-10</th><th>2026-10</th><th>YoY</th></tr>')
    for s in SKUS:
        a, b = yoy[s]
        o.append(f'<tr><td style="color:{SKUC[s]};font-weight:700">{s}</td><td>{a}</td><td>{b}</td><td>{sgn((b-a)/a*100,1,True)}</td></tr>')
    o.append('</table></div><div class="note"><b>⚠️ YoY 污染聲明：</b>2026-07～09 為 HAUD／HAMD 獎勵期（E1）、2026-10～12 為 HAUD／Complete 獎勵期（E2），2025 同期均無獎勵。<b>HAUD 與 Complete 之 YoY 至 2026-12 均跨獎勵期不可比</b>，不得作為結構性成長之證據。</div>')
    # self peak
    pk = []
    for c in CODES:
        hist = H.loc[c, :P].dropna(); cur = int(H.loc[c, L]); m = hist.max(); mm = hist[hist == m].index[-1]
        pk.append((c, cur, int(m), mm, cur - int(m)))
    pk.sort(key=lambda x: (-x[4], -x[1]))
    o.append('<details class="pkd"><summary><span class="nm">各店本月 vs 自身歷史高峰（HAUD）</span></summary><div class="tw"><table class="pk"><tr><th>門市</th><th>10 月</th><th>前高（月份）</th><th>差距</th><th>結果</th></tr>')
    nn = ne = nb = 0
    for c, cur, m, mm, g in pk:
        cls, t = ('pk-new', '新高') if g > 0 else (('pk-eq', '持平') if g == 0 else ('pk-no', '未破'))
        nn += g > 0; ne += g == 0; nb += g < 0
        o.append(f'<tr><td>{full(c)[:-2] if full(c).endswith("藥局") else full(c)}</td><td>{cur}</td><td>{m}（{lab(mm)}）</td><td>{sgn(g) if g else "0"}</td><td class="{cls}">{t}</td></tr>')
    newl = '、'.join(nm(c) for c, cur, m, mm, g in pk if g > 0)
    o.append(f'</table></div><div class="note">口徑：前高＝該店 10 月以前之全期單月最高 HAUD（與恢復缺口所用全期最高同一數字來源）。本月 {nn} 家創新高（{newl}），{ne} 家持平，{nb} 家未破。<b>P1 五支合計版（HAUD＋HAMD＋Ultra UD＋Ultra MD＋Complete）：10 月 {p1L} 盒 vs 前高 {p1pk}（{lab(p1pkm)}），通路層級{"創新高 " + sgn(p1L-p1pk) if p1L>p1pk else "未破（" + sgn(p1L-p1pk) + "）"}</b>。</div></details>')
    o.append(f'<div style="margin-top:14px"><small style="color:#636E7A">Complete–HAUD 相關係數（近 3 月均／現役 26 家）</small><div class="big">r = {rr:.3f}</div><div class="note"><b>歷史斷點聲明：</b>舊值 0.514 係「全期月均、含已歇業佑全基隆麥金」口徑；自 v1.6 起改為「近 3 月均、僅現役 26 家」（2026-07 基準 0.314、2026-08 為 0.516、2026-09 為 0.612）。<b>本期 {rr:.3f} 只與上期 0.612 比較，禁止與舊值 0.514 並列。</b>策略含意：10 月起 Complete 列入 E2 獎勵，r 上升須併列獎勵效應，不得逕解讀為品類連動增強；B 條件成立者仍僅佑全八里中山、佑全中城兩家微量店（順風池 8.33），「乘 Complete 勢」仍非可規模化打法。</div></div></div>\n')

    # ---- priority top5
    o.append('<div class="card"><h2>拜訪優先序 前 5</h2>')
    for i, c in enumerate(ORDER[:5]):
        dd = R[c]; tot5 = dd['move']; rg = dd['recgap']; cg = 0.4 * dd['cgap']; tn = dd['tnterm']
        st = FS[c]; ax, txt = PRIO_TEXT[c]
        pc = lambda v: f'{v/tot5*100:.0f}%'
        o.append(f'<details class="prio"><summary><span class="circ" style="background:{STC[st]}">{i+1}</span><span class="nm">{full(c)}</span><span class="axis">{ax}</span><span class="sc">{tot5:.2f}</span></summary><div class="body">\n')
        o.append(f'<div class="comp"><div><small>恢復缺口</small><b>{rg:.2f}</b><small>{pc(rg)}</small></div><div><small>Complete 缺口</small><b>{cg:.2f}</b><small>{pc(cg)}</small></div><div><small>TN 項（折減後）</small><b>{tn:.2f}</b><small>{pc(tn)}</small></div><div><small>TN 倍數</small><b>{dd["mult"]:.2f}</b><small>{st}｜{STN[st]}</small></div></div>\n<p>{txt}</p></div></details>')
    low = [c for c in CODES if R[c]['mult'] < 1]
    low.sort(key=lambda c: R[c]['mult'])
    o.append('<div class="note"><b>讀法：</b>可搬動量＝恢復缺口＋0.4×Complete缺口＋0.25×(TN+TNF)池×min(倍數/2,1)（歷史裁定第 11 條，2026-08 期起）。TN 項只看池子大小，不分素材厚薄——<b>佑全淡水新市一雖倍數 4.79，HAUD 未止血前不談轉單</b>。倍數 &lt;1 之門市（' +
             '、'.join(f'{nm(c)} {R[c]["mult"]:.2f}' for c in low) + '）不談轉單；大安羅斯福另有特註 TN 池不列為轉單素材。前 10 中 Complete 項全部為 0。</div></div>\n')

    # ---- decline / complete
    o.append('<div class="card"><details><summary><span class="nm">下滑 TOP5／Complete 逆勢關注（點開）</span><span class="st">HAUD 下滑 TOP5／Complete 逆勢關注｜切換</span></summary><div class="body">\n')
    o.append('<input type="radio" name="dn" id="dn-h" class="dnr" checked><input type="radio" name="dn" id="dn-c" class="dnr">\n<div class="dntabs"><label for="dn-h">HAUD</label><label for="dn-c">Complete</label></div>\n')
    p3 = ['2026-07', '2026-08', '2026-09']
    dl = []
    for c in CODES:
        if c == '1703': continue
        a = H.loc[c, p3].mean(); cur = H.loc[c, L]; prv = H.loc[c, P]
        dl.append((c, a, cur, cur - a, (cur - a) / a if a else 0, prv))
    dl.sort(key=lambda x: (round(x[3], 2), x[4], x[2], nm(x[0])))
    DLW = {
     '1318': '<b>➖ 回落未達真實下滑</b>｜13→9→7→4 連三月下滑；近期均 6.67 仍遠高於基期 0.67，依第三步定義不構成真實下滑。同月 Complete 1→9、TN 4→10，較像店員推力轉向（候選 P-03）。Kit 2026-11-03 裁定鎖 D 解鎖改 E，已列 App。',
     'A1308': '<b>➖ 回落未達真實下滑</b>｜12、11、10 高原首度跌到 6；近期均 9.0 仍為基期 2.33 的 3.9 倍。10 月含重複列 1＋5。鎖 D，11 月 ≥9 視為回到高原。',
     'A1106': '<b>➖ 回落未達真實下滑</b>｜8 月 24 為全期高點，9–10 月 14、15；近期均 17.67 為基期 14.0 的 1.26 倍。鎖 D、每月必訪店。',
     '1322': '<b>❌ 真實下滑（可得性未排除）</b>｜15→11→8→3→3；近期均 4.67 較基期 8.0 低 42%、中位數 3 較 6 低 50%，<b>均值與中位數雙確認</b>。同店他支仍在賣，先查架上可得性（候選 P-04）。鎖 A、已列 App 第 1 名。',
     'A1118': '<b>➖ 回落未達真實下滑</b>｜9 月 15 為單月高點，10 月 8；近期均 11.33 與基期 11.67 持平。鎖 D（Kit 裁定維持），11 月仍 <9.3 觸發解鎖評估。同月 Complete 6→11（候選 P-03）。',
    }
    o.append('<div class="dnp" id="dnp-h"><div class="note">以「本月 − 前 3 月均」排序之減量前 5 家（差值取小數 2 位；同分依減幅 % 大者、本月低者、門市名稱）。<b>「前 3 月均」</b>為最新月之前連續 3 個月（7 月、8 月、9 月）之均值，每月滾動，與深查之前期（5–7 月）／近期（8–10 月）視窗不同；<b>「MoM」</b>為上月→本月，僅供參考、不參與排序；<b>「期間高峰」</b>為該店入體系以來 HAUD 單月最高；新加入門市（佑全中城）不列入。<b>此表只揭露、不進三榜、不進 App、不作為緊急店判準。</b>判讀欄之「真實下滑」依主檔第三步框架：近期（8–10 月均）低於基期（25/09–11 均）≥20%，且均值與中位數雙確認。</div>\n')
    o.append('<div style="font-size:12px;color:#636E7A;margin:4px 0">手機請左右滑動檢視完整欄位</div><div class="tw"><table class="dn"><tr><th>#</th><th class="l">門市</th><th>前 3 月均→本月</th><th>差值</th><th>MoM（上月→本月）</th><th>期間高峰</th><th class="l">規則判讀</th></tr>')
    for i, (c, a, cur, df_, pct, prv) in enumerate(dl[:5]):
        hs = H.loc[c].dropna(); pkv = int(hs.max()); pkm = hs[hs == pkv].index[-1]
        o.append(f'<tr><td class="c">{i+1}</td><td class="l nmc">{nm(c)}<span class="chip" style="background:{STC[FS[c]]}">{FS[c]}</span></td><td>{fmt(a)}→{int(cur)}</td><td class="neg">{fmt(df_)}</td><td>{int(prv)}→{int(cur)}（{sgn(cur-prv) if cur!=prv else "0"}）</td><td>{pkv}<small>（{slab(pkm)}）</small></td><td class="l why">{DLW[c]}</td></tr>')
    o.append('</table></div>\n<div class="note"><b>讀法：</b>本期減量前 5 家中<b>僅佑全淡水新市一構成「真實下滑」</b>（均值與中位數雙確認，但可得性未排除），其餘四家近期均都仍不低於基期的 80%。佑全中和景新、信義吳興同月 Complete 大增，回落須併列 E2 獎勵推力轉向之可能，不等於客源流失。佑全淡水新市一、佑全中和景新已列緊急店；其餘三家依各自鎖定階段處理，不因此表改變。</div>\n</div>\n')
    # complete 逆勢
    rec = MS[-3:]; pri = MS[-6:-3]
    act = [c for c in CODES if c != '1703']
    mult = C.loc[act, rec].sum().sum() / C.loc[act, pri].sum().sum()
    zl = []
    for c in act:
        pm = C.loc[c, pri].mean(); rm = C.loc[c, rec].mean(); pmd = C.loc[c, pri].median(); rmd = C.loc[c, rec].median()
        if pm >= 3 and rm <= pm * mult * 0.7 and rmd <= pmd * mult * 0.7:
            o6p = sum(G[s].loc[c, pri].sum() for s in SKUS if s != 'Complete'); o6r = sum(G[s].loc[c, rec].sum() for s in SKUS if s != 'Complete')
            zl.append((c, pm, rm, pm * mult, pm * mult - rm, pmd, rmd, (o6r - o6p) / o6p))
    zl.sort(key=lambda x: -x[4])
    ZW = {
     '1308': '6、8、7 → 0、5、8：8 月 0 盒是缺口主因（原始檔 8 月兩個店名下都沒有 Complete 這一列），9–10 月已回到 5、8 盒，<b>回升中</b>。同店其他 SKU 同期 {o}，整店{w}。HAUD 鎖 C，未列 App。',
     'A1312': '9、1、5 → 5、2、0：10 月 0 盒，<b>仍在下滑</b>。同店其他 SKU 同期 {o}，{w}，只有 Complete 掉，較可能是陳列、庫存或推薦問題。HAUD 鎖 E，未列 App；拜訪時順帶確認 Complete 架上有貨。',
     '1322': '6、3、4 → 0、4、1：與 HAUD 同步走弱。同店其他 SKU 同期 {o}，整店{w}，與 HAUD 之可得性查證一併處理。已列 App 第 1 名（HAUD 鎖 A）。',
     '1601': '2、4、4 → 3、1、5：缺口 1.29 為四家最小，10 月回到 5 盒，<b>回升中</b>。同店其他 SKU 同期 {o}，{w}。已列 App（HAUD ⚠️ 未驗證）。',
    }
    o.append(f'<div class="dnp" id="dnp-c"><div class="note"><b>Complete 逆勢關注名單</b>：每月找出「量夠大、且一季下來明顯跑輸通路」的店，名單寧可短、每家都值得跑。三道門檻：<b>① 量體</b>：前期（5–7 月）月均 ≥3 盒；<b>② 逆勢缺口</b>：近期（8–10 月）均 ≤ 前期均 × 通路成長倍數 × 0.7，且中位數同樣落後 30% 以上；<b>③ 排序</b>：缺口盒數＝前期均 × 通路成長倍數 − 近期均，由大到小。本期通路成長倍數 = <b>{mult:.3f}</b>（Complete 現役店排除新加入門市 5–7 月月均 {C.loc[act,pri].sum().sum()/3:.1f} → 8–10 月月均 {C.loc[act,rec].sum().sum()/3:.1f}；Kit 2026-11-03 裁定倍數口徑排除佑全中城，9 月實作曾含佑全中城為 1.203，若依本口徑應為 1.183）。「預期月均」= 若該店跟上通路成長應有的月均；「同店其他 SKU」= 同店 Complete 以外 6 支 SKU 合計，8–10 月 vs 5–7 月，用來判斷是整店變弱還是只有 Complete 掉。新加入門市（佑全中城）不列入。<b>此表只揭露，不進三榜、不進 App、不作為緊急店判準。</b></div><div style="font-size:12px;color:#636E7A;margin:4px 0">手機請左右滑動檢視完整欄位</div><div class="tw"><table class="dn"><tr><th>#</th><th class="l">門市</th><th>前期 5–7 月</th><th>近期 8–10 月</th><th>預期月均</th><th>缺口（盒／月）</th><th>中位數 前→近</th><th>10 月方向</th><th>同店其他 SKU</th><th class="l">判讀</th></tr>')
    for i, (c, pm, rm, ex, gap, pmd, rmd, o6) in enumerate(zl):
        pv = [int(C.loc[c, m]) for m in pri]; rv = [int(C.loc[c, m]) for m in rec]
        a9, a10 = rv[1], rv[2]
        dirt = f'{a9}→{a10} 回升' if a10 > a9 else (f'{a9}→{a10} 下滑' if a10 < a9 else f'{a9}→{a10} 持平')
        dcol = '#2E7D3A' if a10 > a9 else ('#B93030' if a10 < a9 else '#636E7A')
        os_ = f'{o6*100:+.0f}%'.replace('-', '−')
        wd = '來客正常' if o6 > 0.03 else ('整店略弱' if o6 < -0.03 else '整店持平')
        o.append(f'<tr><td class="c">{i+1}</td><td class="l nmc">{nm(c)}<span class="chip" style="background:{STC[FS[c]]}">{FS[c]}</span></td><td>{"、".join(map(str,pv))}<small>（均 {pm:.2f}）</small></td><td>{"、".join(map(str,rv))}<small>（均 {rm:.2f}）</small></td><td>{ex:.2f}</td><td class="neg">−{gap:.2f}</td><td>{pmd:g}→{rmd:g}</td><td style="color:{dcol};font-weight:800">{dirt}</td><td>{os_}</td><td class="l why">{ZW[c].format(o=os_, w=wd)}</td></tr>')
    totgap = sum(x[4] for x in zl)
    o.append(f'</table></div><div class="note"><b>讀法：</b>本期 26 家中 {len(zl)} 家過關（上期 2 家），合計每月約少 {totgap:.0f} 盒。文山興隆近期 8.33（7、9、9）已跟上通路，自名單移出。<b>獎勵期：</b>10–12 月 Complete 為 E2 獎勵品項，通路倍數 {mult:.3f} 已把整體拉抬扣掉；10 月單月方向與 E2 首月效應重疊，回升店須下期再確認。兩種倍數口徑（排除／含佑全中城 1.308）本期名單相同。門市旁的階段標籤為該店 HAUD 階段，Complete 本身不分階段。</div>\n</div>\n</div></details></div>\n')

    # ---- pools
    o.append('<div class="card"><details><summary><span class="nm">四大量池與計算定義（點開查看公式與數值）</span></summary><div class="body">\n')
    tnp = sum(R[c]['t_m'] for c in CODES if R[c]['Ccond'])
    recg = sum(R[c]['recgap'] for c in CODES)
    o.append('<table class="ind"><tr><td class="l">①止血潛力</td><td>11.00</td><td class="l">Σ max(0, 前期均−近期均)，僅 A 階段</td><td>佑全淡水新市一 12.33−4.67＝7.67；大安羅斯福 31.00−27.67＝3.33</td></tr>\n')
    o.append(f'<tr><td class="l">②恢復缺口</td><td>{recg:.2f}</td><td class="l">Σ max(0, 全期單月最高×0.85−近期均)，全部現役（含 A；佑全中城依裁定第 7 條不計）</td><td>上期 54.38</td></tr>\n')
    o.append('<tr><td class="l">③微量店＋1盒</td><td>7 家 / 7.0</td><td class="l">全期 HAUD 月均 &lt;3</td><td>佑全基隆復興、佑全八里中山、佑全宜蘭和睦、佑全蘇澳中山、佑全吉安中山、佑全中城、文山木新</td></tr>\n')
    o.append('<tr><td class="l">④-a Complete 順風池</td><td>8.33（2 家）</td><td class="l">Σ(Complete 近3月均−HAUD 近3月均)，B 條件店</td><td>佑全八里中山 4.00、佑全中城 4.33</td></tr>\n')
    o.append(f'<tr><td class="l">④-b TN 轉單池</td><td>{tnp:.2f}（14 家）</td><td class="l">Σ(TN+TNF) 近3月均，C 條件店</td><td>5%／10% 假設轉換＝{tnp*0.05:.1f}／{tnp*0.1:.1f} 盒（假設值）</td></tr></table>\n')
    o.append('<div class="note">①②重疊 11.01 盒（佑全淡水新市一 8.08、大安羅斯福 2.93）；②不得排除 A 階段門市；④-b 為可轉單基數非可實現增量。上期 54.38→本期 64.77（+10.39）之差異來自視窗前滾與多店 10 月回落，無定義變更：佑全淡水新市一 5.42→8.08、康和、佑全中和景新、永正、信義吳興等缺口擴大；已實現部分：文山興隆 1.28→0、佑全頭城青雲 3.35→1.35、佑全羅東公正 2.65→1.50。④-b 淡水清水進、佑全宜蘭礁溪出。①較上期 3.67 增加，主因大安羅斯福自動判 A（Kit 2026-11-03 接受）。</div></div></details></div>\n')

    # ---- stores
    o.append('<div class="card"><h2>每店獨立深查</h2>')
    groups = ['A', 'Q', 'B', 'C', 'D', 'E']
    R1 = {'1601': 'real', '1607': 'real', '1602': 'real', '1318': 'low', '1702': 'low'}
    for g in groups:
        mem = [c for c in CODES if FS[c] == g]
        if not mem: continue
        mem.sort(key=lambda c: -R[c]['move'])
        gname = '覆核佇列未定案' if g == 'Q' else STN[g]
        o.append(f'<h2 class="grp" style="color:{STC[g]};border-left-color:{STC[g]}">{g}｜{gname} （{len(mem)} 家）</h2>')
        for c in mem:
            o.append(store_card(c, g, R1.get(c)))
    o.append('</div>\n')
    o.append('<div class="foot"><b>鎖定表 v1.5（2026-11-03 裁定，18 家）：</b>佑全淡水新市一 A｜佑全花蓮中山、大安健康人生、文山興隆（副C）、中山龍江二、淡水清水（副C）、佑全淡水淡金、信義吳興、<b>佑全頭城青雲（C→D）</b> 鎖D｜佑全三重正義、文山木新、佑全羅東公正 鎖C｜佑全八里中山 鎖B｜樹林博愛、康和、佑全永和中山、佑全基隆復興、<b>佑全中和景新（D 解鎖→E）</b> 鎖E。未鎖定 8 家依雙規則自動定案（大安羅斯福本期自動判 A，Kit 2026-11-03 接受）。<br>已歇業：佑全基隆麥金（2026-06 起不列入）。常設警語：目前無。</div>\n')
    o.append('</div>')
    o.append(scripts)
    return ''.join(o)

def store_card(c, g, r1):
    d = R[c]; t = T[c]; s = d['series']
    col = STC[g]
    title = full(c) + ('（微量店）' if d['micro'] else '')
    o = [f'<details class="store" style="border-left-color:{col}"><summary><span class="nm">{title}</span><span class="st">HAUD 全期 {int(s.sum())} 盒｜近3月均 {d["rec_m"]:.1f}</span></summary><div class="body">']
    o.append('<h4>① 7-SKU 逐月銷量表</h4><div class="tw">')
    rows = {sk: [G[sk].loc[c, m] for m in MS] for sk in SKUS}
    if c == '1703':
        rows = {sk: [np.nan if m < '2025-12' else v for m, v in zip(MS, rows[sk])] for sk in SKUS}
    o.append(skutable(rows, MS) + '</div><h4>② HAUD 透徹分析</h4>')
    vals = [None if pd.isna(H.loc[c, m]) else H.loc[c, m] for m in MS]
    o.append(svg(vals, [lab(m) for m in MS], 250, 'g'))
    hs = s; pkv = int(hs.max()); pkm = hs[hs == pkv].index[-1]
    hist = H.loc[c, :P].dropna(); hm = int(hist.max()); hmm = hist[hist == hm].index[-1]
    cur = int(H.loc[c, L]); gap = cur - hm
    res = ('pk-new', '新高') if gap > 0 else (('pk-eq', '持平') if gap == 0 else ('pk-no', '未破'))
    growth = '不適用' if d['new'] else (sgn((d['rec_m'] / d['base_m'] - 1) * 100, 1, True) if d['base_m'] > 0 else '不適用（基期 0）')
    bm = '不適用' if d['new'] else f'{d["base_m"]:.2f}'
    core = sum(G[sk].loc[c, MS[-3:]].sum() for sk in ['HAUD', 'HAMD', 'Ultra UD', 'Ultra MD', 'Complete'])
    share = G['HAUD'].loc[c, MS[-3:]].sum() / core * 100 if core else 0
    tnv = 0 if c == 'A1107' else None
    o.append(f'<table class="ind"><tr><td class="l">基期月均(25/09–11)</td><td>{bm}</td><td class="l">前期月均(26/05–07)</td><td>{d["pri_m"]:.2f}</td><td class="l">近期月均(26/08–10)</td><td>{d["rec_m"]:.2f}</td></tr>\n')
    o.append(f'<tr><td class="l">基期→近期成長</td><td>{growth}</td><td class="l">CV</td><td>{d["cv"]:.2f}</td><td class="l">期間高峰</td><td>{pkv}（{slab(pkm)}）</td></tr>\n')
    mult = '—' if np.isinf(d['mult']) else f'{d["mult"]:.2f}'
    o.append(f'<tr><td class="l">恢復缺口</td><td>{"不計" if d["new"] else format(d["recgap"], ".2f")}</td><td class="l">Complete 缺口</td><td>{d["cgap"]:.2f}</td><td class="l">TN 池 / 倍數</td><td>{d["t_m"]:.2f} / {mult}</td></tr>\n')
    o.append(f'<tr><td class="l">佔核心 5 品項</td><td>{share:.1f}%</td><td class="l">可搬動量</td><td>{d["move"]:.2f}</td><td class="l">拜訪優先序名次</td><td>{RANK[c]}</td></tr>\n')
    o.append(f'<tr><td class="l">全期最高月（10 月前）</td><td>{hm}（{slab(hmm)}）</td><td class="l">本月 vs 最高峰</td><td>{cur}（{sgn(gap) if gap else "0"}）</td><td class="l">結果</td><td class="{res[0]}">{res[1]}</td></tr></table>')
    k, head, body = t['vd']
    vcol = {'ok': '#2E7D3A', 'no': '#B93030', 'un': '#D68910'}[k]
    icon = {'ok': '✅', 'no': '❌', 'un': '⚠️'}[k]
    o.append(f'<div class="vd" style="border-left-color:{vcol}"><b>{icon} 真偽判定</b>　{head}：{body}</div>')
    # stage
    M, N = d['M'], d['N']
    if c in LOCK:
        srcs = '鎖定表 v1.5' + (f'（{RULED[c]}）' if c in RULED else '')
    else:
        srcs = '自動（雙規則一致）' + (f'（{RULED[c]}）' if c in RULED else '')
    o.append(f'<h4>③ 階段判定</h4><div><b>{g}｜{STN[g]}{SUBC.get(c, "")}</b>　定案來源：{srcs}　｜　規則 M＝{M}／規則 N＝{N}</div>')
    if c in LOCK and not (M == N == g):
        o.append(f'<div style="color:#B93030;font-weight:700">鎖定與雙規則不符：鎖定 {g}／M={M}／N={N}，照鎖定執行</div>')
    o.append(f'<h4>④ 拜訪策略</h4><div>{t["strat"]}</div>')
    if r1 == 'real':
        o.append('<div style="font-size:13px;color:#636E7A">法則 R1 觸發（單月 ≥ 基期 3 倍）：依 R1，先查架上庫存是否被打空。</div>')
    elif r1 == 'low':
        o.append('<div style="font-size:13px;color:#636E7A">法則 R1 觸發（單月 ≥ 基期 3 倍）：屬低基期形式觸發，例行查庫存即可。</div>')
    o.append(f'<div class="one"><b>這次最該優先談的一件事：</b>{t["one"]}</div><h4>⑤ 誠實提醒</h4><div>{t["rem"]}</div></div></details>')
    return ''.join(o)

if __name__ == '__main__':
    out = build()
    open('/home/claude/out/index.html', 'w', encoding='utf-8').write(out)
    print(len(out), {g: sum(1 for c in CODES if FS[c] == g) for g in 'AQBCDE'})
