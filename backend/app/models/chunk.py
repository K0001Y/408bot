"""
Pydantic 数据模型 - Chunk 相关
"""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """知识检索请求"""
    query: str = Field(..., description="搜索关键词或自然语言查询")
    subject: str | None = Field(None, description="科目代码: ds/os/co/cn")
    chapter: str | None = Field(None, description="章节号: 如 '3'")
    content_type: str | None = Field(None, description="内容类型: concept/code/table/exercise/answer/summary")
    top_k: int = Field(10, ge=1, le=50, description="返回结果数量")


class SearchResult(BaseModel):
    """单条检索结果"""
    chunk_id: str
    subsection: str | None = None
    subsection_title: str | None = None
    subject_code: str | None = None
    chapter_number: str | None = None
    content_type: str | None = None
    preview: str = ""
    score: float = 0.0


class SearchResponse(BaseModel):
    """检索响应"""
    results: list[SearchResult]
    total: int = 0


class ChunkDetail(BaseModel):
    """Chunk 完整详情"""
    chunk_id: str
    subject_code: str | None = None
    chapter_number: str | None = None
    chapter_title: str | None = None
    section_number: str | None = None
    section_title: str | None = None
    subsection: str | None = None
    subsection_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    content: str = ""
    content_type: str | None = None
    has_code: bool = False
    has_table: bool = False
    has_formula: bool = False


class AskRequest(BaseModel):
    """RAG 问答请求"""
    query: str = Field(..., description="用户问题")
    subject: str | None = Field(None, description="科目代码")


class AskResponse(BaseModel):
    """RAG 问答响应"""
    answer: str
    sources: list[SearchResult] = []
    thinking: str | None = None
    intermediate_steps: list[dict] = []
    is_agentic: bool = False
