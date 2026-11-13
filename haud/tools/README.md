# 佑全 HAUD 分析端工具（規則主檔〈方法升級計畫〉M1）

只放程式與已公開於報告之彙總期望值；**不放原始 Offtake、店層級銷量明細或已交付原檔**。

| 檔案 | 用途 |
|---|---|
| `hauddata.py` | 讀檔、清理（重複列加總、店碼合併）、第零步機械性檢查（含 S6 之 0 與缺漏清單） |
| `engine.py` | 參數化分析引擎：窗口、雙規則 M／N、恢復缺口、可搬動量、量池、相關係數 |
| `regress.py`＋`regress/<期別>.json` | 回歸測試：新檔重跑既往期別，分辨「原始檔歷史改寫」與「判定差異」 |
| `gate.py` | 交付前總檢查：v1／v2 格式、時效、門市稱呼、跨檔一致、契約版號引用、回歸 |
| `timeliness_check.py` | 到店檢查點時效（歷史裁定第 16 條） |
| `alert_v2_validate.py` | 警示檔 v2 自檢（閉環契約第 2 節） |
| `report_reader.py` | App 回報讀回（閉環契約第 6 節） |
| `legacy_2026-10/` | 2026-10 期重構前原樣封存，**不得直接用於新期**；深查與三榜 HTML 建置腳本待 2026-11 期以線上版為基準重建 |

驗證：2026-11-13 以 2026-10 原始檔重跑，2026-09、2026-10 兩期之月合計、恢復缺口、相關係數、量池、微量店、26 家 M／N 與可搬動量全部與已裁定紀錄一致。

## 每期用法
```
python3 regress.py <本期Excel>                         # 第零步第 8 項
python3 -c "from hauddata import *; import json; print(json.dumps(step0_report(load_raw('<本期Excel>')), ensure_ascii=False, default=str, indent=1))"
python3 gate.py --latest <YYYY-MM> --json <App檔> --index index.html --ledger 期別帳本.md --facts 事實表.md --rules 規則主檔.md --contract-version <現行> --haud-total <本期> --excel <本期Excel>
python3 regress.py --build <本期Excel> <YYYY-MM>       # 第六步：本期裁定定案後建立期望值
```

### gate.py 門市稱呼掃描（2026-11-13 補強）
帶 `--facts` 時以名冊店碼為準，掃描期別帳本、事實表、規則主檔與 `--doc` 帶入之 SOP：店碼須置於中文名稱之後（`名稱（店碼）`）；「店碼在前」與獨立店碼皆列為失敗。略過：「」內原文、JSON `name` 欄範例、版本沿革與附錄原文。index.html、rank.html 與對話文字不在掃描範圍，須人工確認。

```
python3 gate.py --latest 2026-10 --json <App檔> --index index.html \
  --ledger 佑全_期別帳本.md --facts 佑全_事實表.md --rules 規則主檔.md \
  --doc 深查SOP.md --doc 三榜SOP.md --contract-version 2.1 --haud-total 198 --excel <Offtake.xlsx>
```
