# 佑全 HAUD 分析端工具（主檔〈方法升級計畫〉M1）

只放程式，不放原始 Offtake、店層級明細或已交付原檔。

| 檔案 | 用途 | 依據 |
|---|---|---|
| `timeliness_check.py` | 到店檢查點時效把關（JSON checkpoints／checks、index.html、主檔必查點） | 主檔歷史裁定第 16 條 |
| `alert_v2_validate.py` | 警示 JSON v2（yq-alert-2）交付前自檢，比照 App v1.5.101 匯入規則 | 閉環契約 v2.0 第 2.6 節 |
| `report_reader.py` | 讀回 App 匯出（yq-report-1，v2.0 語義），來源雜湊／題目定義核對與證據分級 | 閉環契約 v2.0 第 6 節 |

分析引擎與建置腳本將於 2026-11 期 M1 首次建置時加入。
