# 408 考研辅助 Agent - 启动指南

## 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.12+ | 后端运行环境 |
| Node.js | 18+ | 前端构建与开发 |
| [uv](https://docs.astral.sh/uv/) | 最新版 | Python 包管理 |
| Ollama (可选) | 最新版 | 本地 LLM 推理 |

## 一、后端安装与启动

### 1. 安装 Python 依赖

```bash
cd backend
uv sync
```

### 2. 安装 PyTorch

项目使用 `sentence-transformers` 进行文本向量化，依赖 PyTorch。

**CPU 版本**（推荐，体积更小）：

```bash
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

> 若 PyPI 下载缓慢，可追加清华镜像：`-i https://pypi.tuna.tsinghua.edu.cn/simple`

**CUDA 版本**（有 NVIDIA 显卡时使用）：

```bash
# 以 CUDA 12.4 为例
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### 3. 下载 Embedding 模型

首次运行会自动从 HuggingFace 下载 `BAAI/bge-large-zh-v1.5` 模型（约 1.3GB）。

**国内环境加速**：

```bash
# 方式一：使用 HuggingFace 镜像（推荐）
set HF_ENDPOINT=https://hf-mirror.com    # Windows CMD
# export HF_ENDPOINT=https://hf-mirror.com  # Linux/Mac

# 方式二：后续启动时使用离线模式（模型已缓存后）
set HF_HUB_OFFLINE=1
```

### 4. 数据入库

首次运行或数据更新后，需将 `processed/` 目录下的 chunks JSON 导入向量数据库：

```bash
cd backend

# 设置镜像（首次下载模型时需要）
set HF_ENDPOINT=https://hf-mirror.com

# 导入 chunks 到 ChromaDB
uv run python scripts/ingest_chunks.py

# 构建知识图谱（如已有 knowledge_graph.json 可跳过）
uv run python scripts/build_graph.py
```

入库完成后会在 `backend/data/vector_db/` 生成 ChromaDB 持久化文件。

### 5. 配置 LLM (可选)

编辑 `backend/config.yaml`，选择 LLM 提供者：

**Ollama（本地模型）**：
```yaml
llm:
  provider: "ollama"
  ollama:
    model: "deepseek-r1:8b"
    base_url: "http://localhost:11434"
```

需提前安装 Ollama 并拉取模型：
```bash
ollama pull deepseek-r1:8b
ollama serve
```

**OpenAI API**：
```yaml
llm:
  provider: "openai"
  openai:
    model: "gpt-4"
    api_key: ${OPENAI_API_KEY}
```

```bash
set OPENAI_API_KEY=sk-xxx
```

> 不配置 LLM 时，知识检索、图谱浏览、错题本等基础功能仍可正常使用，仅 RAG 问答和 AI 出题不可用。

### 6. 启动后端

```bash
cd backend

# 设置离线模式（模型已缓存后推荐）
set HF_HUB_OFFLINE=1

# 启动服务（端口 8000）
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

开发模式（热重载）：
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后可访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health

## 二、前端安装与启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（端口 5173，自动代理 /api 到后端）
npm run dev
```

浏览器访问 http://localhost:5173

### 生产构建

```bash
npm run build
```

构建产物在 `frontend/dist/` 目录。

## 三、启动顺序速查

```
1. cd backend && set HF_HUB_OFFLINE=1 && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
2. cd frontend && npm run dev
3. 浏览器打开 http://localhost:5173
```

## 四、功能可用性

| 功能 | 依赖 | 状态 |
|------|------|------|
| 知识检索 | Embedding + ChromaDB | 数据入库后可用 |
| 知识图谱浏览 | knowledge_graph.json | 图谱构建后可用 |
| Chunk 详情 | ChromaDB | 数据入库后可用 |
| 错题本 CRUD | SQLite | 始终可用 |
| 错题本导出 Word | python-docx | 始终可用 |
| RAG 智能问答 | LLM (Ollama/OpenAI) | 需配置 LLM |
| AI 生成练习题 | LLM (Ollama/OpenAI) | 需配置 LLM |
| 试卷分析 | LLM + OCR | 需配置 LLM |

## 五、常见问题

### Q: 启动后端时卡在 Embedding 模型加载

Embedding 模型首次加载需从 HuggingFace 下载，国内可能超时。解决方案：

```bash
# 设置镜像
set HF_ENDPOINT=https://hf-mirror.com
# 重新启动
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

模型下载完成后（缓存在 `~/.cache/huggingface/`），后续启动建议设置 `HF_HUB_OFFLINE=1` 跳过网络检查。

### Q: Knowledge Search 返回 500 / 向量检索失败

检查是否已运行数据入库脚本 `scripts/ingest_chunks.py`。

### Q: Ollama 服务不可用的警告

这是正常提示，不影响基础功能。如需 RAG 问答，请启动 Ollama：
```bash
ollama serve
```

### Q: PyTorch 安装失败 / 找不到 torch

确保通过 `--index-url` 指定 PyTorch 官方源安装，不要直接 `pip install torch`：
```bash
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Q: scikit-learn 导入报错

如遇 `ModuleNotFoundError: No module named 'sklearn.utils'`，强制重装：
```bash
uv pip install --force-reinstall scikit-learn -i https://pypi.tuna.tsinghua.edu.cn/simple
```
