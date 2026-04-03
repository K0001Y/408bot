"""
SmartAnswerSkill - 智能路由

根据查询复杂度自动选择标准 RAG 或 Agentic RAG。
"""

from typing import Any

from app.skills.base_skill import BaseSkill
from app.skills.answer_generation_skill import AnswerGenerationSkill
from app.skills.agentic_rag_skill import AgenticRAGSkill

# 复杂问题关键词
COMPLEX_INDICATORS = [
    "比较", "对比", "区别", "差异", "不同",
    "总结", "归纳", "所有", "列举",
    "分析", "为什么", "如何", "怎样",
    "关系", "联系", "影响",
    "优缺点", "优势", "劣势",
]


class SmartAnswerSkill(BaseSkill):
    name = "smart_answer"
    description = "智能选择标准 RAG 或 Agentic RAG"

    def __init__(self, basic_skill: AnswerGenerationSkill, agentic_skill: AgenticRAGSkill):
        super().__init__()
        self.basic_skill = basic_skill
        self.agentic_skill = agentic_skill

    def _execute_impl(self, params: dict) -> dict:
        query = params.get("query", "")
        complexity = self._analyze_complexity(query)

        self.logger.info("查询复杂度=%s query='%s'", complexity, query[:50])

        if complexity == "complex":
            try:
                return self.agentic_skill.execute(params)
            except Exception as e:
                self.logger.warning(
                    "Agentic RAG 失败，降级为标准 RAG error=%s", str(e),
                )
                return self.basic_skill.execute(params)
        else:
            return self.basic_skill.execute(params)

    def _analyze_complexity(self, query: str) -> str:
        """分析查询复杂度"""
        for indicator in COMPLEX_INDICATORS:
            if indicator in query:
                return "complex"
        return "simple"
