# 無人機田間試驗評估智慧代理人

**人工智慧與資訊安全期末專題提案**

* **專案日期：** 2026 年 9 月 7 日至 12 月 21 日
* **提案人：** [@Kuonaiwei1126](https://github.com/Kuonaiwei1126)、[@ChengLiangHsu](https://github.com/ChengLiangHsu)
* **核心定位：** 以高解析度、地面取樣距離（Ground Sample Distance, GSD）< 1 cm/px 的無人機正射影像為輸入，結合植保領域知識與分析工具，由 AI Agent 評估田間試驗藥效並產出可追溯證據之報告草稿。

---

## 實作架構

後端採用三層 Clean Architecture：

```text
adapter → usecase → entity
```

* `entity`：田間試驗、證據與評估規則，不依賴外部框架。
* `usecase`：Agent 執行、資料匯入、試驗評估、證據驗證與報告流程；抽象 interface 位於 `usecase/port/`。
* `adapter`：FastAPI、Pydantic AI、SQLite、Rasterio、RAG 與檔案輸出的具體 implementation。
* `bootstrap.py`：建立 adapter 並注入 usecase；`main.py` 只負責啟動 ASGI app。

詳細分層、依賴圖與功能對應請見 [05. 系統設計](docs/05_proposed_scheme.md#clean-architecture-分層)，完整目錄請見 [06. 執行規劃](docs/06_execution_plan.md#github-repository-結構)。

---

## 提案章節目錄

| 章節 | 內容摘要 |
| :--- | :--- |
| [00. 概述](docs/report/00_overview.md) | 專題定位、成員分工、真實試驗資料集 |
| [01. 摘要](docs/report/01_abstract.md) | 研究動機、痛點、解法與預期成效 |
| [02. 緒論](docs/report/02_introduction.md) | 田間試驗背景、現有限制、五大預期貢獻 |
| [03. 相關文獻](docs/report/03_related_work.md) | 農業 VLM/Agent、植生指標與規範文獻整理 |
| [04. 深度探討](docs/report/04_deep_research.md) | 核心思維模式、關鍵爭論與技術 Q&A |
| [05. 系統設計](docs/report/05_proposed_scheme.md) | 系統架構圖、執行流程與演算法虛擬碼 |
| [06. 執行規劃](docs/report/06_execution_plan.md) | 15 週開發里程碑、分工與專案結構規範 |
| [07. 參考文獻](docs/report/07_references.md) | 22 篇論文文獻與 TACTRI / EPPO 法規標準 |

---

## 專案追蹤與管理

* [TODO.md](TODO.md)：專案待辦事項與里程碑查核點
* [REFERENCE.md](REFERENCE.md)：外部文獻與標準規範備忘錄
* [REQUIREMENT.md](REQUIREMENT.md)：作業要求與規範
