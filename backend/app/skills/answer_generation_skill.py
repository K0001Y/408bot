"""
AnswerGenerationSkill - 标准 RAG 问答

基于检索结果 + LLM 生成回答。
手动组装 RAG 链（不用 RetrievalQA），提供更细粒度的控制。
"""

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.skills.base_skill import BaseSkill
from app.skills.knowledge_retrieval_skill import KnowledgeRetrievalSkill
from app.utils.exceptions import LLMError

# RAG Prompt 模板
RAG_PROMPT_TEMPLATE = """你是 408 考研辅导助手，严格基于以下教材内容回答问题。

用户问题：{question}

相关教材内容：
{context}

要求：
1. 先分析用户问题涉及的知识点，在 <think> 标签中简要说明你的推理过程
2. 只基于提供的教材内容回答，不要添加外部知识
3. 如果教材内容不足以回答问题，明确说明"根据现有教材内容无法完整回答该问题"
4. 如涉及代码，保留原格式
5. 如涉及多个知识点，分点说明
6. 在回答末尾简要列出参考来源（章节号）

请按以下格式输出：
<think>
你的推理分析过程...
</think>

最终回答..."""


class AnswerGenerationSkill(BaseSkill):
    name = "answer_generation"
    description = "基于检索结果生成回答（标准 RAG）"

    def __init__(self, retrieval_skill: KnowledgeRetrievalSkill, llm: Any):
        """
        Args:
            retrieval_skill: 知识检索 Skill
            llm: LangChain BaseChatModel 实例
        """
        super().__init__()
        self.retrieval_skill = retrieval_skill
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
        self.chain = self.prompt | self.llm | StrOutputParser()

    def _execute_impl(self, params: dict) -> dict:
        """
        执行 RAG 问答。

        Args:
            params: {
                "query": str - 用户问题,
                "subject": str|None - 科目代码,
                "top_k": int - 检索数量 (默认 10)
            }

        Returns:
            {"answer": str, "sources": [...], "thinking": str|None, "intermediate_steps": [], "is_agentic": bool}
        """
        query = params.get("query", "")
        if not query:
            return {"answer": "请输入问题", "sources": [], "thinking": None, "intermediate_steps": [], "is_agentic": False}

        subject = params.get("subject")
        top_k = params.get("top_k", 10)

        # 1. 检索相关文档
        self.logger.info("检索相关文档 query='%s' subject=%s top_k=%d", query[:50], subject, top_k)
        retrieval_result = self.retrieval_skill.execute({
            "query": query,
            "subject": subject,
            "top_k": top_k,
        })
        sources = retrieval_result.get("results", [])

        if not sources:
            self.logger.warning("未检索到相关内容 query='%s'", query[:50])
            return {
                "answer": "未找到与您问题相关的教材内容，请尝试换一种方式描述问题。",
                "sources": [],
                "thinking": None,
                "intermediate_steps": [],
                "is_agentic": False,
            }

        # 2. 构建 context
        context_parts = []
        for i, src in enumerate(sources):
            section_info = f"[{src.get('subsection', '')} {src.get('subsection_title', '')}]"
            preview = src.get("preview", "")
            context_parts.append(f"来源{i + 1} {section_info}:\n{preview}")

        context = "\n\n".join(context_parts)
        self.logger.debug("构建 context 长度=%d 来源数=%d", len(context), len(sources))

        # 3. LLM 生成回答
        try:
            raw = self.chain.invoke({
                "question": query,
                "context": context,
            })
        except Exception as e:
            self.logger.error("LLM 生成失败 error=%s", str(e), exc_info=True)
            raise LLMError(
                message="回答生成失败",
                detail=f"query='{query}', error={str(e)}",
            )

        thinking, answer = self.extract_thinking(raw)

        return {
            "answer": answer,
            "sources": sources,
            "thinking": thinking or None,
            "intermediate_steps": [],
            "is_agentic": False,
        }
