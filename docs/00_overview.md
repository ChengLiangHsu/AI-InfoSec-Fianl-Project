# 期末專題提案：UAV Field-Trial Assessor Agent

**日期：** Oct 9, 2026  
**提案人：** @Leo  

---

## 專題概述

本專題提出 **UAV Field-Trial Assessor Agent（無人機田間試驗評估智慧代理人）**：以高解析度（$\text{GSD} < 1\text{ cm}$）無人機正射影像為輸入，自動完成試驗小區切割、植生指標計算、雜草/病蟲害傷害偵測，並結合作物保護（Crop Protection, CP）領域知識（試驗設計、藥效計算公式、登記試驗規範）推理出各處理的藥效評估與建議，產出可追溯證據的試驗報告草稿。

* **定位**：AI Agent + Domain Knowledge（植保/田間試驗）+ Data Analytics（影像指標 + 統計）+ Real-World Application（農藥登記試驗報告）。

---

## 為何這題適合本組

| 角色 | 成員背景 | 負責面向 |
| :--- | :--- | :--- |
| **Domain Lead（農業/植保）** | 郭乃瑋 - Bayer 產品開發、TACTRI 登記試驗、UAV 遙測 | 試驗資料與 ground truth、領域知識庫、評估指標設計、結果驗證 |
| **AI/System Lead（資訊）** | 許承諒 - 資訊背景 | Agent 架構、影像模型（分割/偵測）、Tool/RAG 整合、GitHub、DESIGN.md |

### 手上可用的真實資料
> 皆為實際田間試驗 UAV 正射影像，$\text{GSD } 0.85 \sim 0.9\text{ cm}$

| 資料集 | 作物 / 目標 | 設計 | Ground Truth |
| :--- | :--- | :--- | :--- |
| **4RL（廣西 2026）** | 水稻二化螟 + 縱捲葉蟲藥效 | RCBD，8 處理 $\times$ 3 重複，24 小區 | 幼蟲數、捲葉率（$0 \sim 50\text{ DAA}$ 多時點） |
| **Concil（民雄）** | 水稻鴨舌草除草劑藥效 | 農慣法 vs. 處理對半分區 | RGB + 多光譜（NDRE），有青苔干擾 |
| **Wheat FHB（中國）** | 小麥赤黴病 | 多小區 | 病情指數、DON 毒素、產量 |
| **育苗箱計數** | 水稻育苗場 | ROI 內計數 | 人工點數（233 箱） |

> **補充**：具體題目名稱、資料集範圍可在 proposal 階段再收斂；現階段先以 4RL + Concil 兩個資料集作為主要 case study。
