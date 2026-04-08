"""
408 教材数据预处理模块

基于书签层级的智能 chunk 切分
"""

from .pdf_processor import PDFProcessor
from .config import CONFIG, SUBJECTS, PDF_FILES
from .utils import (
    clean_text,
    detect_content_type,
    enrich_chunk_metadata,
    generate_stats,
)

__all__ = [
    'PDFProcessor',
    'CONFIG',
    'SUBJECTS',
    'PDF_FILES',
    'clean_text',
    'detect_content_type',
    'enrich_chunk_metadata',
    'generate_stats',
]
