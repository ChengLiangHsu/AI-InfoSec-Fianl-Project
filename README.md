# 無人機田間試驗評估智慧代理人

**人工智慧與資訊安全期末專題提案**

* **日期：** Oct 9, 2026
* **提案人：** @Leo
* **核心定位：** 以高解析度、地面取樣距離（Ground Sample Distance, GSD）$\text{GSD} < 1\text{ cm/px}$ 無人機正射影像為輸入，結合植保領域知識與分析工具，由 AI Agent 評估田間試驗藥效並產出可追溯證據之報告草稿。

---

## 提案章節目錄

| 章節 | 檔案名稱 | 核心內容摘要 |
| :--- | :--- | :--- |
| **00. 概述** | [00_overview.md](docs/00_overview.md) | 專題定位、成員分工（Domain Lead / System Lead）、可用真實資料集（4RL、Concil 等） |
| **01. 摘要** | [01_abstract.md](docs/01_abstract.md) | 提案摘要（依 Motivation, Challenge, Solution, Method, Evaluation, Findings 結構） |
| **02. 緒論** | [02_introduction.md](docs/02_introduction.md) | 研究背景、田間試驗核心痛點、現有做法限制、創新點與 5 大預期貢獻 |
| **03. 文獻** | [03_related_work.md](docs/03_related_work.md) | 農業 VLM/Agent、分割模型、UAV 植生指標、領域規範文獻及 14 篇重點論文彙整表 |
| **04. 深入** | [04_deep_research.md](docs/04_deep_research.md) | 5 個核心思維模式（UTC 優先等）、3 大專業爭論、10 個深度技術與領域理解問答 |
| **05. 設計** | [05_proposed_scheme.md](docs/05_proposed_scheme.md) | 系統架構（Mermaid 圖）、執行流程圖、演算法虛擬碼（Algorithm 1）與可行性分析 |
| **06. 規劃** | [06_execution_plan.md](docs/06_execution_plan.md) | 兩人分工表、15 週開發里程碑與 GitHub / `DESIGN.md` 目錄結構規範 |
| **07. 文獻** | [07_references.md](docs/07_references.md) | 正文引用之 22 篇文獻出處與待補充之領域規範（TACTRI / EPPO） |

---

## 專案追蹤與管理

* [TODO.md](TODO.md)：專案待辦事項與里程碑查核點
* [REFERENCE.md](REFERENCE.md)：外部文獻與標準規範備忘錄