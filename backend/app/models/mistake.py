"""
Pydantic 数据模型 - 错题本相关
"""

from datetime import datetime

from pydantic import BaseModel, Field


class MistakeCreate(BaseModel):
    """错题添加请求"""
    input: str = Field(..., description="输入格式: '页面 章节 题号1 题号2 ...'，如 '156 3.4 5 6 7'")
    subject_code: str = Field(..., description="科目代码: ds/os/co/cn")


class MistakeUpdate(BaseModel):
    """错题更新请求（所有字段均为可选，只更新传入的非 None 字段）"""
    question_text: str | None = Field(None, description="题目文本")
    answer_text: str | None = Field(None, description="答案文本")
    explanation: str | None = Field(None, description="解析/备注")


class MistakeItem(BaseModel):
    """单条错题"""
    mistake_id: str
    subject_code: str
    page: int
    chapter: str
    question_number: int
    question_text: str = ""
    answer_text: str = ""
    explanation: str = ""
    added_at: str = ""


class MistakeListResponse(BaseModel):
    """错题列表响应"""
    mistakes: list[MistakeItem]
    total: int = 0


class MistakeAddResponse(BaseModel):
    """错题添加响应"""
    added: int
    mistakes: list[MistakeItem]


class WordGenerateRequest(BaseModel):
    """Word 生成请求"""
    mistake_ids: list[str] = Field(..., description="要导出的错题 ID 列表")


class WordGenerateResponse(BaseModel):
    """Word 生成响应"""
    filename: str
    download_url: str
