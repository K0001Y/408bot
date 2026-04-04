"""
错题本 API 路由

端点:
- POST /              - 添加错题（解析 "页码 章节 题号1 题号2..." 格式）
- GET  /              - 错题列表
- DELETE /{id}        - 删除错题
- POST /generate-word - 生成 Word 文档
- GET  /download/{fn} - 下载 Word 文件
"""

import uuid
import re
from pathlib import Path

import aiosqlite
from fastapi import APIRouter, Request, Query
from fastapi.responses import FileResponse

from app.models.mistake import (
    MistakeCreate, MistakeUpdate, MistakeItem, MistakeListResponse,
    MistakeAddResponse, WordGenerateRequest, WordGenerateResponse,
)
from app.config import BACKEND_DIR
from app.utils.logging import get_logger
from app.utils.dependencies import get_app_state, AppState
from app.utils.exceptions import (
    InputFormatError, QuestionNotFoundError,
)
from app.utils.question_parser import extract_question_by_number, extract_answer_by_number

logger = get_logger("api.mistakes")

router = APIRouter()

# Word 导出目录
EXPORT_DIR = BACKEND_DIR / "data" / "exports"


# ──────────── 解析输入格式 ────────────

def parse_mistake_input(raw: str) -> tuple[int, str, list[int]]:
    """
    解析错题输入格式: "页码 章节 题号1 题号2 ..."
    例如: "156 3.4 5 6 7" → (156, "3.4", [5, 6, 7])

    Returns:
        (page, chapter, question_numbers)

    Raises:
        InputFormatError: 格式不正确
    """
    parts = raw.strip().split()
    if len(parts) < 3:
        raise InputFormatError(
            message="输入格式错误",
            detail=f"期望格式: '页码 章节 题号1 题号2 ...'，如 '156 3.4 5 6 7'。实际输入: '{raw}'",
        )

    try:
        page = int(parts[0])
    except ValueError:
        raise InputFormatError(
            message="页码必须是整数",
            detail=f"页码='{parts[0]}'",
        )

    chapter = parts[1]
    # 验证章节格式 (如 "3", "3.4", "12.1")
    if not re.match(r"^\d+(\.\d+)*$", chapter):
        raise InputFormatError(
            message="章节格式不正确",
            detail=f"章节='{chapter}'，期望格式如 '3' 或 '3.4'",
        )

    question_numbers = []
    for p in parts[2:]:
        try:
            question_numbers.append(int(p))
        except ValueError:
            raise InputFormatError(
                message=f"题号必须是整数",
                detail=f"题号='{p}'",
            )

    if not question_numbers:
        raise InputFormatError(
            message="至少需要一个题号",
            detail=f"输入: '{raw}'",
        )

    return page, chapter, question_numbers


# ──────────── 端点 ────────────


@router.post("/", response_model=MistakeAddResponse)
async def add_mistakes(req: MistakeCreate, request: Request):
    """
    添加错题。

    输入格式: "页码 章节 题号1 题号2..."
    """
    state: AppState = get_app_state(request)

    page, chapter, q_numbers = parse_mistake_input(req.input)

    logger.info(
        "添加错题 subject=%s page=%d chapter=%s questions=%s",
        req.subject_code, page, chapter, q_numbers,
    )

    added_items = []

    async with aiosqlite.connect(state.db_path) as db:
        for q_num in q_numbers:
            mistake_id = f"{req.subject_code}_{chapter}_{q_num}_{uuid.uuid4().hex[:6]}"

            # 尝试从知识库中获取题目和答案文本
            question_text = ""
            answer_text = ""

            try:
                q_skill = state.skills.get("question_location")
                if q_skill:
                    # 按节精确检索，避免语义搜索带来的误匹配
                    section_result = q_skill.find_by_section(
                        subject=req.subject_code,
                        section_number=chapter,
                    )

                    exercises = section_result.get("exercises", [])
                    answers = section_result.get("answers", [])

                    # 从整个小节 chunk 中按题号提取单道题
                    for ex in exercises:
                        text = extract_question_by_number(ex.get("content", ""), q_num)
                        if text:
                            question_text = text
                            break
                    for ans in answers:
                        text = extract_answer_by_number(ans.get("content", ""), q_num)
                        if text:
                            answer_text = text
                            break
            except Exception as e:
                logger.warning(
                    "题目内容检索失败 q=%d error=%s", q_num, str(e),
                )

            await db.execute(
                """
                INSERT OR REPLACE INTO mistakes
                (mistake_id, subject_code, page, chapter, question_number,
                 question_text, answer_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (mistake_id, req.subject_code, page, chapter, q_num,
                 question_text, answer_text),
            )

            added_items.append(MistakeItem(
                mistake_id=mistake_id,
                subject_code=req.subject_code,
                page=page,
                chapter=chapter,
                question_number=q_num,
                question_text=question_text,
                answer_text=answer_text,
            ))

        await db.commit()

    logger.info("添加错题完成 count=%d", len(added_items))

    return MistakeAddResponse(added=len(added_items), mistakes=added_items)


@router.get("/", response_model=MistakeListResponse)
async def list_mistakes(
    request: Request,
    subject: str | None = Query(None, description="科目代码过滤"),
    chapter: str | None = Query(None, description="章节过滤"),
):
    """错题列表"""
    state: AppState = get_app_state(request)

    logger.info("获取错题列表 subject=%s chapter=%s", subject, chapter)

    query = "SELECT * FROM mistakes WHERE 1=1"
    params: list = []

    if subject:
        query += " AND subject_code = ?"
        params.append(subject)
    if chapter:
        query += " AND chapter = ?"
        params.append(chapter)

    query += " ORDER BY added_at DESC"

    async with aiosqlite.connect(state.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    mistakes = []
    for row in rows:
        mistakes.append(MistakeItem(
            mistake_id=row["mistake_id"],
            subject_code=row["subject_code"],
            page=row["page"],
            chapter=row["chapter"],
            question_number=row["question_number"],
            question_text=row["question_text"] or "",
            answer_text=row["answer_text"] or "",
            explanation=row["explanation"] or "",
            added_at=str(row["added_at"]) if row["added_at"] else "",
        ))

    logger.info("错题列表返回 count=%d", len(mistakes))
    return MistakeListResponse(mistakes=mistakes, total=len(mistakes))


@router.delete("/{mistake_id}")
async def delete_mistake(mistake_id: str, request: Request):
    """删除错题"""
    state: AppState = get_app_state(request)

    logger.info("删除错题 mistake_id=%s", mistake_id)

    async with aiosqlite.connect(state.db_path) as db:
        cursor = await db.execute(
            "DELETE FROM mistakes WHERE mistake_id = ?",
            (mistake_id,),
        )
        await db.commit()

        if cursor.rowcount == 0:
            raise QuestionNotFoundError(
                message=f"错题不存在: {mistake_id}",
                detail=f"mistake_id={mistake_id}",
            )

    return {"message": "删除成功", "mistake_id": mistake_id}


@router.put("/{mistake_id}", response_model=MistakeItem)
async def update_mistake(mistake_id: str, req: MistakeUpdate, request: Request):
    """
    更新错题内容。

    只更新请求中非 None 的字段。
    """
    state: AppState = get_app_state(request)

    # 构建动态 UPDATE 语句
    fields = []
    values = []

    if req.question_text is not None:
        fields.append("question_text = ?")
        values.append(req.question_text)
    if req.answer_text is not None:
        fields.append("answer_text = ?")
        values.append(req.answer_text)
    if req.explanation is not None:
        fields.append("explanation = ?")
        values.append(req.explanation)

    if not fields:
        raise InputFormatError(message="至少需要提供一个要更新的字段")

    # 添加 updated_at 时间戳
    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(mistake_id)

    sql = f"UPDATE mistakes SET {', '.join(fields)} WHERE mistake_id = ?"

    logger.info("更新错题 mistake_id=%s fields=%s", mistake_id, [f.split(" =")[0] for f in fields[:-1]])

    async with aiosqlite.connect(state.db_path) as db:
        cursor = await db.execute(sql, values)
        await db.commit()

        if cursor.rowcount == 0:
            raise QuestionNotFoundError(
                message=f"错题不存在: {mistake_id}",
                detail=f"mistake_id={mistake_id}",
            )

        # 返回更新后的完整记录
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mistakes WHERE mistake_id = ?", (mistake_id,)) as cur:
            row = await cur.fetchone()

    return MistakeItem(
        mistake_id=row["mistake_id"],
        subject_code=row["subject_code"],
        page=row["page"],
        chapter=row["chapter"],
        question_number=row["question_number"],
        question_text=row["question_text"] or "",
        answer_text=row["answer_text"] or "",
        explanation=row["explanation"] or "",
        added_at=str(row["added_at"]) if row["added_at"] else "",
    )


@router.post("/generate-word", response_model=WordGenerateResponse)
async def generate_word(req: WordGenerateRequest, request: Request):
    """生成 Word 文档"""
    state: AppState = get_app_state(request)

    if not req.mistake_ids:
        raise InputFormatError(message="错题 ID 列表不能为空")

    logger.info("生成 Word 文档 ids=%d", len(req.mistake_ids))

    # 查询选中的错题
    placeholders = ",".join("?" for _ in req.mistake_ids)
    query = f"SELECT * FROM mistakes WHERE mistake_id IN ({placeholders})"

    async with aiosqlite.connect(state.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, req.mistake_ids) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        raise QuestionNotFoundError(
            message="未找到指定的错题",
            detail=f"ids={req.mistake_ids}",
        )

    mistakes_data = []
    for row in rows:
        mistakes_data.append({
            "mistake_id": row["mistake_id"],
            "subject_code": row["subject_code"],
            "page": row["page"],
            "chapter": row["chapter"],
            "question_number": row["question_number"],
            "question_text": row["question_text"] or "",
            "answer_text": row["answer_text"] or "",
            "explanation": row["explanation"] or "",
            "added_at": str(row["added_at"]) if row["added_at"] else "",
        })

    # 生成 Word
    docx_skill = state.get_skill("docx_generation")
    result = docx_skill.execute({"mistakes": mistakes_data})

    filename = result.get("filename", "")
    if not filename:
        raise InputFormatError(message="Word 生成失败")

    return WordGenerateResponse(
        filename=filename,
        download_url=result.get("download_url", ""),
    )


@router.get("/download/{filename}")
async def download_word(filename: str):
    """下载生成的 Word 文件"""
    logger.info("下载 Word 文件 filename=%s", filename)

    filepath = EXPORT_DIR / filename

    if not filepath.exists():
        raise QuestionNotFoundError(
            message=f"文件不存在: {filename}",
            detail=f"path={filepath}",
        )

    # 安全检查：防止路径穿越
    if not filepath.resolve().is_relative_to(EXPORT_DIR.resolve()):
        raise InputFormatError(
            message="无效的文件路径",
            detail=f"filename={filename}",
        )

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
