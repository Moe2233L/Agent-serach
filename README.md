# Research Agent - AI 智能研究助手🔍

基于 **FastAPI + Vue 3 + LangChain + OpenAI** 构建的全栈 AI 研究助手。

输入一个研究主题，AI 会自动完成**任务规划 → 多源搜索 → 信息总结 → 报告生成**的全流程，整个过程通过 SSE 实时推送进度，让你在浏览器中亲眼见证研究报告的诞生。

## 功能特性

- **一键研究**：输入主题，AI 自动将主题分解为多个可独立搜索的子任务
- **深度研究模式**：开启后对每个子任务最多迭代 3 轮搜索（gap evaluation → 精准搜索词 → 再搜索），直到信息充分
- **多引擎搜索**：基于 DDGS 进行多关键词并发搜索，获取丰富原始资料
- **并发执行**：子任务并行执行搜索与总结，大幅缩短等待时间
- **网页全文提取**：LLM 自动评估搜索结果价值，精选最多 2 个优质来源提取完整文章内容（5000+ 字），取代仅几十字的搜索摘要，大幅提升报告深度
- **实时进度反馈**：SSE 推送驱动可视化步骤条 + 渐变进度条 + 实时日志 + 子任务迭代轮次标记 + 全文提取状态，每个阶段清晰可见
- **专业报告生成**：LLM 生成结构化研究报告（标题 / 摘要 / 正文 / 结论 / 参考文献），支持 Markdown 一键下载
- **追问机制**：研究完成后可基于已有报告进行追问，AI 结合新搜索结果针对性回答
- **历史记录**：自动保存研究历史至 localStorage，支持回顾查看 + 追问
- **玻璃拟态 UI**：暗色主题配以毛玻璃效果、粒子网络动画背景、渐变光晕和流畅动效

## 技术栈

| 层级 | 技术 |
| :--- | :--- |
| 前端框架 | Vue 3 (Composition API, `<script setup>`) + TypeScript |
| 构建工具 | Vite |
| Markdown 渲染 | marked |
| 后端框架 | FastAPI + Uvicorn (ASGI) |
| AI 框架 | LangChain + LangChain-OpenAI |
| 大语言模型 | OpenAI（兼容任意 OpenAI API 格式的模型） |
| 搜索引擎 | DDGS（多引擎元搜索，支持代理） |
| 内容提取 | BeautifulSoup 4 + lxml（LLM 精选页面全文提取） |
| 实时通信 | Server-Sent Events (SSE) |
| 样式方案 | CSS 自定义属性 + Glassmorphism 主题 |

## 架构概览

```
┌────────────────────────────────────────────────────────────┐
│                    Frontend (Vite :5173)                    │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ App.vue  │  │ ResearchCard │  │ MarkdownViewer       │  │
│  │ SSE 消费  │→ │ 步骤/进度/日志 │→ │ 报告渲染/下载          │  │
│  │ deep_mode│  │ 折叠/展开    │  │ ParticleNetwork      │  │
│  └────┬─────┘  └──────────────┘  │ 粒子动画背景          │  │
│       │                          └──────────────────────┘  │
│  ┌────┴─────┐                                              │
│  │ utils/   │                                              │
│  │ sse.ts   │— SSE 流解析通用函数                            │
│  └──────────┘                                              │
└───────────────────────────┬────────────────────────────────┘
                            │ POST /research/stream (SSE)
                            │ POST /research/{id}/followup (SSE)
                            │ event: log / phase / subtasks / ...
                      ┌─────┴──────┐
                      │ Vite Proxy │
                      └─────┬──────┘
┌───────────────────────────┴────────────────────────────────┐
│                    Backend (Uvicorn :8000)                  │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ main.py  │→ │   agent.py   │→ │    services/          │  │
│  │ FastAPI  │  │ ResearchAgent│  │ todo_planner          │  │
│  │ SSE 端点  │  │ 三阶段编排+   │  │ search_tool           │  │
│  │ followup │  │ 迭代搜索+追问 │  │ task_summarizer       │  │
│  └──────────┘  │ + 全文提取    │  │   (含 gap evaluation  │  │
│                └──────────────┘  │    + URL 评估)         │  │
│                                  │ report_writer          │  │
│                                  │   (含追问回答)          │  │
│                                  │ content_extractor      │  │
│                                  │   (BS4 + lxml 全文提取) │  │
│                                  └────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 研究流程

```
输入主题 ──→ [规划阶段] ──→ [执行阶段] ──→ [报告阶段] ──→ 完成
               LLM 分解      并发搜索+总结      LLM 撰写     可追问
               ↓               ↓ (深度模式)       ↓
             subtasks       迭代最多3轮        report
             事件             gap evaluation    事件
                             精准搜索词重搜
                             子任务迭代轮次标记
                             ↓ 每次搜索后
                             LLM 评估 URL 价值
                             ↓ 精选最多 2 个
                             提取网页全文 5000+ 字
                             ↓ 注入搜索结果供总结
```

## 快速开始

### 前置条件

- Python 3.10+
- Node.js 18+
- OpenAI API Key（或兼容 API 的第三方服务，如 DeepSeek、通义千问等）

### 1. 安装后端

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.3
SEARCH_MAX_RESULTS=5
LLM_TIMEOUT=60
```

### 2. 启动后端

```bash
# 从项目根目录启动
python -m backend.src.main

# 终端输出: Uvicorn running on http://0.0.0.0:8000
```

验证后端是否正常运行：

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 3. 安装并启动前端

```bash
cd frontend
npm install
npm run dev

# 终端输出: Local: http://localhost:5173
```

### 4. 使用

打开浏览器访问 **http://localhost:5173**, 输入研究主题（如"人工智能在医疗领域的应用"），点击"开始研究"即可。

## 使用指南

| 步骤 | 操作 | 说明 |
| :--- | :--- | :--- |
| 1 | 输入研究主题 | 支持中文、英文或混合输入 |
| 2 | 调整搜索条数 | 滑块 2-15 条，控制每个子任务的搜索结果数量 |
| 3 | 调整子任务数 | 滑块 1-6 个，控制主题分解的粒度 |
| 4 | 开启深度研究 | 可选，开启后每个子任务最多迭代 3 轮搜索，直到信息充分 |
| 5 | 点击"开始研究" | 右侧面板展开，显示研究卡片 |
| 6 | 观察进度 | 步骤条 → 进度条 → 子任务芯片(含迭代轮次) → 日志，实时更新 |
| 7 | 查看报告 | 生成完成后自动展开，支持 Markdown 下载 |
| 8 | 历史追问 | 点击历史记录查看报告，可输入追问针对性地深入探讨 |

## 项目结构

```
Agent/
├── backend/
│   ├── requirements.txt          # Python 依赖清单
│   └── src/
│       ├── __init__.py
│       ├── main.py               # FastAPI 应用入口 + SSE /health + /research/stream 端点
│       ├── agent.py              # ResearchAgent 核心编排器（规划/执行/报告三阶段）
│       ├── config.py             # 环境配置加载（.env → Settings 单例）
│       ├── models.py             # Pydantic 数据模型（ResearchState, Subtask, SSE 事件等）
│       └── services/
│           ├── __init__.py
│           ├── todo_planner.py   # LLM 驱动的子任务规划
│           ├── search_tool.py    # DDGS 异步网络搜索
│           ├── task_summarizer.py # LLM 驱动的搜索结果总结（含 gap evaluation + URL 价值评估）
│           ├── report_writer.py  # LLM 驱动的完整报告生成（含追问回答）
│           ├── content_extractor.py # 精选页面全文提取（BS4 + lxml，合规限速）
├── frontend/
│   ├── package.json              # Node.js 依赖与脚本
│   ├── vite.config.ts            # Vite 配置（含开发代理）
│   └── src/
│       ├── main.ts               # Vue 应用入口
│       ├── style.css             # 全局样式 / CSS 变量 / 主题
│       ├── App.vue               # 主布局（左右双栏）+ SSE 事件消费
│       ├── types/
│       │   └── research.ts       # TypeScript 类型定义（SubtaskState, LogState, ResearchCardData）
│       ├── utils/
│       │   └── sse.ts            # SSE 流解析通用函数
│       └── components/
│           ├── ResearchCard.vue   # 研究卡片（步骤条 / 进度条 / 子任务 / 日志 / 报告 / 错误提示）
│           ├── MarkdownViewer.vue # Markdown 渲染与样式
│           └── ParticleNetwork.vue # Canvas 粒子背景动画
├── .env.example                  # 环境变量模板
└── README.md
```

## API 文档

### `GET /health`

健康检查端点。

**响应示例：**

```json
{ "status": "ok" }
```

### `POST /research/stream`

发起研究请求，返回 SSE 事件流。

**请求体：**

```json
{
  "topic": "量子计算最新进展",
  "max_results": 5,
  "subtask_count": 3,
  "deep_mode": false
}
```

**参数说明：**

| 参数 | 类型 | 默认值 | 范围 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `topic` | string | - | - | 研究主题，必填 |
| `max_results` | integer | 5 | 1-20 | 每个子任务的搜索结果数量 |
| `subtask_count` | integer | 3 | 1-8 | 子任务数量 |
| `deep_mode` | boolean | false | - | 开启深度研究模式(迭代搜索) |

### `POST /research/{research_id}/followup`

对已完成的研究进行追问，返回 SSE 事件流。

**请求体：**

```json
{
  "question": "能详细说说这个领域的最新突破吗？"
}
```

**参数说明：**

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `question` | string | 追问内容，必填 |

### SSE 事件流

| 事件名 | 触发阶段 | data 说明 |
| :--- | :--- | :--- |
| `log` | 全程 | `{ phase: string, message: string }` 阶段日志 |
| `phase` | 阶段切换 | `{ phase: "planning" \| "executing" \| "reporting" }` 阶段通知 |
| `subtasks` | 规划完成 | `{ subtasks: [{ id, title, query }] }` 子任务列表 |
| `subtask_status` | 执行中 | `{ id, status, title, iteration? }` 子任务状态变更(含迭代轮次) |
| `subtask_completed` | 子任务完成 | `{ id, title, summary, iteration }` 子任务完成通知 |
| `report` | 报告完成 | `{ report: "markdown string" }` 研究报告 |
| `report_chunk` | 报告流式生成 | `{ chunk: "string" }` 报告片段 |
| `completed` | 全部完成 | `{ research_id: string }` 研究结束 |
| `error` | 任意阶段 | `{ error: string }` 错误信息 |
| `followup_start` | 追问开始 | `{ question: string }` 追问发起通知 |
| `report_append_prefix` | 追问追加 | `{ prefix: string }` 追加到报告的 Markdown 前缀 |
| `followup_completed` | 追问完成 | `{ answer: string }` 追问回答完成 |

## 配置参考

所有配置项通过项目根目录下的 `.env` 文件加载：

| 环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | - | OpenAI API 密钥（必填） |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 基础地址，可替换为第三方兼容服务 |
| `LLM_MODEL` | `gpt-4o-mini` | 模型名称，需与 API 提供商匹配 |
| `LLM_TEMPERATURE` | `0.3` | 生成温度，范围 0-2，越低越确定 |
| `SEARCH_MAX_RESULTS` | `5` | 每个子任务的搜索结果上限 |
| `SEARCH_PROXY` | (空) | 搜索引擎使用的 HTTP/HTTPS 代理 |
| `LLM_TIMEOUT` | `60` | LLM 请求超时时间(秒)，防止网络卡住研究流程 |
| `SUBTASK_COUNT` | `3` | 默认子任务数量 |

## 本地开发

### 热重载开发

```bash
# 终端 1：后端（热重载）
uvicorn backend.src.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2：前端（HMR + API 代理）
cd frontend && npm run dev
```

### 构建生产版本

```bash
cd frontend
npm run build
# 产出在 frontend/dist/
```

### 代码质量

```bash
cd frontend
npm run build  # TypeScript 检查 + Vite 构建
```

## License

MIT
