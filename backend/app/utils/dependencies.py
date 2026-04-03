"""
FastAPI 依赖注入模块

管理全局共享资源（ChromaDB、SQLite、图谱数据、Skills 等），
通过 FastAPI 的 Depends() 机制注入到路由处理器中。
"""

import uuid
from contextvars import ContextVar
from typing import Any

from starlette.requests import Request

from app.utils.logging import get_logger

logger = get_logger("dependencies")

# ──────────── 请求级上下文 ────────────

# 每个请求的唯一 ID，用于日志关联
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """获取当前请求 ID"""
    return request_id_var.get()


# ──────────── 全局共享资源容器 ────────────


class AppState:
    """
    应用级共享资源容器。

    在 lifespan 中初始化，通过 app.state 传递给路由。
    """

    def __init__(self):
        self.chroma_collection: Any = None  # ChromaDB collection
        self.embeddings: Any = None         # Embedding 模型（SentenceTransformer）
        self.graph_data: dict | None = None # 知识图谱数据
        self.db_path: str = ""              # SQLite 数据库路径

        # Skills 注册表（在 lifespan 中填充）
        self.skills: dict[str, Any] = {}
        self._llm: Any = None               # LLM 实例（延迟创建）

    def is_ready(self) -> bool:
        """检查核心资源是否已就绪"""
        return self.chroma_collection is not None

    def get_llm(self) -> Any:
        """延迟创建 LLM 实例"""
        if self._llm is None:
            from app.llm_factory import LLMFactory
            self._llm = LLMFactory.create_llm()
            logger.info("LLM 实例延迟创建成功")
        return self._llm

    def get_skill(self, name: str) -> Any:
        """
        获取已注册的 Skill。

        对于 LLM 依赖的 Skills，首次访问时延迟创建。
        """
        if name in self.skills:
            return self.skills[name]

        # 延迟创建 LLM 依赖的 Skills
        if name in ("answer_generation", "smart_answer", "quiz_generation"):
            self._init_llm_skills()
            if name in self.skills:
                return self.skills[name]

        from app.utils.exceptions import AppError
        available = list(self.skills.keys())
        raise AppError(
            code=4001,
            message=f"Skill 不可用: {name}",
            detail=f"已注册 Skills: {available}",
        )

    def _init_llm_skills(self) -> None:
        """延迟初始化需要 LLM 的 Skills"""
        if "answer_generation" in self.skills:
            return  # 已初始化

        try:
            llm = self.get_llm()
            retrieval_skill = self.skills.get("knowledge_retrieval")
            if not retrieval_skill:
                logger.error("无法初始化 LLM Skills: knowledge_retrieval 不可用")
                return

            from app.skills.answer_generation_skill import AnswerGenerationSkill
            from app.skills.agentic_rag_skill import AgenticRAGSkill
            from app.skills.smart_answer_skill import SmartAnswerSkill
            from app.skills.quiz_generation_skill import QuizGenerationSkill

            basic = AnswerGenerationSkill(retrieval_skill, llm)
            self.skills["answer_generation"] = basic
            logger.info("注册 Skill: answer_generation")

            agentic = AgenticRAGSkill(retrieval_skill, llm)
            self.skills["agentic_rag"] = agentic
            logger.info("注册 Skill: agentic_rag")

            smart = SmartAnswerSkill(basic, agentic)
            self.skills["smart_answer"] = smart
            logger.info("注册 Skill: smart_answer")

            quiz = QuizGenerationSkill(retrieval_skill, llm)
            self.skills["quiz_generation"] = quiz
            logger.info("注册 Skill: quiz_generation")

        except Exception as e:
            logger.error("LLM Skills 初始化失败 error=%s", str(e), exc_info=True)


def get_app_state(request: Request) -> AppState:
    """从请求中获取应用状态"""
    return request.app.state.app_state


def get_chroma_collection(request: Request):
    """获取 ChromaDB collection"""
    state = get_app_state(request)
    if state.chroma_collection is None:
        logger.error("ChromaDB collection 未初始化")
        from app.utils.exceptions import VectorSearchError
        raise VectorSearchError(
            message="向量数据库未就绪",
            detail="ChromaDB collection 未在启动时正确初始化",
        )
    return state.chroma_collection


def get_embeddings(request: Request):
    """获取 Embedding 模型"""
    state = get_app_state(request)
    if state.embeddings is None:
        logger.error("Embedding 模型未初始化")
        from app.utils.exceptions import LLMError
        raise LLMError(
            message="Embedding 模型未就绪",
            detail="Embedding 模型未在启动时正确加载",
        )
    return state.embeddings


def get_graph_data(request: Request) -> dict | None:
    """获取知识图谱数据"""
    return get_app_state(request).graph_data
