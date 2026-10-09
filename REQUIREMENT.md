# 期末專題提案作業規範 (Final Project Proposal Requirements)

---

## 一、作業目的與基本要求

本期末專題旨在訓練學生完成一個從問題發現、資料蒐集、領域研究、AI 分析、系統設計，到實作與驗證的完整專案。專題應以真實世界問題為核心，原則上採用：

$$\text{AI Agent} + \text{Domain Knowledge} + \text{Data Analytics} + \text{Real-World Application}$$

> **核心導向**：學生不應只訓練一個 AI Model 或製作單純 Chatbot，而應設計一個具有特定專業能力的 **Domain AI Agent（領域智慧代理人）**，能夠理解使用者需求、取得與分析資料、結合領域知識進行推理，最後提供有依據的結果、預測、診斷或建議。

### 參考專案範例
* **AI Plant Doctor**（植物病害診斷與照護）
* **Energy Detective**（能源用量偵測與節能分析）
* **Warehouse Manager**（智慧倉儲物流管理）
* **Factory Doctor**（工廠設備預知保養與診斷）
* **Financial Analyst**（金融趨勢分析與風險評估）
* **Architect Assistant**（建築法規檢驗與輔助設計）
* **Pet Life Analyst**（寵物健康與行為生活分析）

---

## 二、Final Project Proposal（占總成績 10%）

Proposal 為期末專題第一階段，占成績 10%，須完成以下四大核心章節：

### 1. Abstract 摘要
摘要應形成完整的研究故事，建議採用以下 **A–F 六段式結構**：

* **A. Attention Getter — Motivation**  
  以具體證據說明「為什麼這個問題現在很重要、創新或有趣」。應優先引用 2025–2026 年的研究論文、政府/產業報告、統計資料、公開資料集、科技新聞或真實案例，**不應只寫「近年來 AI 快速發展」**。
* **B. But — Challenge**  
  指出現有技術、應用或研究仍存在的問題、限制與 Research Gap。
* **C. Cure — Proposed Solution**  
  清楚說明：「為了解決上述問題，本專題提出一個新的 `______` AI Agent / System。」
* **D. Development — Method**  
  簡述系統如何整合 AI、資料來源、分析方法及 Domain Knowledge。
* **E. Experiments — Evaluation**  
  說明預計使用的 Dataset、Case Study、Baseline、Evaluation Metrics 或使用者測試方法。
* **F. Findings — Expected Outcomes**  
  Proposal 尚未完成實驗者應寫 Expected Findings / Expected Outcomes，**嚴禁虛構實驗結果**。

```text
Abstract Story 脈絡：
Attention Getter → But → Cure → Development → Experiments → Findings
```

---

### 2. Introduction 緒論
Introduction 必須回答：**Why is this project worth doing?**（為什麼這個專案值得做？）

建議使用 **A–F 結構**撰寫（重要論述應盡可能有客觀證據與來源支持）：
* **A. Attention Getter**：以公開數據、權威研究、產業報告或實際案例引題。
* **B. Background**：說明應用領域、目標受眾（使用者）及現行技術背景。
* **C. Problem**：明確定義真正需要被解決的核心問題。
* **D. Existing Limitations**：說明目前既有方法的不足、限制與挑戰。
* **E. Innovation**：說明本專題之方法與既有系統的不同之處與創新點。
* **F. Contributions**：條列本專題預期的主要技術與應用貢獻。

---

### 3. Related Work 相關研究
Related Work 應兼顧技術與領域本質：
* 內容比例分配：**約 1/2 AI Technology + 1/2 Domain Know-how**
* *範例*：若題目為「AI Plant Doctor」，不能只探討 CNN、Transformer、LLM 等演算法，也必須深入研究植物病害機理、環境微氣候因子、土壤濕度、農業感測器及農業資料集。
* **研究工具**：可使用 Perplexity、Connected Papers、NotebookLM、Google Scholar、GitHub、Udemy 等工具輔助研究，但必須核實原始文獻來源及內容正確性。

#### 文獻整理摘要表 (Article Summary Table)
Proposal **必須包含**下表格式：

| Ref. | Year | Problem | AI Method | Domain Knowledge | Dataset | Findings | Limitation |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| [1] | 2025 | | | | | | |
| [2] | 2026 | | | | | | |

最後必須以邏輯鏈歸納出研究切入點：
$$\text{Existing Research} \longrightarrow \text{Limitations} \longrightarrow \text{Research Gap} \longrightarrow \text{Our Project}$$

---

## 三、Deep Research：三大核心問題

每組必須針對所選定的專業領域進行深入探討，回答以下三大核心問題：

### Q1. 五個核心思維模式 (5 Core Mindsets)
* **問題**：這個領域的專家普遍認同的五個核心思維模式是什麼？
* **要求**：每一項思維模式皆須詳細說明其**核心意義**、**具體佐證**，以及**如何具體影響本系統的架構設計**。

### Q2. 三個最重要的專業爭論 (3 Key Professional Controversies)
* **問題**：這個領域專家爭論最激烈的三個問題是什麼？
* **建議架構**：
  $$\text{觀點 A} \longleftrightarrow \text{觀點 B} \longrightarrow \text{Evidence} \longrightarrow \text{Consensus} \longrightarrow \text{Unresolved Problems}$$
* **要求**：說明雙方最有力的支持論點與證據、目前的學界/業界共識，以及至今仍懸而未決的挑戰。

### Q3. 十個深度理解問題 (10 Deep Understanding Questions)
* **問題**：設計 10 個專業問題，用以驗證一個人是「真正深入理解該領域」，還是僅停留在「死記硬背名詞」。
* **涵蓋層次**：問題應具備推論深度，涵蓋 **Why**、**What-if**、**Trade-off**、**Failure Case**、**Evidence**、**Comparison**、**Design Decision**、**Real-world Scenario** 等面向。

---

## 四、Proposed Scheme / Proposed Design 系統規劃與設計

Proposed Scheme 是本提案最核心的技術內容，必須將專題設計為一個具備實作可行性的 AI Agent System。

### 系統推薦運作架構
```text
① User / Application Scenario
  └→ ② Query / Input
        └→ ③ Planner & Reasoning Agent
              └→ ④ Data Acquisition / Retrieval
                    └→ ⑤ Analytics Engine
                          └→ ⑥ Domain Knowledge Integration
                                └→ ⑦ Decision / Recommendation
                                      └→ ⑧ Output & Interaction
```
* **資料來源**：可整合 IoT Sensor、Database、CSV/Excel、API、Web Scraping、Open Data、PDF/Research Paper、Knowledge Base、Vector DB 等。

---

### Proposal 必須提供的三種技術表示

#### 1. System Architecture (系統架構圖)
必須繪製完整的系統架構圖，圖中主要模組應以標號（①、②、③……）明確標記，並在正文內容中逐一詳細說明各模組職責。

#### 2. Flowchart (系統流程圖)
清楚呈現由輸入到輸出的完整處理邏輯：
$$\text{Input} \longrightarrow \text{Processing} \longrightarrow \text{AI / Analytics} \longrightarrow \text{Decision} \longrightarrow \text{Output}$$
必要時需包含 **Decision 條件分支**、**Loop 迭代迴圈**、**Exception 例外處理機制** 或 **Human-in-the-loop 人機協同互動點**。

#### 3. Pseudocode (核心演算法虛擬碼)
核心演算法必須提供具備**行號**的 Pseudocode，參考格式如下：

```algo
Algorithm 1: Domain AI Agent
Input : User Query Q
Output: Domain-specific Result R

01: Receive user query Q
02: Analyze intent and requirements
03: Decompose Q into subtasks
04: Select appropriate data sources and tools
05: Retrieve and preprocess relevant data
06: Analyze data using AI/ML methods
07: Integrate results with domain knowledge
08: Generate candidate solutions
09: Evaluate evidence, uncertainty, and limitations
10: Generate final recommendation R
11: Present results and supporting evidence
12: return R
```

---

## 五、AI 使用規範

> **AI is OK — 鼓勵並允許合理使用 AI**

* **允許工具**：ChatGPT、Claude、Gemini、NotebookLM、Perplexity、Connected Papers、GitHub Copilot、Codex 等。
* **適用範疇**：Research、Literature Review、Coding、Debugging、Architecture Design、Data Analysis、Pseudocode、Documentation、PPT 製作等。
* **基本責任原則**：
  > **AI 可以幫你完成工作，但你必須能解釋它做了什麼、為什麼這樣設計，以及如何驗證結果。**
* **考核方式**：教師將針對 Architecture、DESIGN.md、引用文獻、資料來源、程式碼邏輯與實驗結果進行口頭質詢。

---

## 六、繳交要求與 Final Handover

### A. Proposal 階段繳交清單
1. **Proposal Document**：涵蓋 Abstract、Introduction、Related Work、Deep Research、Proposed Scheme、References。
2. **Proposal PPT**：完整呈現研究動機、文獻、Research Gap、Agent Design、Architecture、Flowchart、Pseudocode。
3. **GitHub Repository**：建立正式專題儲存庫。
4. **DESIGN.md**：自 Proposal 階段即著手建立並持續更新的系統設計規格書。

---

### B. Final Project 最終交付標準 (Handover Package)

| 必繳項目 | 最低要求 |
| :--- | :--- |
| **GitHub** | 完整 Source Code、資料/資料來源、執行與測試方式 |
| **README.md** | 專題介紹、Installation 指南、How to Run 步驟、Demo 展示 |
| **DESIGN.md** | Architecture、Components、Data Flow、AI Model、Domain Knowledge、Algorithm、Implementation Mapping、Results、Limitations |
| **Final PPT** | 超過 20 頁（$>20\text{ pages}$） |
| **Final Video** | 上傳至 YouTube 之專題簡報與 Demo 影片，片長超過 10 分鐘（$>10\text{ min}$） |
| **Experiments** | Dataset、Evaluation Metrics、Results 分析、Baseline Comparison |
| **Conclusion** | Contributions、Limitations、Future Work |

#### DESIGN.md 核心說明路徑
$$\text{Problem} \rightarrow \text{Requirements} \rightarrow \text{Architecture} \rightarrow \text{Components} \rightarrow \text{Data} \rightarrow \text{AI/Analytics} \rightarrow \text{Domain Knowledge} \rightarrow \text{Algorithm} \rightarrow \text{Implementation} \rightarrow \text{How to Run} \rightarrow \text{Results}$$

> **Final Handover 驗收標準**：
> 不僅僅是「程式可以在本機執行」，而是：**即使原開發者不在場，接手者僅憑 GitHub Repo + README.md + DESIGN.md 即可順利理解系統原理、重現實驗、執行測試並接續後續開發。**

---

## 七、Proposal 評分標準（10%）

| 評分項目 | 評核重點 | 比例 |
| :--- | :--- | :---: |
| **Introduction** | 研究重要性、研究動機、客觀佐證 (Evidence)、創新性 (Innovation) | 20% |
| **Related Work** | AI 技術與領域知識平衡（AI + Domain）、Article Summary 表格完整性 | 20% |
| **Deep Research** | 5 Mindsets + 3 Controversies + 10 Deep Questions 之深度與嚴謹度 | 20% |
| **Proposed AI Agent** | 代理人架構設計與完整 System Architecture | 20% |
| **Technical Feasibility** | Flowchart、Pseudocode 邏輯嚴密性與技術可行性 | 15% |
| **GitHub & Documentation**| GitHub 專案設置、DESIGN.md 架構與文件整體完成度 | 5% |
| **Total** | | **100%** |

---

## 核心評量原則總結

> **不要只做一個 Model，也不要只做一個 Chatbot。**  
> 請設計一個懂領域、會取得資料、會分析、會推理、能提供有用結果，而且能用客觀證據驗證的 **Domain AI Agent**。

### 專題完整故事鏈
$$\text{Public Evidence} \longrightarrow \text{Important Problem} \longrightarrow \text{AI + Domain Research} \longrightarrow \text{Deep Understanding} \longrightarrow \text{Research Gap}$$
$$\downarrow$$
$$\text{Proposed AI Agent} \longrightarrow \text{Architecture / Flowchart / Pseudocode} \longrightarrow \text{Implementation} \longrightarrow \text{Experiments} \longrightarrow \text{Final Handover}$$