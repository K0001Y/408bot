"""
真题坊 API 路由

端点:
- POST /upload  - 上传真题图片/PDF
- POST /analyze - 对上传的真题进行 RAG 解析
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.config import BACKEND_DIR
from app.utils.logging import get_logger
from app.utils.dependencies import get_app_state, AppState
from app.utils.exceptions import UnsupportedFileError, InputFormatError

logger = get_logger("api.exam")

router = APIRouter()

# 上传目录
UPLOAD_DIR = BACKEND_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 支持的文件类型
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class ExamAnalyzeRequest(BaseModel):
    """真题解析请求"""
    question_text: str = Field(..., description="题目文本（手动输入或 OCR 结果）")
    subject: str | None = Field(None, description="科目代码")


class ExamAnalyzeResponse(BaseModel):
    """真题解析响应"""
    answer: str
    knowledge_points: list[str] = []
    sources: list[dict] = []


@router.post("/upload")
async def upload_exam(file: UploadFile = File(...)):
    """
    上传真题图片/PDF。

    返回文件路径和提取的文本内容（如果可能）。
    当前版本: 保存文件，返回文件 ID，用户需手动输入题目文本。
    后续版本: 集成 OCR 自动提取。
    """
    if not file.filename:
        raise InputFormatError(message="文件名不能为空")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileError(
            message=f"不支持的文件格式: {ext}",
            detail=f"支持的格式: {ALLOWED_EXTENSIONS}",
        )

    # 读取文件内容
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise InputFormatError(
            message=f"文件过大（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）",
            detail=f"实际大小: {len(content)} bytes",
        )

    # 保存文件
    file_id = uuid.uuid4().hex[:12]
    saved_name = f"{file_id}{ext}"
    save_path = UPLOAD_DIR / saved_name

    with open(save_path, "wb") as f:
        f.write(content)

    logger.info(
        "文件上传成功 filename=%s file_id=%s size=%d bytes",
        file.filename, file_id, len(content),
    )

    # OCR 自动识别（不阻塞上传）
    ocr_text = ""
    ocr_error = None
    try:
        from app.utils.ocr import get_ocr_engine
        engine = get_ocr_engine()
        if engine.available:
            ocr_text = engine.recognize(save_path)
            if ocr_text:
                logger.info("OCR 识别成功 file_id=%s chars=%d", file_id, len(ocr_text))
        else:
            ocr_error = "OCR 引擎未就绪"
    except Exception as e:
        ocr_error = str(e)
        logger.warning("OCR 识别失败 file_id=%s error=%s", file_id, ocr_error)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "saved_as": saved_name,
        "size": len(content),
        "message": "文件上传成功" + ("，已自动识别文字。" if ocr_text else "。请在下方输入题目文本进行解析。"),
        "ocr_text": ocr_text,
        "ocr_error": ocr_error,
    }


@router.post("/analyze", response_model=ExamAnalyzeResponse)
async def analyze_exam(req: ExamAnalyzeRequest, request: Request):
    """
    真题解析。

    使用 RAG 对题目文本进行知识点分析和作答。
    """
    state: AppState = get_app_state(request)

    if not req.question_text.strip():
        raise InputFormatError(message="题目文本不能为空")

    logger.info(
        "真题解析 text='%s' subject=%s",
        req.question_text[:50], req.subject,
    )

    # 使用 smart_answer 进行解答
    smart_skill = state.get_skill("smart_answer")
    result = smart_skill.execute({
        "query": req.question_text,
        "subject": req.subject,
    })

    # 从来源中提取涉及的知识点
    sources = result.get("sources", [])
    knowledge_points = list({
        s.get("subsection_title", "")
        for s in sources
        if s.get("subsection_title")
    })

    return ExamAnalyzeResponse(
        answer=result.get("answer", ""),
        knowledge_points=sorted(knowledge_points),
        sources=sources,
    )
