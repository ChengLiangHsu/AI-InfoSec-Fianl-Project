# 6. 分工、時程與 GitHub / DESIGN.md

### 分工表

| 工作項 | 郭乃瑋 (Domain) | 許承諒 (AI/System) |
| :--- | :--- | :--- |
| **Proposal 文件** | Abstract、Introduction、Related Work 領域半、Deep Research | Related Work AI 半、Architecture、Flowchart、Pseudocode |
| **資料** | 整理 4RL / Concil 影像、GeoJSON、處理表、人工調查；去識別化 | 資料讀取與 CRS 對齊模組 |
| **影像工具** | 指標定義、干擾規則、ground truth 對齊、驗證 | 小區切割、分割模型（SAM 2.1 / YOLO-seg）、計數工具封裝為 tools |
| **領域知識庫** | 撰寫 TACTRI / EPPO / 公式條目、藥害分級 | RAG 建置（chunk、embedding、retriever） |
| **Agent** | 設計推理規則與例外（UTC、CV、單時點） | Planner、tool calling、證據鏈驗證、報告模板 |
| **實驗** | 定義 baseline 與 metrics、人工結論對照 | 跑實驗、VLM baseline、統計分析 |
| **交付** | PPT 動機 / 領域 / 結果 | GitHub、README.md、DESIGN.md、Demo video |

### 時程（草案）

| 週次 | 里程碑 |
| :--- | :--- |
| **W1–W2（10月中）** | Proposal 文件 + PPT；GitHub repo 與 `DESIGN.md v0` 建立 |
| **W3–W5** | 資料整理與去識別化；小區切割 + 指標工具可跑 4RL 全部 24 小區 |
| **W6–W8** | SAM 2.1 / YOLO-seg 分割；干擾遮罩；指標 vs. ground truth 相關分析 |
| **W9–W11** | 知識庫 + Planner agent + 工具整合；證據鏈輸出 |
| **W12–W13** | 實驗：baseline 比較、Concil 第二案例；撰寫 Results / Limitations |
| **W14–W15** | Final PPT（> 20 頁）、YouTube demo（> 10 min）、handover package |

### GitHub Repository 建議結構

```text
uav-trial-assessor/
├── README.md               # 專題介紹、Installation、How to Run、Demo
├── DESIGN.md               # Problem → Requirements → Architecture... → Results
├── data/                   # 去識別化小區級資料、GeoJSON 範例（原始影像另置或抽樣）
├── knowledge_base/         # TACTRI / EPPO / 公式 / 生育期 Markdown
├── tools/                  # 工具庫
│   ├── plot_segmentation.py
│   ├── indices.py
│   ├── interference_mask.py
│   ├── segment_sam.py
│   ├── count_template.py
│   └── stats.py
├── agent/                  # 智慧代理人模組
│   ├── planner.py
│   ├── tool_registry.py
│   ├── evidence.py
│   └── report.py
├── experiments/            # notebooks、評估腳本、結果
└── docs/                   # Proposal、PPT、架構圖
```

> **`DESIGN.md` 規範**：從 Proposal 階段即建立，依規範章節：Problem、Requirements、Architecture（5.1）、Components、Data Flow（5.2）、AI Model、Domain Knowledge、Algorithm（5.3）、Implementation Mapping、How to Run、Results、Limitations。
