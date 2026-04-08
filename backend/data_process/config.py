"""
408 教材数据预处理配置文件
"""

import os
from pathlib import Path

# ============ 基础路径配置 ============
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = Path(__file__).parent / "processed"
TEMP_DIR = Path("/tmp/408_ocr")

# ============ 处理参数配置 ============
CONFIG = {
    # PDF 转图片参数
    'dpi': 300,
    'fmt': "png",
    'thread_count': 4,
    
    # 水印裁剪参数（相对于图片高度的比例）
    'watermark_crop_top': 0.08,      # 去除顶部 8%
    'watermark_crop_bottom': 0.95,   # 保留到 95%，去除底部 5%
    
    # OCR 参数
    'ocr_lang': 'ch',
    'use_gpu': False,
    'min_confidence': 0.8,
    
    # Chunk 切分参数
    'max_chunk_tokens': 3000,
    'min_chunk_tokens': 200,
    
    # 内容检测参数
    'code_score_threshold': 3,
}

# ============ 科目映射 ============
SUBJECTS = {
    '数据结构': 'ds',
    '操作系统': 'os',
    '计算机组成原理': 'co',
    '计算机网络': 'cn'
}

SUBJECT_CODES = {
    'ds': '数据结构',
    'os': '操作系统',
    'co': '计算机组成原理',
    'cn': '计算机网络'
}

# ============ PDF 文件列表 ============
PDF_FILES = [
    ('2026数据结构_带书签【公众号：研料库，料最全】.pdf', '数据结构'),
    ('2026操作系统_带书签【公众号：研料库，料最全】.pdf', '操作系统'),
    ('2026计算机组成原理_带书签【公众号：研料库，料最全】.pdf', '计算机组成原理'),
    ('2026计算机网络_带书签【公众号：研料库，料最全】.pdf', '计算机网络'),
]

# ============ 代码检测模式 ============
CODE_PATTERNS = [
    (r'#include', 3),
    (r'struct\s+\w+', 2),
    (r'int\s+main\s*\(', 3),
    (r'void\s+\w+\s*\(', 2),
    (r'return\s+\d+', 1),
    (r'\{\s*$', 1),
    (r'^\s+\w+', 1),  # 缩进行
]

CODE_LINE_PATTERNS = [
    r'^\s*(struct|int|void|char|float|double|bool|return|if|for|while|#include|#define|typedef)',
    r'^\s*\{',
    r'^\s*\}',
    r'^\s*//',
    r'^\s*\*',
    r'^\s*\w+\s*\(',
]

# ============ 内容类型检测模式 ============
CONTENT_TYPE_PATTERNS = {
    'summary': [
        r'^(\d+\.\d+\.\d+\s+)?(本节小结|本章小结|总结)',
    ],
    'exercise': [
        r'^(\d+\.\d+\.\d+\s+)?(本节习题|习题精选|练习题)',
    ],
    'answer': [
        r'答案与解析|参考答案|【答案】',
    ],
}

# ============ 水印清理模式 ============
WATERMARK_PATTERNS = [
    r'后续课程更新.*QQ群:\d+',
    r'公众号.*料最全',
    r'研料库',
]

# ============ 中文数字映射 ============
CHINESE_NUMBERS = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
}


def ensure_directories():
    """确保输出目录和临时目录存在"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def get_pdf_path(filename: str) -> Path:
    """获取 PDF 文件的完整路径"""
    return DATA_DIR / filename


def get_output_path(subject_code: str, suffix: str = "chunks.json") -> Path:
    """获取输出文件的完整路径"""
    return OUTPUT_DIR / f"{subject_code}_{suffix}"
