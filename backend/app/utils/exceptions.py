"""
自定义异常与错误码定义

异常层次:
  AppError (基类)
  ├── InputFormatError     (4001) - 输入格式错误
  ├── QuestionNotFoundError(4002) - 题目不存在
  ├── UnsupportedFileError (4003) - 文件格式不支持
  ├── OCRError             (5001) - OCR 识别失败
  ├── VectorSearchError    (5002) - 向量检索失败
  ├── LLMError             (5003) - LLM 调用失败
  └── GraphError           (5004) - 图谱操作失败
"""


class AppError(Exception):
    """
    基础应用异常 - 所有自定义异常的父类。

    Attributes:
        code: 错误码（4xxx 客户端错误, 5xxx 服务端错误）
        message: 用户可见的错误消息
        detail: 内部调试信息（仅写入日志，不返回给前端）
    """

    def __init__(self, code: int, message: str, detail: str | None = None):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(f"[{code}] {message}")


# ──────────── 4xxx 客户端错误 ────────────


class InputFormatError(AppError):
    """4001 - 输入格式错误"""

    def __init__(self, message: str = "输入格式错误", detail: str | None = None):
        super().__init__(4001, message, detail)


class QuestionNotFoundError(AppError):
    """4002 - 题目不存在"""

    def __init__(self, message: str = "题目不存在", detail: str | None = None):
        super().__init__(4002, message, detail)


class UnsupportedFileError(AppError):
    """4003 - 文件格式不支持"""

    def __init__(self, message: str = "文件格式不支持", detail: str | None = None):
        super().__init__(4003, message, detail)


# ──────────── 5xxx 服务端错误 ────────────


class OCRError(AppError):
    """5001 - OCR 识别失败"""

    def __init__(self, message: str = "OCR 识别失败", detail: str | None = None):
        super().__init__(5001, message, detail)


class VectorSearchError(AppError):
    """5002 - 向量检索失败"""

    def __init__(self, message: str = "向量检索失败", detail: str | None = None):
        super().__init__(5002, message, detail)


class LLMError(AppError):
    """5003 - LLM 调用失败"""

    def __init__(self, message: str = "LLM 调用失败", detail: str | None = None):
        super().__init__(5003, message, detail)


class GraphError(AppError):
    """5004 - 知识图谱操作失败"""

    def __init__(self, message: str = "知识图谱操作失败", detail: str | None = None):
        super().__init__(5004, message, detail)
