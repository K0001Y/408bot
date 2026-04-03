"""
FastAPI 应用入口

包含:
- lifespan: 启动时加载资源（Embedding、ChromaDB、图谱、SQLite）
- 中间件: CORS、请求日志（含 request_id）
- 全局异常处理: AppError → JSON 错误响应
- 路由挂载: /api/knowledge, /api/graph, /api/practice, /api/exam, /api/mistakes
"""

import json
import time
import uuid
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings, BACKEND_DIR
from app.utils.logging import setup_logging, get_logger
from app.utils.exceptions import AppError
from app.utils.dependencies import AppState, request_id_var

# 在模块导入时就初始化日志
setup_logging()
logger = get_logger("main")


# ──────────── Lifespan ────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动时加载资源，关闭时清理"""
    settings = get_settings()
    app_state = AppState()

    logger.info("=" * 60)
    logger.info("应用启动 name=%s version=%s", settings.app.name, settings.app.version)
    logger.info("=" * 60)

    # 1. 加载 Embedding 模型
    t0 = time.time()
    try:
        from app.llm_factory import LLMFactory
        app_state.embeddings = LLMFactory.create_embeddings()
        logger.info("Embedding 模型加载完成 elapsed=%.2fs", time.time() - t0)
    except Exception as e:
        logger.critical("Embedding 模型加载失败，应用无法正常运行 error=%s", str(e), exc_info=True)
        # 不阻止启动，但后续检索功能不可用

    # 2. 初始化 ChromaDB
    t0 = time.time()
    try:
        import chromadb
        persist_dir = str(settings.vector_db.abs_persist_directory)
        client = chromadb.PersistentClient(path=persist_dir)
        collection_name = settings.vector_db.collection_name

        # 尝试获取已有 collection
        try:
            app_state.chroma_collection = client.get_collection(
                name=collection_name,
            )
            count = app_state.chroma_collection.count()
            logger.info(
                "ChromaDB 连接成功 collection=%s documents=%d elapsed=%.2fs",
                collection_name, count, time.time() - t0,
            )
        except Exception:
            logger.warning(
                "ChromaDB collection '%s' 不存在，请先运行 scripts/ingest_chunks.py 导入数据",
                collection_name,
            )
    except Exception as e:
        logger.critical("ChromaDB 初始化失败 error=%s", str(e), exc_info=True)

    # 3. 加载知识图谱
    t0 = time.time()
    try:
        graph_path = settings.graph.abs_graph_json_path
        if graph_path.exists():
            with open(graph_path, "r", encoding="utf-8") as f:
                app_state.graph_data = json.load(f)
            node_count = len(app_state.graph_data.get("nodes", []))
            edge_count = len(app_state.graph_data.get("edges", []))
            logger.info(
                "知识图谱加载完成 nodes=%d edges=%d elapsed=%.2fs",
                node_count, edge_count, time.time() - t0,
            )
        else:
            logger.warning(
                "知识图谱文件不存在 path=%s，请先运行 scripts/build_graph.py",
                graph_path,
            )
    except Exception as e:
        logger.error("知识图谱加载失败 error=%s", str(e), exc_info=True)

    # 4. 初始化 SQLite (错题数据库)
    t0 = time.time()
    try:
        import aiosqlite
        import asyncio

        db_path = str(settings.mistakes.abs_db_path)
        db_path_obj = settings.mistakes.abs_db_path
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)
        app_state.db_path = db_path

        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mistakes (
                    mistake_id TEXT PRIMARY KEY,
                    subject_code TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    chapter TEXT NOT NULL,
                    question_number INTEGER NOT NULL,
                    question_text TEXT DEFAULT '',
                    answer_text TEXT DEFAULT '',
                    explanation TEXT DEFAULT '',
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
        logger.info("SQLite 数据库初始化完成 path=%s elapsed=%.2fs", db_path, time.time() - t0)
    except Exception as e:
        logger.error("SQLite 初始化失败 error=%s", str(e), exc_info=True)

    # 5. 检查 LLM 可用性
    try:
        from app.llm_factory import LLMFactory
        if settings.llm.provider == "ollama":
            if LLMFactory.check_ollama_health():
                logger.info("Ollama 服务检查通过")
            else:
                logger.warning(
                    "Ollama 服务不可用 url=%s，RAG 问答功能将不可用。"
                    "请确保 Ollama 已启动: ollama serve",
                    settings.llm.ollama.base_url,
                )
        elif settings.llm.provider == "openai":
            if settings.llm.openai.api_key:
                logger.info("OpenAI API Key 已配置")
            else:
                logger.warning("OpenAI API Key 未配置，RAG 问答功能将不可用")
    except Exception as e:
        logger.warning("LLM 可用性检查失败 error=%s", str(e))

    # 6. 初始化 Skills（不依赖 LLM 的部分）
    t0 = time.time()
    try:
        if app_state.chroma_collection and app_state.embeddings:
            from app.skills.knowledge_retrieval_skill import KnowledgeRetrievalSkill
            from app.skills.question_location_skill import QuestionLocationSkill

            retrieval = KnowledgeRetrievalSkill(
                app_state.chroma_collection, app_state.embeddings,
            )
            app_state.skills["knowledge_retrieval"] = retrieval
            logger.info("注册 Skill: knowledge_retrieval")

            question_loc = QuestionLocationSkill(
                app_state.chroma_collection, app_state.embeddings,
            )
            app_state.skills["question_location"] = question_loc
            logger.info("注册 Skill: question_location")

        if app_state.graph_data:
            from app.skills.knowledge_graph_skill import KnowledgeGraphSkill
            graph_skill = KnowledgeGraphSkill(app_state.graph_data)
            app_state.skills["knowledge_graph"] = graph_skill
            logger.info("注册 Skill: knowledge_graph")

        from app.skills.docx_generation_skill import DocxGenerationSkill
        docx_skill = DocxGenerationSkill()
        app_state.skills["docx_generation"] = docx_skill
        logger.info("注册 Skill: docx_generation")

        logger.info(
            "Skills 初始化完成 registered=%s elapsed=%.2fs",
            list(app_state.skills.keys()), time.time() - t0,
        )
    except Exception as e:
        logger.error("Skills 初始化失败 error=%s", str(e), exc_info=True)

    logger.info("=" * 60)
    logger.info("应用启动完成 - 所有资源加载结束")
    logger.info("=" * 60)

    # 挂载到 app.state
    app.state.app_state = app_state

    yield

    # 关闭清理
    logger.info("应用关闭，清理资源...")


# ──────────── FastAPI App ────────────


settings = get_settings()

app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────── 请求日志中间件 ────────────


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    为每个请求生成唯一 ID，记录请求开始/完成/异常。
    响应头中包含 X-Request-ID 方便日志关联。
    """
    rid = str(uuid.uuid4())[:8]
    request_id_var.set(rid)

    method = request.method
    path = request.url.path
    query = str(request.query_params) if request.query_params else ""

    logger.info("[%s] 请求开始 %s %s %s", rid, method, path, query)
    t0 = time.time()

    try:
        response = await call_next(request)
        elapsed_ms = (time.time() - t0) * 1000
        logger.info(
            "[%s] 请求完成 %s %s status=%d elapsed=%.1fms",
            rid, method, path, response.status_code, elapsed_ms,
        )
        response.headers["X-Request-ID"] = rid
        return response
    except Exception as e:
        elapsed_ms = (time.time() - t0) * 1000
        logger.error(
            "[%s] 请求异常 %s %s error=%s elapsed=%.1fms",
            rid, method, path, str(e), elapsed_ms, exc_info=True,
        )
        raise


# ──────────── 全局异常处理器 ────────────


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """处理业务异常 → 结构化 JSON 错误响应"""
    rid = request_id_var.get()

    # 4xxx → 400, 5xxx → 500
    http_status = 400 if exc.code < 5000 else 500

    if exc.detail:
        logger.error(
            "[%s] AppError code=%d message='%s' detail='%s'",
            rid, exc.code, exc.message, exc.detail,
        )
    else:
        logger.warning("[%s] AppError code=%d message='%s'", rid, exc.code, exc.message)

    return JSONResponse(
        status_code=http_status,
        content={
            "error_code": exc.code,
            "message": exc.message,
            "request_id": rid,
        },
        headers={"X-Request-ID": rid},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """处理未预期异常 → 通用 500 错误（不泄露内部信息）"""
    rid = request_id_var.get()

    logger.error(
        "[%s] 未预期异常 type=%s message='%s'\n%s",
        rid, type(exc).__name__, str(exc), traceback.format_exc(),
    )

    return JSONResponse(
        status_code=500,
        content={
            "error_code": 5000,
            "message": "服务器内部错误",
            "request_id": rid,
        },
        headers={"X-Request-ID": rid},
    )


# ──────────── 路由挂载 ────────────

from app.api import knowledge, graph, practice, exam, mistakes

app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(graph.router, prefix="/api/graph", tags=["知识图谱"])
app.include_router(practice.router, prefix="/api/practice", tags=["练习室"])
app.include_router(exam.router, prefix="/api/exam", tags=["真题坊"])
app.include_router(mistakes.router, prefix="/api/mistakes", tags=["错题本"])


# ──────────── 健康检查 ────────────


@app.get("/api/health")
async def health_check(request: Request):
    """系统健康检查"""
    state = request.app.state.app_state
    return {
        "status": "ok" if state.is_ready() else "degraded",
        "version": settings.app.version,
        "components": {
            "vector_db": state.chroma_collection is not None,
            "embeddings": state.embeddings is not None,
            "knowledge_graph": state.graph_data is not None,
            "database": bool(state.db_path),
        },
    }
