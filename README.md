# 408 考研辅助 Agent

基于 RAG（检索增强生成）技术的 408 计算机考研复习助手，覆盖数据结构、操作系统、计算机组成原理、计算机网络四科。

## 功能概览

| 模块 | 描述 |
|------|------|
| **知识问答** | 基于教材内容的智能检索与回答，支持标准 RAG 和 Agentic RAG 自动路由 |
| **知识图谱** | 交互式知识点关系可视化，支持按学科筛选、节点搜索、子图探索 |
| **练习刷题** | 教材习题浏览 + AI 智能出题（选择/填空/简答/算法/综合） |
| **试卷分析** | 上传试卷文件或粘贴题目文本，AI 分析解题思路与知识点 |
| **错题本** | 收录错题自动检索原题解析，支持按科目筛选、批量删除、导出 Word |

## 技术栈

### 后端
- **框架**: FastAPI 0.115+
- **LLM**: OpenAI API / Ollama (本地模型)
- **Embedding**: BAAI/bge-large-zh-v1.5 (sentence-transformers)
- **向量数据库**: ChromaDB 0.5+
- **编排**: LangChain 0.3+, LangGraph
- **数据库**: SQLite (aiosqlite) - 错题存储
- **文档生成**: python-docx
- **Python**: 3.12+

### 前端
- **框架**: React 18 + TypeScript
- **构建**: Vite 6
- **样式**: Tailwind CSS 3.4
- **图谱可视化**: Cytoscape.js
- **图标**: Lucide React
- **通知**: Sonner

## 项目结构

```
408-robot/
├── backend/                  # 后端服务
│   ├── app/
│   │   ├── main.py           # FastAPI 入口，lifespan 初始化
│   │   ├── config.py         # Pydantic Settings 配置
│   │   ├── llm_factory.py    # LLM 提供者工厂
│   │   ├── agent.py          # Agent 主类
│   │   ├── api/              # API 路由
│   │   │   ├── knowledge.py  #   /api/knowledge - 知识检索
│   │   │   ├── graph.py      #   /api/graph - 知识图谱
│   │   │   ├── practice.py   #   /api/practice - 练习刷题
│   │   │   ├── exam.py       #   /api/exam - 试卷分析
│   │   │   └── mistakes.py   #   /api/mistakes - 错题本
│   │   ├── skills/           # 技能模块
│   │   │   ├── base_skill.py
│   │   │   ├── knowledge_retrieval_skill.py
│   │   │   ├── knowledge_graph_skill.py
│   │   │   ├── answer_generation_skill.py
│   │   │   ├── agentic_rag_skill.py
│   │   │   ├── smart_answer_skill.py
│   │   │   ├── question_location_skill.py
│   │   │   ├── quiz_generation_skill.py
│   │   │   └── docx_generation_skill.py
│   │   ├── models/           # 数据模型
│   │   │   ├── chunk.py
│   │   │   ├── mistake.py
│   │   │   └── graph.py
│   │   └── utils/            # 工具模块
│   │       ├── dependencies.py
│   │       ├── embeddings.py
│   │       ├── exceptions.py
│   │       └── logging.py
│   ├── scripts/
│   │   ├── ingest_chunks.py  # 数据入库脚本
│   │   └── build_graph.py    # 知识图谱构建脚本
│   ├── data/                 # 运行时数据
│   │   ├── vector_db/        # ChromaDB 持久化
│   │   ├── graph/            # 知识图谱 JSON
│   │   ├── mistakes.db       # 错题 SQLite
│   │   ├── exports/          # 导出的 Word 文件
│   │   └── uploads/          # 上传的试卷文件
│   └── config.yaml           # 应用配置
│
├── frontend/                 # 前端应用
│   ├── src/
│   │   ├── App.tsx           # 根组件 + 页面路由
│   │   ├── pages/            # 5 个功能页面
│   │   ├── components/       # 通用组件 + UI 组件库
│   │   ├── hooks/            # 自定义 Hooks
│   │   └── lib/              # API 客户端 + 常量 + 工具
│   └── vite.config.ts        # Vite 配置 (API 代理)
│
├── data_process/             # 数据预处理
│   ├── pdf_processor.py      # PDF 解析 + 分块
│   ├── config.py
│   └── utils.py
│
├── data/                     # 原始 PDF 教材
├── processed/                # 处理后的 chunks JSON
└── agent_spec.md             # 完整技术规格文档
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python 包管理)
- Ollama (可选，本地模型推理) 或 OpenAI API Key

### 1. 后端启动

```bash
cd backend

# 安装依赖
uv sync

# 配置 (编辑 config.yaml)
# - 选择 LLM 提供者: ollama 或 openai
# - 如用 OpenAI，设置环境变量:
#   export OPENAI_API_KEY=sk-xxx

# 首次运行: 入库数据 (需要先将 processed/ 下的 chunks JSON 准备好)
uv run python scripts/ingest_chunks.py
uv run python scripts/build_graph.py

# 启动后端服务 (端口 8000)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器 (端口 5173)
npm run dev
```

浏览器访问 `http://localhost:5173`

### 3. 使用 Ollama 本地模型 (可选)

```bash
# 安装 Ollama: https://ollama.com
# 拉取模型
ollama pull deepseek-r1:8b

# 确认 config.yaml 中:
# llm.provider: "ollama"
# llm.ollama.model: "deepseek-r1:8b"
```

## API 接口

后端运行后可访问自动生成的 API 文档: `http://localhost:8000/docs`

### 主要端点

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/knowledge/search` | 向量相似度搜索 |
| `GET` | `/api/knowledge/chunk/{id}` | 获取 chunk 详情 |
| `POST` | `/api/knowledge/ask` | 智能问答 (RAG) |
| `GET` | `/api/knowledge/chapters` | 获取章节目录 |
| `GET` | `/api/graph/` | 获取完整知识图谱 |
| `GET` | `/api/graph/node/{id}` | 获取节点子图 (BFS) |
| `GET` | `/api/graph/search` | 模糊搜索节点 |
| `GET` | `/api/practice/exercises` | 获取教材习题 |
| `POST` | `/api/practice/generate` | AI 生成练习题 |
| `POST` | `/api/exam/upload` | 上传试卷文件 |
| `POST` | `/api/exam/analyze` | 试卷题目分析 |
| `POST` | `/api/mistakes/` | 添加错题记录 |
| `GET` | `/api/mistakes/` | 查询错题列表 |
| `DELETE` | `/api/mistakes/{id}` | 删除错题 |
| `POST` | `/api/mistakes/generate-word` | 生成错题本 Word |
| `GET` | `/api/mistakes/download/{fn}` | 下载导出文件 |

## 架构设计

### Skills 技能架构

所有 AI 能力封装为独立的 Skill 模块，继承自 `BaseSkill`:

```
BaseSkill (抽象基类)
├── KnowledgeRetrievalSkill   # 向量检索
├── KnowledgeGraphSkill       # 图谱查询
├── AnswerGenerationSkill     # 标准 RAG 回答
├── AgenticRAGSkill           # 多步推理 RAG
├── SmartAnswerSkill          # 智能路由 (标准/Agentic 自动选择)
├── QuestionLocationSkill     # 习题定位
├── QuizGenerationSkill       # AI 出题
└── DocxGenerationSkill       # Word 文档生成
```

### 初始化策略

- **启动时加载**: Embedding 模型、ChromaDB 连接、知识图谱、非 LLM 技能
- **懒加载**: LLM 实例及依赖 LLM 的技能（首次请求时初始化）

### RAG 流程

```
用户提问 → SmartAnswerSkill 复杂度判断
  ├── 复杂问题 → AgenticRAGSkill (多步推理 + 工具调用)
  │                 ↓ 失败时回退
  └── 简单问题 → AnswerGenerationSkill (标准 RAG)
```

## 配置说明

`backend/config.yaml` 主要配置项:

```yaml
llm:
  provider: "ollama"          # ollama 或 openai
  openai:
    model: "gpt-4"
    api_key: ${OPENAI_API_KEY}
  ollama:
    model: "deepseek-r1:8b"
    base_url: "http://localhost:11434"

embedding:
  model_name: "BAAI/bge-large-zh-v1.5"
  device: "auto"              # auto / cpu / cuda / mps

vector_db:
  collection_name: "408_knowledge"

logging:
  level: "INFO"
```

Embedding 模型首次加载时自动从 HuggingFace 下载。国内环境可设置镜像:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 数据流

```
PDF 教材 → pdf_processor.py → chunks JSON → ingest_chunks.py → ChromaDB
                                           → build_graph.py  → knowledge_graph.json
```

四科教材对应的 subject 代码: `ds`(数据结构), `os`(操作系统), `co`(组成原理), `cn`(计算机网络)

## 开发指南

```bash
# 后端开发 (热重载)
cd backend && uv run uvicorn app.main:app --reload --port 8000

# 前端开发 (热重载，自动代理 /api 到后端)
cd frontend && npm run dev

# 前端构建
cd frontend && npm run build
```

## 许可证

MIT
