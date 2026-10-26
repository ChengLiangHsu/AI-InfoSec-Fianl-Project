# 6. 分工、時程與 GitHub / DESIGN.md

### 分工表

| 工作項 | [@Kuonaiwei1126](https://github.com/Kuonaiwei1126) (Domain) | [@ChengLiangHsu](https://github.com/ChengLiangHsu) (AI/System) |
| :--- | :--- | :--- |
| **Proposal 文件** | Abstract、Introduction、Related Work 領域半、Deep Research | Related Work AI 半、Architecture、Flowchart、Pseudocode |
| **PoC 原型 (Walking Skeleton)** | 規劃評估問答 Prompt、試驗對話測試案例 | 實作最小 Agent、FastAPI API 介面與核心服務連通測試 |
| **資料** | 整理 4RL / Concil 影像、GeoJSON、處理表、人工調查；去識別化 | 資料讀取與 CRS 對齊模組 |
| **影像工具** | 指標定義、干擾規則、ground truth 對齊、驗證 | 小區切割、干擾排除與植生指標計算工具封裝為核心服務模組 |
| **領域規則庫** | 整理 TACTRI / EPPO 準則與 Abbott 公式規則 | 實作 Python 確定性藥效計算與試驗檢核模組 |
| **Agent** | 設計推理規則與例外（UTC、CV、單時點） | Planner 整合真實工具、tool calling、證據鏈驗證、報告模板 |
| **實驗** | 定義 baseline 與 metrics、人工結論對照 | 跑實驗、VLM baseline、統計分析 |
| **交付** | PPT 動機 / 領域 / 結果 | GitHub、README.md、DESIGN.md、Demo video |

### 時程（草案）

| 週次 | 里程碑 |
| **W1–W2（10月中）** | Proposal 文件 + PPT；GitHub repo 與 `DESIGN.md v0` 建立；模組化服務骨架搭建（FastAPI 介面層 → Pydantic AI Agent → 核心服務層） |
| **W3–W5** | 資料整理與去識別化；小區切割 + 指標工具可跑 4RL 全部 24 小區 |
| **W6–W8** | 小區幾何切割；干擾遮罩排除；植生指標計算；指標 vs. ground truth 相關分析 |
| **W9–W11** | 試驗判定規則 + Planner agent 整合真實工具；證據鏈與報告草稿輸出 |
| **W12–W13** | 實驗：baseline 比較、Concil 第二案例；撰寫 Results / Limitations |
| **W14–W15** | Final PPT（> 20 頁）、YouTube demo（> 10 min）、handover package |

### GitHub Repository 結構

```text
uav-trial-assessor/
├── README.md               # 專題介紹、Installation、How to Run、Demo
├── DESIGN.md               # Problem → Requirements → Architecture... → Results
├── data/                   # 去識別化小區級資料、GeoJSON 範例（原始影像另置或抽樣）
├── src/
│   ├── api/                # FastAPI 路由與請求檢核
│   │   ├── app.py          # FastAPI 應用建置
│   │   ├── routers/        # 試驗評估與報告 API
│   │   └── schemas.py      # Pydantic 請求與回應資料結構
│   ├── agent/              # AI Agent 協調層
│   │   ├── report_agent.py # Pydantic AI Agent 與 Tool 定義
│   │   └── prompts.py      # 領域推理與報告生成 Prompts
│   ├── services/           # 核心業務與確定性演算法
│   │   ├── segmentation.py # 小區幾何切割與外緣 Buffer 校正
│   │   ├── indices.py      # 植生指標計算 (VARI, NDRE, EXG) 與干擾遮罩
│   │   ├── trial_rules.py  # Abbott 藥效公式與對照區 (UTC) 壓力檢核
│   │   └── report_generator.py # 報告草稿彙整與影像佐證輸出
│   ├── database/           # 資料庫持久化
│   │   ├── db.py           # SQLite 連線與初始化
│   │   └── models.py       # SQLModel 資料表記錄
│   └── main.py             # ASGI 啟動入口
├── tests/                  # 單元測試與整合測試
│   ├── test_segmentation.py
│   ├── test_indices.py
│   ├── test_trial_rules.py
│   └── test_api.py
├── experiments/            # 實驗評估腳本與測試結果
└── docs/                   # Proposal 文件、PPT 與架構圖
```

系統採用模組化服務架構，核心數值運算與藥效公式維持確定性純 Python 函式，由 Pydantic AI Agent 作為 Planner 調度工具與生成報告。

> **`DESIGN.md` 規範**：從 Proposal 階段即建立，依規範章節：Problem、Requirements、Architecture（5.1）、Components、Data Flow（5.2）、AI Model、Domain Knowledge、Algorithm（5.3）、Implementation Mapping、How to Run、Results、Limitations。
