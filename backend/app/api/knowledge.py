"""
知识库 API 路由

端点:
- POST /search     - 知识检索
- GET  /chunk/{id} - 获取 chunk 详情
- POST /ask        - RAG 问答（智能路由）
- GET  /chapters   - 获取章节树
"""

from fastapi import APIRouter, Request, Depends

from app.models.chunk import (
    SearchRequest, SearchResponse, SearchResult,
    ChunkDetail, AskRequest, AskResponse,
)
from app.utils.logging import get_logger
from app.utils.dependencies import get_app_state, AppState
from app.utils.exceptions import QuestionNotFoundError, VectorSearchError

logger = get_logger("api.knowledge")

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(req: SearchRequest, request: Request):
    """知识检索"""
    state: AppState = get_app_state(request)
    skill = state.get_skill("knowledge_retrieval")

    logger.info(
        "知识检索 query='%s' subject=%s chapter=%s type=%s top_k=%d",
        req.query[:50], req.subject, req.chapter, req.content_type, req.top_k,
    )

    result = skill.execute({
        "query": req.query,
        "subject": req.subject,
        "chapter": req.chapter,
        "content_type": req.content_type,
        "top_k": req.top_k,
    })

    results = [SearchResult(**r) for r in result.get("results", [])]
    return SearchResponse(results=results, total=result.get("total", 0))


@router.get("/chunk/{chunk_id}")
async def get_chunk_detail(chunk_id: str, request: Request):
    """获取 chunk 详情"""
    state: AppState = get_app_state(request)
    skill = state.get_skill("knowledge_retrieval")

    logger.info("获取 chunk 详情 chunk_id=%s", chunk_id)

    detail = skill.get_chunk_detail(chunk_id)
    if detail is None:
        raise QuestionNotFoundError(
            message=f"Chunk 不存在: {chunk_id}",
            detail=f"chunk_id={chunk_id}",
        )

    return detail


@router.post("/ask", response_model=AskResponse)
async def ask_question(req: AskRequest, request: Request):
    """RAG 问答 - 自动路由到标准 RAG 或 Agentic RAG"""
    state: AppState = get_app_state(request)
    skill = state.get_skill("smart_answer")

    logger.info("RAG 问答 query='%s' subject=%s", req.query[:50], req.subject)

    result = skill.execute({
        "query": req.query,
        "subject": req.subject,
    })

    sources = [
        SearchResult(**s) for s in result.get("sources", [])
    ]

    return AskResponse(
        answer=result.get("answer", ""),
        sources=sources,
    )


@router.get("/chapters")
async def get_chapters(request: Request):
    """获取章节树 - 从 ChromaDB metadata 聚合"""
    state: AppState = get_app_state(request)

    if state.chroma_collection is None:
        raise VectorSearchError(message="向量数据库未就绪")

    logger.info("获取章节树")

    try:
        # 获取所有 chunks 的 metadata 来构建章节树
        all_meta = state.chroma_collection.get(
            include=["metadatas"],
        )

        # 聚合章节结构: subject → chapter → [sections]
        tree: dict[str, dict[str, set[str]]] = {}

        for meta in all_meta.get("metadatas", []):
            if not meta:
                continue
            subject = meta.get("subject_code", "")
            chapter = meta.get("chapter_number", "")
            subsection = meta.get("subsection", "")
            sub_title = meta.get("subsection_title", "")

            if not subject or not chapter:
                continue

            tree.setdefault(subject, {}).setdefault(chapter, set())
            if subsection:
                label = f"{subsection} {sub_title}" if sub_title else subsection
                tree[subject][chapter].add(label)

        # 转为 JSON 友好格式
        result = {}
        for subject, chapters in sorted(tree.items()):
            result[subject] = {}
            for ch, sections in sorted(chapters.items(), key=lambda x: x[0]):
                result[subject][ch] = sorted(sections)

        return {"chapters": result}

    except Exception as e:
        logger.error("获取章节树失败 error=%s", str(e), exc_info=True)
        raise VectorSearchError(
            message="获取章节树失败",
            detail=str(e),
        )
