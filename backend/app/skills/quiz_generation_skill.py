"""
QuizGenerationSkill - AI 习题生成

基于教材知识点，通过 LLM 生成不同类型的练习题。
支持选择题、填空题、简答题、算法题等。
"""

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.skills.base_skill import BaseSkill
from app.skills.knowledge_retrieval_skill import KnowledgeRetrievalSkill
from app.utils.exceptions import LLMError


# 出题 Prompt 模板
QUIZ_PROMPT_TEMPLATE = """你是 408 考研命题专家。根据以下教材知识点，出 {count} 道 {quiz_type} 题。

知识点范围：
{context}

要求：
1. 题目难度为 {difficulty}（简单/中等/困难）
2. 每道题后给出参考答案和解析
3. 题目内容严格基于提供的教材知识点
4. 选择题需有 A/B/C/D 四个选项
5. 格式要求：
   - 每道题之间用空行分隔
   - 题号格式：【题目1】、【题目2】...
   - 答案格式：【答案】
   - 解析格式：【解析】

{extra_instructions}

请出题："""


# 支持的题型
QUIZ_TYPES = {
    "choice": "选择题",
    "fill": "填空题",
    "short_answer": "简答题",
    "algorithm": "算法题",
    "comprehensive": "综合题",
}

# 难度映射
DIFFICULTY_MAP = {
    "easy": "简单",
    "medium": "中等",
    "hard": "困难",
}


class QuizGenerationSkill(BaseSkill):
    name = "quiz_generation"
    description = "基于教材知识点生成练习题"

    def __init__(self, retrieval_skill: KnowledgeRetrievalSkill, llm: Any):
        """
        Args:
            retrieval_skill: 知识检索 Skill（用于获取相关知识点）
            llm: LangChain BaseChatModel 实例
        """
        super().__init__()
        self.retrieval_skill = retrieval_skill
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template(QUIZ_PROMPT_TEMPLATE)
        self.chain = self.prompt | self.llm | StrOutputParser()

    def _execute_impl(self, params: dict) -> dict:
        """
        生成练习题。

        Args:
            params: {
                "topic": str - 知识点/章节主题,
                "subject": str|None - 科目代码 ds/os/co/cn,
                "quiz_type": str - 题型 (choice/fill/short_answer/algorithm/comprehensive),
                "count": int - 题目数量 (默认 3),
                "difficulty": str - 难度 (easy/medium/hard, 默认 medium),
                "top_k": int - 检索知识点数量 (默认 8),
            }

        Returns:
            {"quiz_content": str, "quiz_type": str, "count": int,
             "difficulty": str, "sources": [...]}
        """
        topic = params.get("topic", "")
        if not topic:
            return {
                "quiz_content": "请提供出题的知识点或主题",
                "quiz_type": "",
                "count": 0,
                "difficulty": "",
                "sources": [],
            }

        subject = params.get("subject")
        quiz_type_key = params.get("quiz_type", "choice")
        count = params.get("count", 3)
        difficulty_key = params.get("difficulty", "medium")
        top_k = params.get("top_k", 8)

        quiz_type = QUIZ_TYPES.get(quiz_type_key, "选择题")
        difficulty = DIFFICULTY_MAP.get(difficulty_key, "中等")

        self.logger.info(
            "AI 出题 topic='%s' type=%s count=%d difficulty=%s subject=%s",
            topic[:50], quiz_type, count, difficulty, subject,
        )

        # 1. 检索相关知识点
        retrieval_result = self.retrieval_skill.execute({
            "query": topic,
            "subject": subject,
            "top_k": top_k,
        })
        sources = retrieval_result.get("results", [])

        if not sources:
            self.logger.warning("未检索到相关知识点 topic='%s'", topic[:50])
            return {
                "quiz_content": "未找到与该主题相关的教材内容，无法出题。请尝试更具体的知识点描述。",
                "quiz_type": quiz_type,
                "count": 0,
                "difficulty": difficulty,
                "sources": [],
            }

        # 2. 构建知识点上下文
        context_parts = []
        for i, src in enumerate(sources):
            section = f"[{src.get('subsection', '')} {src.get('subsection_title', '')}]"
            preview = src.get("preview", "")
            context_parts.append(f"知识点{i + 1} {section}:\n{preview}")

        context = "\n\n".join(context_parts)

        # 3. 构建额外指令
        extra_instructions = ""
        if quiz_type_key == "algorithm":
            extra_instructions = "算法题需要给出完整的代码实现和时间/空间复杂度分析。"
        elif quiz_type_key == "comprehensive":
            extra_instructions = "综合题需要涉及多个知识点的关联，考查综合分析能力。"

        # 4. LLM 生成题目
        try:
            quiz_content = self.chain.invoke({
                "context": context,
                "quiz_type": quiz_type,
                "count": count,
                "difficulty": difficulty,
                "extra_instructions": extra_instructions,
            })
        except Exception as e:
            self.logger.error("LLM 出题失败 error=%s", str(e), exc_info=True)
            raise LLMError(
                message="AI 出题失败",
                detail=f"topic='{topic}', type={quiz_type}, error={str(e)}",
            )

        self.logger.info("AI 出题完成 生成长度=%d", len(quiz_content))

        return {
            "quiz_content": quiz_content,
            "quiz_type": quiz_type,
            "count": count,
            "difficulty": difficulty,
            "sources": sources,
        }
