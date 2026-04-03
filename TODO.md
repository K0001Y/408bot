# 408 考研辅助 Agent - 待处理清单

> 最后更新: 2026-04-03

---

## 优先级说明

- **P0 - 阻塞性问题**: 影响核心功能运行，需立即处理
- **P1 - 重要功能**: 影响用户体验或系统稳定性
- **P2 - 优化改进**: 提升性能、代码质量、开发体验
- **P3 - 未来规划**: 新功能、扩展性、部署相关

---

## P0 - 阻塞性问题

### 1. Ollama 运行环境修复
- **现象**: Ollama 健康检查通过，但推理时报错 `fork/exec ollama: no such file or directory`
- **原因**: Ollama runner 二进制文件缺失（系统环境问题）
- **解决方案**: 重新安装或重启 Ollama 应用
- **影响范围**: 所有 LLM 相关功能（知识问答、练习生成、试卷分析）

### 2. Agentic RAG 与 ChatOllama 不兼容
- **现象**: `create_react_agent` 调用 `bind_tools()` 时 ChatOllama 不支持
- **原因**: `langchain_community.chat_models.ChatOllama` 是旧版实现，不支持工具绑定
- **解决方案**:
  ```bash
  # 安装新版 langchain-ollama
  uv add langchain-ollama
  ```
  然后将 `llm_factory.py` 中的导入改为:
  ```python
  from langchain_ollama import ChatOllama
  ```
- **影响范围**: Agentic RAG 路由（复杂问题的多步推理）

---

## P1 - 重要功能

### 3. LangChain 依赖包升级
- [ ] 添加 `langchain-ollama` 到 `pyproject.toml`
- [ ] 添加 `langgraph>=0.2.0` 到 `pyproject.toml`（Agentic RAG 依赖）
- [ ] 将 `langchain-community` 中的 `ChatOllama` 迁移到 `langchain-ollama`
- [ ] 将 `langchain-community` 中的 `HuggingFaceEmbeddings` 迁移到 `langchain-huggingface`
  ```bash
  uv add langchain-ollama langchain-huggingface langgraph
  ```

### 4. OCR 功能实现
- **当前状态**: 试卷上传端点仅保存文件，未实现 OCR 文字识别
- **待实现**: 
  - [ ] 集成 OCR 引擎（推荐 PaddleOCR 或 Tesseract）
  - [ ] 图片预处理（去噪、二值化、倾斜校正）
  - [ ] 数学公式识别（LaTeX 输出）
  - [ ] 解析识别结果并传入分析流程

### 5. 错题本数据持久化验证
- [ ] 验证 mistakes.db SQLite 数据库在并发写入下的稳定性
- [ ] 添加数据库迁移机制（版本管理）
- [ ] 完善错题的编辑（更新）功能

### 6. 前端错误处理完善
- [ ] 统一网络错误提示（断网、超时、服务不可用）
- [ ] 添加请求重试机制
- [ ] 长时间 LLM 请求的加载状态优化（流式输出或进度提示）

---

## P2 - 优化改进

### 7. 前端构建优化
- **当前问题**: JS bundle 651KB，Vite 警告超过 500KB 限制
- [ ] 实现路由级代码分割（React.lazy + Suspense）
- [ ] Cytoscape.js 动态导入（仅图谱页面加载）
- [ ] react-markdown 动态导入

### 8. 测试覆盖
- [ ] 后端单元测试（pytest）
  - [ ] Skills 各技能模块测试
  - [ ] API 端点集成测试
  - [ ] 嵌入向量编码测试
  - [ ] 错误处理链路测试
- [ ] 前端组件测试（Vitest + Testing Library）
  - [ ] 页面组件渲染测试
  - [ ] API 调用 mock 测试
  - [ ] 用户交互测试

### 9. 日志与监控
- [ ] 结构化日志输出（JSON 格式可选）
- [ ] 请求耗时统计中间件
- [ ] LLM 调用成本统计（token 用量追踪）
- [ ] ChromaDB 查询性能指标

### 10. 知识图谱增强
- [ ] 支持图谱数据增量更新（不需每次全量重建）
- [ ] 图谱节点点击后关联知识检索
- [ ] 图谱导出（PNG/SVG）

### 11. 用户体验优化
- [ ] LLM 回答流式输出（SSE）
- [ ] 暗色/亮色主题切换
- [ ] 移动端响应式适配
- [ ] 键盘快捷键支持
- [ ] 对话历史记录持久化

---

## P3 - 未来规划

### 12. 生产部署
- [ ] Docker Compose 编排（前端 + 后端 + ChromaDB）
- [ ] Nginx 反向代理配置
- [ ] 环境变量管理（.env.production）
- [ ] HTTPS 证书配置
- [ ] 健康检查端点完善

### 13. 数据管道增强
- [ ] 支持更多数据源格式（PPT、Markdown、网页）
- [ ] 增量数据入库（检测新增/修改的 chunks）
- [ ] 数据版本管理

### 14. 多用户支持
- [ ] 用户认证（JWT）
- [ ] 错题本用户隔离
- [ ] 学习进度追踪
- [ ] 个人化推荐

### 15. AI 能力增强
- [ ] 支持 Claude API 作为 LLM 提供者
- [ ] 多模型对比回答
- [ ] RAG 检索质量评估（RAGAS 指标）
- [ ] 自动化知识图谱构建（LLM 抽取实体关系）

---

## 已完成

- [x] 后端架构搭建（FastAPI + 中间件 + 异常处理 + 日志）
- [x] 配置系统（YAML + 环境变量 + Pydantic Settings）
- [x] 数据入库脚本（PDF 处理 → Chunks → ChromaDB）
- [x] 知识图谱构建脚本
- [x] Embedding 模块（BAAI/bge-large-zh-v1.5 + ChromaDB 协议适配）
- [x] Skills 架构（BaseSkill + 9 个技能模块）
- [x] 全部 5 个 API 模块实现（knowledge/graph/practice/exam/mistakes）
- [x] LLM 工厂（OpenAI / Ollama 双模式支持）
- [x] 错题本 SQLite 存储 + Word 导出
- [x] 前端完整实现（5 个功能页面 + 设计系统）
- [x] 知识图谱可视化（Cytoscape.js）
- [x] 前端构建验证通过
