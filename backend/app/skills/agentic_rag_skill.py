"""
AgenticRAGSkill - Agentic RAG 复杂问答

使用 langgraph 的 create_react_agent 实现多步推理：
- 动态检索
- 查询重写

支持 OpenAI 和 Ollama，对本地模型自动降级。
"""

from typing import Any

from langchain_core.tools import tool as tool_decorator
from langgraph.prebuilt import create_react_agent

from app.skills.base_skill import BaseSkill
from app.skills.knowledge_retrieval_skill import KnowledgeRetrievalSkill
from app.utils.exceptions import LLMError

SYSTEM_PROMPT = """你是 408 考研辅导助手，使用工具帮助用户回答复杂的考研问题。

请按照以下步骤思考：

1. 分析用户问题，确定涉及哪些知识点
2. 使用 knowledge_retrieval 检索相关内容
3. 如果检索结果不足，换一种方式描述后重新检索
4. 整合所有检索到的信息，基于教材内容生成完整回答

重要原则：
- 只基于检索到的教材内容回答
- 如果教材内容不足以回答问题，明确说明
- 如涉及代码，保留原格式
- 如涉及多个知识点，分点说明"""


class AgenticRAGSkill(BaseSkill):
    name = "agentic_rag"
    description = "Agentic RAG 复杂问答（多步推理）"

    def __init__(self, retrieval_skill: KnowledgeRetrievalSkill, llm: Any):
        super().__init__()
        self.retrieval_skill = retrieval_skill
        self.llm = llm
        self._agent = None

    def _build_agent(self):
        """构建 langgraph ReAct agent"""
        retrieval_skill = self.retrieval_skill
        skill_logger = self.logger

        @tool_decorator
        def knowledge_retrieval(query: str) -> str:
            """从教材中检索相关知识。输入具体的关键词或问题，返回相关教材内容。"""
            skill_logger.debug("Agent 调用检索 query='%s'", query[:80])
            try:
                results = retrieval_skill.execute({"query": query, "top_k": 5})
                items = results.get("results", [])
                if not items:
                    return "未找到相关内容"

                output_parts = []
                for item in items:
                    output_parts.append(
                        f"[{item.get('subsection', '')} {item.get('subsection_title', '')}]: "
                        f"{item.get('preview', '')}"
                    )
                return "\n\n".join(output_parts)
            except Exception as e:
                skill_logger.warning("Agent 检索失败 error=%s", str(e))
                return f"检索失败: {str(e)}"

        tools = [knowledge_retrieval]

        agent = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=SYSTEM_PROMPT,
        )
        return agent

    @property
    def agent(self):
        if self._agent is None:
            self._agent = self._build_agent()
        return self._agent

    def _execute_impl(self, params: dict) -> dict:
        """
        执行 Agentic RAG。

        Args:
            params: {"query": str, "subject": str|None}

        Returns:
            {"answer": str, "sources": [], "intermediate_steps": [...], "thinking": str|None, "is_agentic": bool}
        """
        query = params.get("query", "")
        if not query:
            return {"answer": "请输入问题", "sources": [], "intermediate_steps": [], "thinking": None, "is_agentic": True}

        try:
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": query}]},
                config={"recursion_limit": 10},
            )

            # 从 messages 中提取最终回答
            messages = result.get("messages", [])
            answer = ""
            steps = []
            thinking_parts = []

            for msg in messages:
                msg_type = getattr(msg, "type", "")
                if msg_type == "ai":
                    content = getattr(msg, "content", "") or ""
                    think, clean = self.extract_thinking(content)
                    if think:
                        thinking_parts.append(think)
                    if not getattr(msg, "tool_calls", None):
                        answer = clean or content
                elif msg_type == "tool":
                    steps.append({
                        "tool": getattr(msg, "name", "unknown"),
                        "output": str(getattr(msg, "content", ""))[:300],
                    })

            if not answer and messages:
                # Fallback: 取最后一条消息
                last = messages[-1]
                _, answer = self.extract_thinking(getattr(last, "content", str(last)))

            combined_thinking = "\n\n---\n\n".join(thinking_parts) if thinking_parts else None

            return {
                "answer": answer,
                "sources": [],
                "intermediate_steps": steps,
                "thinking": combined_thinking,
                "is_agentic": True,
            }
        except Exception as e:
            self.logger.error("Agentic RAG 失败 error=%s", str(e), exc_info=True)
            # 抛出异常让 SmartAnswerSkill 降级到标准 RAG
            raise LLMError(
                message="Agentic RAG 处理失败",
                detail=str(e),
            )
