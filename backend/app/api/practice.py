"""
练习室 API 路由

端点:
- GET  /exercises - 教材习题列表
- POST /generate  - AI 生成习题
"""

from fastapi import APIRouter, Request, Query
from pydantic import BaseModel, Field

from app.utils.logging import get_logger
from app.utils.dependencies import get_app_state, AppState

logger = get_logger("api.practice")

router = APIRouter()


# ──────────── 请求/响应模型 ────────────


class QuizGenerateRequest(BaseModel):
    """AI 出题请求"""
    topic: str = Field(..., description="知识点或主题")
    subject: str | None = Field(None, description="科目代码: ds/os/co/cn")
    quiz_type: str = Field("choice", description="题型: choice/fill/short_answer/algorithm/comprehensive")
    count: int = Field(3, ge=1, le=10, description="题目数量")
    difficulty: str = Field("medium", description="难度: easy/medium/hard")


class QuizGenerateResponse(BaseModel):
    """AI 出题响应"""
    quiz_content: str
    quiz_type: str
    count: int
    difficulty: str
    sources: list[dict] = []


# ──────────── 端点 ────────────


@router.get("/exercises")
async def get_exercises(
    request: Request,
    subject: str | None = Query(None, description="科目代码"),
    chapter: str | None = Query(None, description="章节号"),
    query: str | None = Query(None, description="搜索关键词"),
    top_k: int = Query(20, ge=1, le=100),
):
    """教材习题列表"""
    state: AppState = get_app_state(request)
    skill = state.get_skill("question_location")

    logger.info(
        "获取教材习题 subject=%s chapter=%s query=%s top_k=%d",
        subject, chapter, query and query[:30], top_k,
    )

    result = skill.execute({
        "subject": subject,
        "chapter": chapter,
        "query": query,
        "top_k": top_k,
        "include_answers": True,
    })

    return {
        "exercises": result.get("exercises", []),
        "answers": result.get("answers", []),
        "total": result.get("total", 0),
    }


@router.post("/generate", response_model=QuizGenerateResponse)
async def generate_quiz(req: QuizGenerateRequest, request: Request):
    """AI 生成习题"""
    state: AppState = get_app_state(request)
    skill = state.get_skill("quiz_generation")

    logger.info(
        "AI 出题 topic='%s' type=%s count=%d difficulty=%s",
        req.topic[:50], req.quiz_type, req.count, req.difficulty,
    )

    result = skill.execute({
        "topic": req.topic,
        "subject": req.subject,
        "quiz_type": req.quiz_type,
        "count": req.count,
        "difficulty": req.difficulty,
    })

    return QuizGenerateResponse(
        quiz_content=result.get("quiz_content", ""),
        quiz_type=result.get("quiz_type", ""),
        count=result.get("count", 0),
        difficulty=result.get("difficulty", ""),
        sources=result.get("sources", []),
    )
