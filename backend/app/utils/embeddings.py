"""
BGE Embedding 封装模块

提供统一的 embedding 接口，供数据导入脚本和运行时 Skills 共用。
使用 BAAI/bge-large-zh-v1.5 模型，支持 ChromaDB EmbeddingFunction 协议。

注意:
- BGE 模型查询时需加前缀以获得最佳检索效果
- 文档编码不加前缀
"""

import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger("embeddings")

# BGE 查询前缀（官方推荐，用于检索场景）
BGE_QUERY_PREFIX = "为这个句子生成表示以用于检索中文文档: "


class BGEEmbeddingFunction:
    """
    BGE Embedding 函数 - 实现 ChromaDB EmbeddingFunction 协议。

    供 ChromaDB collection 直接使用，自动处理查询前缀。
    """

    def __init__(self, model: Optional[object] = None):
        """
        Args:
            model: SentenceTransformer 模型实例，如为 None 则自动加载
        """
        self._model = model

    @property
    def model(self):
        if self._model is None:
            self._model = load_sentence_transformer()
        return self._model

    def name(self) -> str:
        """ChromaDB 要求的 name 方法，用于标识 embedding 函数"""
        return "bge-large-zh-v1.5"

    def __call__(self, input: list[str]) -> list[list[float]]:
        """ChromaDB EmbeddingFunction 协议要求的 __call__ 方法"""
        embeddings = self.model.encode(
            input,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()


def load_sentence_transformer():
    """
    加载 SentenceTransformer 模型。

    Returns:
        SentenceTransformer 实例

    Raises:
        RuntimeError: 模型加载失败
    """
    settings = get_settings()
    model_name = settings.embedding.model_name
    device = settings.embedding.device

    if device == "auto":
        device = _detect_device()

    logger.info("加载 SentenceTransformer model=%s device=%s", model_name, device)

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name, device=device)
        logger.info("SentenceTransformer 加载成功 model=%s device=%s", model_name, device)
        return model
    except Exception as e:
        logger.critical("SentenceTransformer 加载失败 error=%s", str(e), exc_info=True)
        raise RuntimeError(f"Embedding 模型加载失败: {e}")


def _get_raw_model(model):
    """
    从模型实例中获取底层 SentenceTransformer。

    支持:
    - SentenceTransformer 直接实例
    - HuggingFaceEmbeddings（LangChain 包装器，底层模型在 .client 属性）
    """
    if hasattr(model, "encode"):
        # 原生 SentenceTransformer
        return model
    if hasattr(model, "client") and hasattr(model.client, "encode"):
        # LangChain HuggingFaceEmbeddings 包装器
        return model.client
    raise TypeError(
        f"不支持的 Embedding 模型类型: {type(model).__name__}。"
        "需要 SentenceTransformer 或 HuggingFaceEmbeddings 实例"
    )


def encode_documents(model, texts: list[str]) -> list[list[float]]:
    """
    编码文档文本（不加查询前缀）。

    Args:
        model: SentenceTransformer 或 HuggingFaceEmbeddings 实例
        texts: 文本列表

    Returns:
        embedding 向量列表
    """
    raw = _get_raw_model(model)
    embeddings = raw.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 10,
        batch_size=32,
    )
    return embeddings.tolist()


def encode_query(model, query: str) -> list[float]:
    """
    编码查询文本（加 BGE 查询前缀）。

    Args:
        model: SentenceTransformer 或 HuggingFaceEmbeddings 实例
        query: 查询文本

    Returns:
        embedding 向量
    """
    raw = _get_raw_model(model)
    prefixed_query = BGE_QUERY_PREFIX + query
    embedding = raw.encode(
        [prefixed_query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embedding[0].tolist()


def _detect_device() -> str:
    """自动检测最佳计算设备"""
    import platform
    system = platform.system()
    machine = platform.machine()

    if system == "Darwin" and machine == "arm64":
        try:
            import torch
            if torch.backends.mps.is_available():
                return "mps"
        except (ImportError, AttributeError):
            pass

    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass

    return "cpu"
