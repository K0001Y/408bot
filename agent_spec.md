# 408 考研辅助 Agent 技术规格文档

## 1. 项目概述

### 1.1 项目目标
构建一个基于 RAG 技术的 408 考研辅助 Agent，严格基于王道教材内容提供知识问答、习题练习、真题解析和错题整理功能。

### 1.2 核心功能
1. **知识库问答**：基于教材内容的精准知识检索与问答
2. **知识图谱**：可视化展示知识点关联关系
3. **练习室**：教材习题 + AI 生成习题
4. **真题坊**：真题上传与解析
5. **错题本**：错题收录、管理与 Word 导出

### 1.3 技术栈
- **前端**：React + TypeScript + Tailwind CSS
- **后端**：Python FastAPI
- **Agent 框架**：LangChain（用于知识问答 RAG 流程）
- **向量数据库**：ChromaDB
- **LLM**：OpenAI API / Claude API
- **知识图谱**：D3.js / Cytoscape.js
- **文档生成**：python-docx

### 1.4 Skills 架构

Agent 通过灵活调用 Skills 执行具体任务，每个 Skill 是一个独立的功能模块。

**Skill 列表**：

| Skill 名称 | 功能 | 调用场景 |
|-----------|------|---------|
| `KnowledgeRetrievalSkill` | 从向量数据库检索相关知识 | 知识库搜索 |
| `KnowledgeGraphSkill` | 知识图谱查询与节点关联分析 | 知识图谱可视化 |
| `AnswerGenerationSkill` | 基于检索结果生成回答 | 知识问答 |
| `QuestionLocationSkill` | 根据页码/章节/题号定位题目 | 错题收录 |
| `DocxGenerationSkill` | 生成 Word 格式错题本 | 错题本导出 |
| `OCRSkill` | 识别真题 PDF 内容 | 真题上传 |
| `QuizGenerationSkill` | 基于知识点生成习题 | 练习室 |

**Skill 调用方式**：
```python
# Agent 根据任务类型动态选择 Skill
class Agent:
    def __init__(self):
        self.skills = {
            "knowledge_retrieval": KnowledgeRetrievalSkill(),
            "knowledge_graph": KnowledgeGraphSkill(),
            "answer_generation": AnswerGenerationSkill(),
            "question_location": QuestionLocationSkill(),
            "docx_generation": DocxGenerationSkill(),
            "ocr": OCRSkill(),
            "quiz_generation": QuizGenerationSkill(),
        }
    
    def execute(self, task_type: str, params: dict):
        """根据任务类型调用对应 Skill"""
        skill = self.skills.get(task_type)
        if not skill:
            raise ValueError(f"Unknown task type: {task_type}")
        return skill.execute(params)
```

---

## 2. 功能规格

### 2.1 知识库模块 (/knowledge)

#### 2.1.1 搜索功能

**输入**：
- 搜索框：支持自然语言查询
- 筛选器：
  - 科目：数据结构 / 操作系统 / 计算机组成原理 / 计算机网络
  - 章节：动态加载对应科目的章节列表
  - 内容类型：全部 / 概念 / 代码 / 表格 / 习题 / 总结

**输出**：
- 结果列表展示：
  ```
  [3.2.10 本节小结] 虚拟内存技术允许进程部分装入内存即可运行...
  [3.2.4 页面置换算法] 常见的页面置换算法包括 OPT、FIFO、LRU...
  ```
- 点击列表项后展开详细内容（完整概念解释、代码、表格）

**交互流程**：
```
用户输入查询 → RAG 检索 → 返回 Top-K 结果列表 → 用户点击 → 展示详细内容
```

#### 2.1.2 知识图谱页面 (/knowledge/graph)

**功能**：
- 独立的知识图谱可视化浏览页面
- 支持搜索定位节点
- 展示节点的两层关联关系

**图谱数据结构**：
```json
{
  "nodes": [
    {
      "id": "虚拟内存",
      "type": "concept",
      "chapter": "3.2",
      "chunk_id": "os_3.2.1"
    },
    {
      "id": "页表",
      "type": "concept",
      "chapter": "3.2",
      "chunk_id": "os_3.2.2"
    },
    {
      "id": "LRU算法",
      "type": "algorithm",
      "chapter": "3.2",
      "chunk_id": "os_3.2.4"
    }
  ],
  "edges": [
    {
      "source": "虚拟内存",
      "target": "页表",
      "relation": "依赖",
      "weight": 1.0
    },
    {
      "source": "虚拟内存",
      "target": "LRU算法",
      "relation": "相关",
      "weight": 0.7
    }
  ]
}
```

**节点类型**：
| 类型 | 说明 | 颜色 |
|------|------|------|
| concept | 概念 | 蓝色 |
| algorithm | 算法 | 绿色 |
| chapter | 章节 | 灰色 |

**边类型**：
| 关系 | 说明 |
|------|------|
| 属于 | 算法/概念 → 章节 |
| 依赖 | 概念A → 概念B（先修关系）|
| 相关 | 概念A ↔ 概念B（关联关系）|

**自动提取规则**：
- **属于关系**：从 chunk 的 chapter/subsection 字段提取
- **依赖关系**：通过文本分析提取（如"要理解 X，需要先了解 Y"）
- **相关关系**：通过共现分析提取（同一章节内频繁共现的概念）

**展示规则**：
- 默认展示所有节点
- 搜索后高亮目标节点及其两层关联节点
- 其他节点淡化显示
- 支持节点拖拽、画布缩放

---

### 2.2 练习室模块 (/practice)

#### 2.2.1 教材习题

**功能**：
- 按科目/章节浏览教材原题
- 展示题目 + 答案解析（可折叠）

**数据来源**：
- 预处理阶段标记的 `content_type: exercise` 的 chunks

#### 2.2.2 生成习题

**功能**：
- 选择知识点，生成练习题
- 标注 `【AI】`

**Prompt 模板**：
```
基于以下知识点生成一道选择题：
知识点：{concept}
教材内容：{context}

要求：
1. 题目难度与考研真题相当
2. 提供 4 个选项
3. 给出正确答案和详细解析
4. 在开头标注【AI】
```

**存储**：
- 生成的习题不存入知识库
- 仅临时展示，可收藏到错题本

---

### 2.3 真题坊模块 (/exam)

#### 2.3.1 真题上传

**功能**：
- 上传真题 PDF 文件
- OCR 识别题目内容
- 手动校正识别结果

**技术方案**：
- 使用 PaddleOCR 识别 PDF
- 支持图片裁剪和区域选择
- 识别结果可编辑

#### 2.3.2 真题解析

**功能**：
- 基于知识库检索相关知识点
- 给出解题思路和答案

---

### 2.4 错题本模块 (/mistakes) 【核心功能】

#### 2.4.1 错题收录

**输入格式**：
```
单行输入：页面 章节 题号1 题号2 ...

示例：
156 3.4 5 6 7
```

**解析规则**：
- 第一个数字：页面号（起始页）
- 第二个字符串：章节号（如 3.4）
- 后续数字：题号列表（空格分隔）

**存储结构**：
```json
{
  "mistake_id": "mistake_001",
  "subject_code": "os",
  "page": 156,
  "chapter": "3.4",
  "question_number": 5,
  "question_text": "题目原文...",
  "answer_text": "正确答案...",
  "explanation": "解析...",
  "added_at": "2025-03-24T10:00:00",
  "selected": false
}
```

#### 2.4.2 错题列表

**功能**：
- 展示所有收录的错题
- 支持按科目/章节筛选
- 每题前面有复选框
- 支持全选/取消全选

**列表项展示**：
```
[ ] 【3.4.5】（第156页）虚拟内存的主要特征包括...
[ ] 【3.4.6】（第158页）页面置换算法的目的是...
```

#### 2.4.3 生成 Word

**触发条件**：
- 用户勾选错题后，点击"生成 Word"按钮

**Word 文档格式**：

**前半部分 - 题目**：
```
408 考研错题本

题目部分
==================================================

【3.4.5】（第156页）
虚拟内存的主要特征包括哪些？
A. ...
B. ...
C. ...
D. ...

【3.4.6】（第158页）
页面置换算法的目的是什么？
A. ...
B. ...
C. ...
D. ...
```

**后半部分 - 答案与解析**：
```

答案与解析部分
==================================================

【3.4.5】（第156页）
正确答案：B
解析：虚拟内存的主要特征包括...

【3.4.6】（第158页）
正确答案：C
解析：页面置换算法的目的是...
```

**技术要求**：
- 使用 `python-docx` 生成 Word 文档
- 题目和答案分页显示
- 支持下载 docx 文件

---

## 3. 数据模型

### 3.1 Chunk 模型

```typescript
interface Chunk {
  chunk_id: string;           // 如 "os_3.2.10"
  subject_code: string;       // "ds" | "os" | "co" | "cn"
  chapter_number: string;     // "3"
  chapter_title: string;      // "内存管理"
  section_number: string;     // "3.2"
  section_title: string;      // "虚拟内存"
  subsection: string;         // "3.2.10"
  subsection_title: string;   // "本节小结"
  page_start: number;
  page_end: number;
  content: string;
  char_count: number;
  token_count: number;
  content_type: "concept" | "code" | "table" | "exercise" | "answer" | "summary";
  has_code: boolean;
  has_table: boolean;
  has_image_ref: boolean;
  has_formula: boolean;
  is_partial?: boolean;
  part_index?: number;
  total_parts?: number;
}
```

### 3.2 错题模型

```typescript
interface Mistake {
  mistake_id: string;
  subject_code: string;
  subject_name: string;
  page: number;
  chapter: string;
  question_number: number;
  question_text: string;
  answer_text: string;
  explanation: string;
  added_at: string;
  selected: boolean;
}
```

### 3.3 知识图谱模型

```typescript
interface GraphNode {
  id: string;
  type: "concept" | "algorithm" | "chapter";
  label: string;
  chapter?: string;
  chunk_id?: string;
  x?: number;
  y?: number;
}

interface GraphEdge {
  source: string;
  target: string;
  relation: "属于" | "依赖" | "相关";
  weight: number;
}

interface KnowledgeGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
```

---

## 4. API 接口设计

### 4.1 知识库接口

#### POST /api/knowledge/search
**请求**：
```json
{
  "query": "时间复杂度相关的算法",
  "subject": "ds",
  "chapter": null,
  "content_type": null,
  "top_k": 10
}
```

**响应**：
```json
{
  "results": [
    {
      "chunk_id": "ds_2.3.4",
      "subsection": "2.3.4",
      "subsection_title": "时间复杂度分析",
      "preview": "时间复杂度是衡量算法效率的重要指标...",
      "score": 0.92
    }
  ]
}
```

#### GET /api/knowledge/chunk/{chunk_id}
**响应**：
```json
{
  "chunk_id": "ds_2.3.4",
  "content": "完整内容...",
  "metadata": { ... }
}
```

### 4.2 知识图谱接口

#### GET /api/graph
**响应**：
```json
{
  "nodes": [...],
  "edges": [...]
}
```

#### GET /api/graph/node/{node_id}
**响应**：节点详情及其两层关联子图

### 4.3 错题本接口

#### POST /api/mistakes
**请求**：
```json
{
  "input": "156 3.4 5 6 7",
  "subject_code": "os"
}
```

**处理逻辑**：
1. 解析输入字符串
2. 根据 page 和 chapter 定位题目
3. 提取题目原文、答案、解析
4. 存储到错题数据库

**响应**：
```json
{
  "added": 3,
  "mistakes": [
    { "mistake_id": "...", "page": 156, "chapter": "3.4", "question_number": 5 }
  ]
}
```

#### GET /api/mistakes
**查询参数**：`subject`, `chapter`

**响应**：错题列表

#### POST /api/mistakes/generate-word
**请求**：
```json
{
  "mistake_ids": ["mistake_001", "mistake_002", ...]
}
```

**响应**：Word 文件下载链接

---

## 5. RAG 技术方案

### 5.1 向量索引

**Embedding 模型**：
- 推荐使用 `BAAI/bge-large-zh-v1.5` 或 OpenAI `text-embedding-3-small`

**索引结构**：
```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.create_collection(
    name="408_knowledge",
    metadata={"hnsw:space": "cosine"}
)

# 添加文档
collection.add(
    ids=[chunk["chunk_id"] for chunk in chunks],
    documents=[chunk["content"] for chunk in chunks],
    metadatas=[{
        "subject_code": chunk["subject_code"],
        "chapter": chunk["chapter_number"],
        "section": chunk["section_number"],
        "subsection": chunk["subsection"],
        "content_type": chunk["content_type"],
        "page_start": chunk["page_start"],
        "page_end": chunk["page_end"]
    } for chunk in chunks]
)
```

### 5.2 检索策略

**混合检索**：
1. **向量检索**：语义相似度匹配
2. **关键词过滤**：metadata 字段过滤（subject/chapter/content_type）
3. **重排序**：使用 Cross-Encoder 对初筛结果重排序

**检索流程**：
```python
def search_knowledge(query, subject=None, chapter=None, content_type=None, top_k=10):
    # 1. 构建过滤条件
    where_clause = {}
    if subject:
        where_clause["subject_code"] = subject
    if chapter:
        where_clause["chapter"] = chapter
    if content_type:
        where_clause["content_type"] = content_type
    
    # 2. 向量检索
    results = collection.query(
        query_texts=[query],
        where=where_clause if where_clause else None,
        n_results=top_k * 2  # 初筛更多结果用于重排序
    )
    
    # 3. 重排序（可选）
    # reranked = rerank_results(query, results)
    
    return results[:top_k]
```

### 5.3 回答生成（使用 LangChain）

**技术选型**：使用 **LangChain** 构建 RAG Chain

**选型理由**：
- 知识问答是线性流程（检索 → 组装 Prompt → 生成），无需复杂状态管理
- LangChain 生态成熟，与 ChromaDB、OpenAI 集成完善
- 代码简洁，易于维护和调试

**LangChain 实现**：
```python
from langchain import OpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

class AnswerGenerationSkill:
    """
    Skill: 基于检索结果生成回答
    使用 LangChain RetrievalQA Chain
    """
    
    def __init__(self):
        # 初始化 Embedding
        self.embeddings = OpenAIEmbeddings()
        
        # 加载向量数据库
        self.vectordb = Chroma(
            persist_directory="./data/vector_db",
            embedding_function=self.embeddings
        )
        
        # 自定义 Prompt 模板
        self.prompt_template = PromptTemplate(
            template="""
你是 408 考研辅导助手，严格基于以下教材内容回答问题。

用户问题：{question}

相关教材内容：
{context}

要求：
1. 只基于提供的教材内容回答，不要添加外部知识
2. 如果教材内容不足以回答问题，明确说明
3. 如涉及代码，保留原格式
4. 如涉及多个知识点，分点说明

回答：
""",
            input_variables=["context", "question"]
        )
        
        # 构建 LangChain RAG Chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=OpenAI(temperature=0, model_name="gpt-4"),
            chain_type="stuff",  # 简单拼接上下文
            retriever=self.vectordb.as_retriever(
                search_kwargs={"k": 10}  # 检索 Top-10
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": self.prompt_template}
        )
    
    def execute(self, params: dict) -> dict:
        """
        执行回答生成
        
        Args:
            params: {"query": "用户问题"}
        
        Returns:
            {"answer": "回答", "sources": [...]}
        """
        query = params.get("query")
        
        # 使用 LangChain 生成回答
        result = self.qa_chain({"query": query})
        
        return {
            "answer": result["result"],
            "sources": [
                {
                    "chunk_id": doc.metadata.get("chunk_id"),
                    "subsection": doc.metadata.get("subsection"),
                    "content": doc.page_content[:300]
                }
                for doc in result["source_documents"]
            ]
        }
```

**Prompt 模板**：
```
你是 408 考研辅导助手，严格基于以下教材内容回答问题。

用户问题：{question}

相关教材内容：
{context}

要求：
1. 只基于提供的教材内容回答，不要添加外部知识
2. 如果教材内容不足以回答问题，明确说明
3. 如涉及代码，保留原格式
4. 如涉及多个知识点，分点说明

回答：
```

---

## 6. 知识图谱构建方案

### 6.1 节点提取

**概念节点**：
- 从 chunk 的 `subsection_title` 提取
- 从内容中的关键术语提取（使用 TF-IDF 或 KeyBERT）

**算法节点**：
- 识别标题中包含"算法"的 subsection
- 标记 `type: algorithm`

### 6.2 边关系提取

**属于关系**（自动）：
```python
# 概念/算法 属于 章节
edges.append({
    "source": chunk["subsection_title"],
    "target": f"第{chunk['chapter_number']}章 {chunk['chapter_title']}",
    "relation": "属于"
})
```

**依赖关系**（自动提取）：
```python
# 通过文本模式匹配提取
dependency_patterns = [
    r"要理解(.+?)，需要先了解(.+?)",
    r"(.+?)的前提是(.+?)",
    r"在学习(.+?)之前，必须先掌握(.+?)",
]

for pattern in dependency_patterns:
    matches = re.findall(pattern, content)
    for match in matches:
        edges.append({
            "source": match[0].strip(),
            "target": match[1].strip(),
            "relation": "依赖"
        })
```

**相关关系**（自动提取）：
```python
# 基于共现分析
# 同一章节内频繁共现的概念建立相关关系
from collections import defaultdict

cooccurrence = defaultdict(int)
for chunk in chunks:
    concepts = extract_concepts(chunk["content"])
    for i, c1 in enumerate(concepts):
        for c2 in concepts[i+1:]:
            pair = tuple(sorted([c1, c2]))
            cooccurrence[pair] += 1

# 建立相关关系（共现次数 > 阈值）
for (c1, c2), count in cooccurrence.items():
    if count >= threshold:
        edges.append({
            "source": c1,
            "target": c2,
            "relation": "相关",
            "weight": min(count / 10, 1.0)  # 归一化权重
        })
```

### 6.3 图谱存储

**存储方式**：
- 节点和边存储在 JSON 文件中
- 或存储在图数据库（如 Neo4j）中

---

## 7. 前端页面设计

### 7.1 布局结构

**整体布局**：
```
┌─────────────────────────────────────────────────────────┐
│  Logo    知识库    练习室    真题坊    错题本     [用户]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                      页面内容                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 7.2 知识库页面 (/knowledge)

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│  [搜索框                                    ] [搜索]    │
├──────────────┬──────────────────────────────────────────┤
│  筛选器       │  搜索结果列表                             │
│              │                                          │
│  科目：       │  [3.2.10 本节小结] 虚拟内存技术...        │
│  ○ 全部      │  [3.2.4 页面置换算法] 常见的页面置换...    │
│  ○ 数据结构   │  [3.2.1 虚拟内存基本概念] 虚拟内存是指...  │
│  ○ 操作系统   │                                          │
│  ○ ...       │                                          │
│              │                                          │
│  章节：       │                                          │
│  □ 3.1       │                                          │
│  □ 3.2       │                                          │
│  □ 3.3       │                                          │
│              │                                          │
│  内容类型：    │                                          │
│  □ 概念      │                                          │
│  □ 代码      │                                          │
│  □ 习题      │                                          │
│              │                                          │
├──────────────┴──────────────────────────────────────────┤
│  [知识图谱] 标签页                                       │
└─────────────────────────────────────────────────────────┘
```

**详情弹窗**：
- 点击搜索结果后弹出详情面板
- 展示完整内容
- 包含"在图谱中查看"按钮

### 7.3 知识图谱页面 (/knowledge/graph)

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│  [搜索节点...                    ] [重置视图]          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                    图谱可视化区域                        │
│                                                         │
│  ┌─────┐         ┌─────┐                               │
│  │虚拟内存│────────│ 页表 │                               │
│  └──┬──┘         └─────┘                               │
│     │                                                   │
│     │         ┌─────┐                                   │
│     └────────→│LRU算法│                                  │
│               └─────┘                                   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  图例：● 概念  ● 算法  ● 章节    线：依赖  线：相关      │
└─────────────────────────────────────────────────────────┘
```

**交互**：
- 节点可拖拽
- 滚轮缩放
- 点击节点高亮其两层关联
- 双击节点跳转到知识详情

### 7.4 错题本页面 (/mistakes)

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│  添加错题：                                              │
│  [页面 章节 题号...                    ] [添加]         │
├─────────────────────────────────────────────────────────┤
│  筛选：科目 [全部 ▼] 章节 [全部 ▼]    [全选] [生成Word]  │
├─────────────────────────────────────────────────────────┤
│  [ ] 【3.4.5】（第156页）虚拟内存的主要特征包括...       │
│  [ ] 【3.4.6】（第158页）页面置换算法的目的是...         │
│  [ ] 【3.5.2】（第160页）地址翻译的过程是...             │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 8. 后端架构

### 8.1 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── api/
│   │   ├── __init__.py
│   │   ├── knowledge.py     # 知识库接口
│   │   ├── graph.py         # 知识图谱接口
│   │   ├── practice.py      # 练习室接口
│   │   ├── exam.py          # 真题坊接口
│   │   └── mistakes.py      # 错题本接口
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rag_service.py   # RAG 服务
│   │   ├── graph_service.py # 知识图谱服务
│   │   ├── ocr_service.py   # OCR 服务
│   │   └── docx_service.py  # Word 生成服务
│   ├── models/
│   │   ├── __init__.py
│   │   ├── chunk.py         # Chunk 模型
│   │   ├── mistake.py       # 错题模型
│   │   └── graph.py         # 图谱模型
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── data/
│   ├── chunks/              # Chunk JSON 文件
│   ├── vector_db/           # ChromaDB 数据
│   ├── graph/               # 知识图谱数据
│   └── mistakes.db          # SQLite 错题数据库
├── requirements.txt
└── Dockerfile
```

### 8.2 核心服务实现

#### Skills 实现

所有核心功能封装为 Skills，Agent 根据任务类型灵活调用。

##### KnowledgeRetrievalSkill

```python
# app/skills/knowledge_retrieval_skill.py
from typing import List, Dict
import chromadb

class KnowledgeRetrievalSkill:
    """
    Skill: 从向量数据库检索相关知识
    用于知识库页面的搜索结果列表展示
    """
    
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./data/vector_db")
        self.collection = self.client.get_collection("408_knowledge")
    
    def execute(self, params: dict) -> List[Dict]:
        """
        执行知识检索
        
        Args:
            params: {
                "query": "搜索关键词",
                "subject": "ds/os/co/cn",
                "chapter": "3",
                "content_type": "concept/code/table/exercise",
                "top_k": 10
            }
        
        Returns:
            List[Dict]: 检索结果列表
        """
        query = params.get("query")
        subject = params.get("subject")
        chapter = params.get("chapter")
        content_type = params.get("content_type")
        top_k = params.get("top_k", 10)
        
        # 构建过滤条件
        where_clause = {}
        if subject:
            where_clause["subject_code"] = subject
        if chapter:
            where_clause["chapter"] = chapter
        if content_type:
            where_clause["content_type"] = content_type
        
        # 向量检索
        results = self.collection.query(
            query_texts=[query],
            where=where_clause if where_clause else None,
            n_results=top_k
        )
        
        # 格式化结果
        formatted_results = []
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i]
            formatted_results.append({
                "chunk_id": metadata.get("chunk_id"),
                "subsection": metadata.get("subsection"),
                "subsection_title": metadata.get("subsection_title"),
                "preview": doc[:200] + "...",
                "score": results["distances"][0][i] if "distances" in results else 0.0
            })
        
        return formatted_results
    
    def get_chunk_detail(self, chunk_id: str) -> Dict:
        """获取 chunk 完整内容"""
        results = self.collection.get(
            ids=[chunk_id],
            include=["documents", "metadatas"]
        )
        
        if results["ids"]:
            return {
                "chunk_id": chunk_id,
                "content": results["documents"][0],
                "metadata": results["metadatas"][0]
            }
        return None
```

##### KnowledgeGraphSkill

```python
# app/skills/knowledge_graph_skill.py
import json
from typing import List, Dict

class KnowledgeGraphSkill:
    """
    Skill: 知识图谱查询与节点关联分析
    用于知识图谱可视化页面的数据获取
    """
    
    def __init__(self):
        with open("./data/graph/knowledge_graph.json") as f:
            data = json.load(f)
            self.nodes = {n["id"]: n for n in data["nodes"]}
            self.edges = data["edges"]
    
    def execute(self, params: dict) -> Dict:
        """
        执行图谱查询
        
        Args:
            params: {
                "action": "full_graph" | "node_subgraph",
                "node_id": "节点ID" (当 action=node_subgraph 时),
                "depth": 2 (关联深度)
            }
        
        Returns:
            Dict: {nodes, edges}
        """
        action = params.get("action", "full_graph")
        
        if action == "full_graph":
            return self.get_full_graph()
        elif action == "node_subgraph":
            node_id = params.get("node_id")
            depth = params.get("depth", 2)
            return self.get_node_subgraph(node_id, depth)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    def get_full_graph(self) -> Dict:
        """获取完整图谱"""
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges
        }
    
    def get_node_subgraph(self, node_id: str, depth: int = 2) -> Dict:
        """获取节点的 N 层关联子图"""
        if node_id not in self.nodes:
            return {"nodes": [], "edges": []}
        
        related_nodes = {node_id}
        related_edges = []
        
        current_layer = {node_id}
        for _ in range(depth):
            next_layer = set()
            for edge in self.edges:
                if edge["source"] in current_layer:
                    related_nodes.add(edge["target"])
                    related_edges.append(edge)
                    next_layer.add(edge["target"])
                elif edge["target"] in current_layer:
                    related_nodes.add(edge["source"])
                    related_edges.append(edge)
                    next_layer.add(edge["source"])
            current_layer = next_layer
        
        return {
            "nodes": [self.nodes[nid] for nid in related_nodes],
            "edges": related_edges
        }
```

##### AnswerGenerationSkill

```python
# app/skills/answer_generation_skill.py
from langchain import OpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

class AnswerGenerationSkill:
    """
    Skill: 基于检索结果生成回答
    使用 LangChain RetrievalQA Chain
    """
    
    def __init__(self):
        # 初始化 Embedding
        self.embeddings = OpenAIEmbeddings()
        
        # 加载向量数据库
        self.vectordb = Chroma(
            persist_directory="./data/vector_db",
            embedding_function=self.embeddings
        )
        
        # 自定义 Prompt 模板
        self.prompt_template = PromptTemplate(
            template="""
你是 408 考研辅导助手，严格基于以下教材内容回答问题。

用户问题：{question}

相关教材内容：
{context}

要求：
1. 只基于提供的教材内容回答，不要添加外部知识
2. 如果教材内容不足以回答问题，明确说明
3. 如涉及代码，保留原格式
4. 如涉及多个知识点，分点说明

回答：
""",
            input_variables=["context", "question"]
        )
        
        # 构建 LangChain RAG Chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=OpenAI(temperature=0, model_name="gpt-4"),
            chain_type="stuff",
            retriever=self.vectordb.as_retriever(
                search_kwargs={"k": 10}
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": self.prompt_template}
        )
    
    def execute(self, params: dict) -> dict:
        """
        执行回答生成
        
        Args:
            params: {"query": "用户问题"}
        
        Returns:
            {"answer": "回答", "sources": [...]}
        """
        query = params.get("query")
        
        # 使用 LangChain 生成回答
        result = self.qa_chain({"query": query})
        
        return {
            "answer": result["result"],
            "sources": [
                {
                    "chunk_id": doc.metadata.get("chunk_id"),
                    "subsection": doc.metadata.get("subsection"),
                    "content": doc.page_content[:300]
                }
                for doc in result["source_documents"]
            ]
        }
```

##### QuestionLocationSkill

```python
# app/skills/question_location_skill.py
import re
from typing import Dict, List

class QuestionLocationSkill:
    """
    Skill: 根据页码/章节/题号定位题目
    用于错题收录时提取题目内容
    """
    
    def __init__(self):
        # 加载 chunk 数据
        import json
        self.chunks = {}
        for subject in ["ds", "os", "co", "cn"]:
            try:
                with open(f"./data/chunks/{subject}_chunks.json") as f:
                    chunks = json.load(f)
                    for chunk in chunks:
                        self.chunks[chunk["chunk_id"]] = chunk
            except FileNotFoundError:
                pass
    
    def execute(self, params: dict) -> Dict:
        """
        定位题目并提取内容
        
        Args:
            params: {
                "subject_code": "os",
                "page": 156,
                "chapter": "3.4",
                "question_number": 5
            }
        
        Returns:
            {
                "question_text": "题目原文",
                "answer_text": "正确答案",
                "explanation": "解析"
            }
        """
        subject_code = params.get("subject_code")
        page = params.get("page")
        chapter = params.get("chapter")
        question_number = params.get("question_number")
        
        # 查找包含该题目的 chunk
        # 策略：查找 page_start <= page <= page_end 且 chapter 匹配的 chunk
        target_chunk = None
        for chunk in self.chunks.values():
            if (chunk["subject_code"] == subject_code and
                chunk["page_start"] <= page <= chunk["page_end"] and
                chunk["chapter_number"] == chapter.split(".")[0]):
                target_chunk = chunk
                break
        
        if not target_chunk:
            return {
                "question_text": f"[题目未找到] 第{page}页 {chapter} 第{question_number}题",
                "answer_text": "",
                "explanation": ""
            }
        
        # 从 chunk 内容中提取题目
        # 使用正则匹配题号
        content = target_chunk["content"]
        question_data = self._extract_question_from_content(
            content, question_number
        )
        
        return question_data
    
    def _extract_question_from_content(self, content: str, question_number: int) -> Dict:
        """从 chunk 内容中提取指定题号的题目"""
        # 匹配题号模式（如 "5." 或 "5、" 或 "(5)"）
        patterns = [
            rf"{question_number}[\.、\.]\s*(.+?)(?=\n\s*{question_number + 1}[\.、\.]|$)",
            rf"\({question_number}\)\s*(.+?)(?=\n\s*\({question_number + 1}\)|$)",
            rf"【{question_number}】\s*(.+?)(?=\n\s*【{question_number + 1}】|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                question_text = match.group(1).strip()
                return {
                    "question_text": question_text,
                    "answer_text": "[需手动添加]",
                    "explanation": "[需手动添加]"
                }
        
        # 未找到题目
        return {
            "question_text": f"[题目提取失败] 第{question_number}题",
            "answer_text": "",
            "explanation": ""
        }
```

##### DocxGenerationSkill

```python
# app/skills/docx_generation_skill.py
from typing import List, Dict
from docx import Document
from docx.shared import Pt
from datetime import datetime
import os

class DocxGenerationSkill:
    """
    Skill: 生成 Word 格式错题本
    题目在前，答案解析在后
    """
    
    def execute(self, params: dict) -> str:
        """
        生成 Word 文档
        
        Args:
            params: {
                "mistakes": [
                    {
                        "chapter": "3.4",
                        "question_number": 5,
                        "page": 156,
                        "question_text": "...",
                        "answer_text": "...",
                        "explanation": "..."
                    }
                ]
            }
        
        Returns:
            str: 生成的 Word 文件路径
        """
        mistakes = params.get("mistakes", [])
        
        doc = Document()
        
        # 设置中文字体
        doc.styles['Normal'].font.name = 'SimSun'
        doc.styles['Normal']._element.rPr.rFonts.set(docx.oxml.ns.qn('w:eastAsia'), 'SimSun')
        
        # 标题
        title = doc.add_heading('408 考研错题本', 0)
        title.alignment = 1  # 居中
        
        # 生成日期
        doc.add_paragraph(f'生成日期：{datetime.now().strftime("%Y-%m-%d")}')
        doc.add_paragraph()
        
        # ========== 题目部分 ==========
        doc.add_heading('题目部分', level=1)
        doc.add_paragraph('=' * 50)
        doc.add_paragraph()
        
        for m in mistakes:
            # 题目标题
            p = doc.add_paragraph()
            run = p.add_run(f"【{m['chapter']}.{m['question_number']}】")
            run.bold = True
            run.font.size = Pt(12)
            
            run = p.add_run(f"（第{m['page']}页）")
            run.font.size = Pt(10)
            
            # 题目内容
            doc.add_paragraph(m['question_text'])
            
            # 空行
            doc.add_paragraph()
        
        # 分页
        doc.add_page_break()
        
        # ========== 答案与解析部分 ==========
        doc.add_heading('答案与解析部分', level=1)
        doc.add_paragraph('=' * 50)
        doc.add_paragraph()
        
        for m in mistakes:
            # 题目标题
            p = doc.add_paragraph()
            run = p.add_run(f"【{m['chapter']}.{m['question_number']}】")
            run.bold = True
            
            run = p.add_run(f"（第{m['page']}页）")
            run.font.size = Pt(10)
            
            # 正确答案
            p = doc.add_paragraph()
            run = p.add_run("正确答案：")
            run.bold = True
            p.add_run(m['answer_text'])
            
            # 解析
            p = doc.add_paragraph()
            run = p.add_run("解析：")
            run.bold = True
            p.add_run(m['explanation'])
            
            # 空行
            doc.add_paragraph()
        
        # 保存
        output_dir = "./data/exports"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir,
            f"mistakes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        )
        doc.save(output_path)
        
        return output_path
```

##### OCRSkill

```python
# app/skills/ocr_skill.py
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from PIL import Image
import os

class OCRSkill:
    """
    Skill: 识别真题 PDF 内容
    用于真题上传功能
    """
    
    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
            use_gpu=False,
            show_log=False
        )
    
    def execute(self, params: dict) -> Dict:
        """
        执行 OCR 识别
        
        Args:
            params: {
                "pdf_path": "/path/to/exam.pdf",
                "page_range": [1, 5]  # 可选，识别指定页码范围
            }
        
        Returns:
            {
                "pages": [
                    {"page": 1, "text": "识别结果..."},
                    ...
                ]
            }
        """
        pdf_path = params.get("pdf_path")
        page_range = params.get("page_range")
        
        # PDF 转图片
        if page_range:
            images = convert_from_path(
                pdf_path,
                dpi=300,
                first_page=page_range[0],
                last_page=page_range[1]
            )
        else:
            images = convert_from_path(pdf_path, dpi=300)
        
        # OCR 识别
        results = []
        for i, image in enumerate(images):
            # 临时保存
            temp_path = f"/tmp/ocr_{i}.png"
            image.save(temp_path)
            
            # 识别
            result = self.ocr.ocr(temp_path, cls=True)
            texts = []
            if result[0]:
                for line in result[0]:
                    text, confidence = line[1][0], line[1][1]
                    if confidence > 0.8:
                        texts.append(text)
            
            results.append({
                "page": i + 1,
                "text": "\n".join(texts)
            })
            
            # 清理
            os.remove(temp_path)
        
        return {"pages": results}
```

##### QuizGenerationSkill

```python
# app/skills/quiz_generation_skill.py
from langchain import OpenAI
from langchain.prompts import PromptTemplate

class QuizGenerationSkill:
    """
    Skill: 基于知识点生成习题
    标注 【AI】
    """
    
    def __init__(self):
        self.llm = OpenAI(temperature=0.7)
        
        self.prompt_template = PromptTemplate(
            template="""
基于以下知识点生成一道考研 408 难度的选择题。

知识点：{concept}
教材内容：{context}

要求：
1. 题目难度与考研真题相当
2. 提供 4 个选项（A/B/C/D）
3. 给出正确答案和详细解析
4. 在开头标注 【AI】

输出格式：
【AI】

题目：
[题目内容]

选项：
A. [选项A]
B. [选项B]
C. [选项C]
D. [选项D]

正确答案：[正确选项]

解析：
[详细解析]
""",
            input_variables=["concept", "context"]
        )
    
    def execute(self, params: dict) -> Dict:
        """
        生成习题
        
        Args:
            params: {
                "concept": "虚拟内存",
                "context": "相关教材内容..."
            }
        
        Returns:
            {"question": "生成的题目内容"}
        """
        concept = params.get("concept")
        context = params.get("context", "")
        
        prompt = self.prompt_template.format(
            concept=concept,
            context=context
        )
        
        response = self.llm.predict(prompt)
        
        return {"question": response}
```

#### Agent 主类

```python
# app/agent.py
from typing import Dict, Any

class Agent:
    """
    408 考研辅助 Agent
    根据任务类型灵活调用 Skills
    """
    
    def __init__(self):
        # 初始化所有 Skills
        from app.skills import (
            KnowledgeRetrievalSkill,
            KnowledgeGraphSkill,
            AnswerGenerationSkill,
            QuestionLocationSkill,
            DocxGenerationSkill,
            OCRSkill,
            QuizGenerationSkill
        )
        
        self.skills = {
            "knowledge_retrieval": KnowledgeRetrievalSkill(),
            "knowledge_graph": KnowledgeGraphSkill(),
            "answer_generation": AnswerGenerationSkill(),
            "question_location": QuestionLocationSkill(),
            "docx_generation": DocxGenerationSkill(),
            "ocr": OCRSkill(),
            "quiz_generation": QuizGenerationSkill(),
        }
    
    def execute(self, task_type: str, params: Dict[str, Any]) -> Any:
        """
        根据任务类型调用对应 Skill
        
        Args:
            task_type: Skill 名称
            params: Skill 参数
        
        Returns:
            Skill 执行结果
        """
        skill = self.skills.get(task_type)
        if not skill:
            raise ValueError(f"Unknown task type: {task_type}. "
                           f"Available: {list(self.skills.keys())}")
        
        return skill.execute(params)
```

#### 知识图谱服务

```python
# app/services/graph_service.py
import json
from typing import List, Dict

class GraphService:
    def __init__(self):
        with open("./data/graph/knowledge_graph.json") as f:
            data = json.load(f)
            self.nodes = {n["id"]: n for n in data["nodes"]}
            self.edges = data["edges"]
    
    def get_full_graph(self) -> Dict:
        """获取完整图谱"""
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges
        }
    
    def get_node_subgraph(self, node_id: str, depth: int = 2) -> Dict:
        """获取节点的 N 层关联子图"""
        related_nodes = {node_id}
        related_edges = []
        
        current_layer = {node_id}
        for _ in range(depth):
            next_layer = set()
            for edge in self.edges:
                if edge["source"] in current_layer:
                    related_nodes.add(edge["target"])
                    related_edges.append(edge)
                    next_layer.add(edge["target"])
                elif edge["target"] in current_layer:
                    related_nodes.add(edge["source"])
                    related_edges.append(edge)
                    next_layer.add(edge["source"])
            current_layer = next_layer
        
        return {
            "nodes": [self.nodes[nid] for nid in related_nodes],
            "edges": related_edges
        }
```

#### 错题本服务

```python
# app/services/mistakes_service.py
import sqlite3
import re
from typing import List, Dict
from docx import Document
from docx.shared import Pt

class MistakesService:
    def __init__(self, db_path: str = "./data/mistakes.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mistakes (
                    mistake_id TEXT PRIMARY KEY,
                    subject_code TEXT,
                    page INTEGER,
                    chapter TEXT,
                    question_number INTEGER,
                    question_text TEXT,
                    answer_text TEXT,
                    explanation TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def parse_input(self, input_str: str) -> Dict:
        """解析输入字符串"""
        parts = input_str.strip().split()
        if len(parts) < 3:
            raise ValueError("输入格式错误，应为：页面 章节 题号1 题号2 ...")
        
        return {
            "page": int(parts[0]),
            "chapter": parts[1],
            "question_numbers": [int(n) for n in parts[2:]]
        }
    
    def add_mistakes(
        self,
        subject_code: str,
        page: int,
        chapter: str,
        question_numbers: List[int]
    ) -> List[Dict]:
        """添加错题"""
        mistakes = []
        
        for qn in question_numbers:
            # 从知识库提取题目内容
            question_data = self._extract_question(subject_code, page, chapter, qn)
            
            mistake = {
                "mistake_id": f"{subject_code}_{page}_{chapter}_{qn}",
                "subject_code": subject_code,
                "page": page,
                "chapter": chapter,
                "question_number": qn,
                **question_data
            }
            
            # 存入数据库
            self._save_mistake(mistake)
            mistakes.append(mistake)
        
        return mistakes
    
    def generate_word(self, mistake_ids: List[str]) -> str:
        """生成 Word 文档"""
        mistakes = self._get_mistakes_by_ids(mistake_ids)
        
        doc = Document()
        
        # 标题
        title = doc.add_heading('408 考研错题本', 0)
        
        # 题目部分
        doc.add_heading('题目部分', level=1)
        doc.add_paragraph('=' * 50)
        
        for m in mistakes:
            p = doc.add_paragraph()
            p.add_run(f"【{m['chapter']}.{m['question_number']}】").bold = True
            p.add_run(f"（第{m['page']}页）")
            doc.add_paragraph(m['question_text'])
            doc.add_paragraph()  # 空行
        
        # 分页
        doc.add_page_break()
        
        # 答案部分
        doc.add_heading('答案与解析部分', level=1)
        doc.add_paragraph('=' * 50)
        
        for m in mistakes:
            p = doc.add_paragraph()
            p.add_run(f"【{m['chapter']}.{m['question_number']}】").bold = True
            p.add_run(f"（第{m['page']}页）")
            
            p = doc.add_paragraph()
            p.add_run("正确答案：").bold = True
            p.add_run(m['answer_text'])
            
            p = doc.add_paragraph()
            p.add_run("解析：").bold = True
            p.add_run(m['explanation'])
            
            doc.add_paragraph()  # 空行
        
        # 保存
        output_path = f"./data/mistakes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        doc.save(output_path)
        
        return output_path
```

---

## 9. 部署方案

### 9.1 开发环境

```bash
# 后端
conda create -n 408-agent python=3.10
conda activate 408-agent
pip install -r requirements.txt

# 前端
cd frontend
npm install
npm run dev
```

### 9.2 生产部署

**Docker Compose**：
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

---

## 10. 开发里程碑

| 阶段 | 任务 | 预估时间 |
|------|------|---------|
| Phase 1 | 数据预处理（PDF → Chunks） | 1 周 |
| Phase 2 | 后端 API 开发（知识库 + RAG） | 1 周 |
| Phase 3 | 知识图谱构建与可视化 | 1 周 |
| Phase 4 | 错题本功能开发 | 3 天 |
| Phase 5 | 前端页面开发 | 1 周 |
| Phase 6 | 集成测试与优化 | 3 天 |

**总计**：约 4-5 周

---

## 11. 附录

### 11.1 错误码定义

| 错误码 | 说明 |
|--------|------|
| 4001 | 输入格式错误 |
| 4002 | 题目不存在 |
| 4003 | 文件格式不支持 |
| 5001 | OCR 识别失败 |
| 5002 | 向量检索失败 |

### 11.2 配置文件示例

```yaml
# config.yaml
app:
  name: "408考研辅助Agent"
  version: "1.0.0"

llm:
  provider: "openai"  # 或 "anthropic"
  model: "gpt-4"
  api_key: ${OPENAI_API_KEY}

vector_db:
  type: "chroma"
  path: "./data/vector_db"

embedding:
  model: "BAAI/bge-large-zh-v1.5"
  # 或 openai: "text-embedding-3-small"

knowledge_graph:
  auto_extract: true
  max_depth: 2
```

---

*文档版本: 1.0*
*创建日期: 2025-03-24*
*状态: 编码就绪*
