"""
408 教材数据预处理工具函数模块
"""

import re
from typing import List, Dict, Optional, Tuple

from .config import CHINESE_NUMBERS, CODE_PATTERNS, CODE_LINE_PATTERNS, CONTENT_TYPE_PATTERNS


# ============ 书签解析工具 ============

def extract_chapter_number(title: str) -> Optional[str]:
    """提取章编号，如 '第3章 内存管理' -> '3'"""
    match = re.search(r'第([一二三四五六七八九十\d]+)章', title)
    if match:
        num = match.group(1)
        return str(CHINESE_NUMBERS.get(num, num))
    return None


def extract_chapter_title(title: str) -> str:
    """提取章标题，如 '第3章 内存管理' -> '内存管理'"""
    match = re.search(r'第[一二三四五六七八九十\d]+章\s+(.+)', title)
    return match.group(1) if match else title


def extract_section_number(title: str) -> Optional[str]:
    """提取节编号，如 '3.2 虚拟内存' -> '3.2'"""
    match = re.match(r'^(\d+\.\d+)', title)
    return match.group(1) if match else None


def extract_section_title(title: str) -> str:
    """提取节标题，如 '3.2 虚拟内存' -> '虚拟内存'"""
    match = re.match(r'^\d+\.\d+\s+(.+)', title)
    return match.group(1) if match else title


def extract_subsection_number(title: str) -> Optional[str]:
    """提取小节编号，如 '3.2.10 本节小结' -> '3.2.10'"""
    match = re.match(r'^(\d+\.\d+\.\d+)', title)
    return match.group(1) if match else None


def extract_subsection_title(title: str) -> str:
    """提取小节标题，如 '3.2.10 本节小结' -> '本节小结'"""
    match = re.match(r'^\d+\.\d+\.\d+\s+(.+)', title)
    return match.group(1) if match else title


def determine_bookmark_level(title: str) -> int:
    """
    确定书签层级
    
    Level 0: 章 (如 "第3章 内存管理")
    Level 1: 节 (如 "3.2 虚拟内存")
    Level 2: 小节 (如 "3.2.10 本节小结")
    """
    if re.match(r'^第[一二三四五六七八九十\d]+章', title):
        return 0
    elif re.match(r'^\d+\.\d+\s+', title) and not re.match(r'^\d+\.\d+\.\d+', title):
        return 1
    else:
        return 2


# ============ 文本清洗工具 ============

def clean_text(raw_text: str) -> str:
    """
    清洗 OCR 结果
    
    Args:
        raw_text: OCR 原始输出
    
    Returns:
        str: 清洗后的文本
    """
    # 去除页眉残留广告
    text = re.sub(r'后续课程更新.*QQ群:\d+', '', raw_text)
    text = re.sub(r'公众号.*料最全', '', text)
    text = re.sub(r'研料库', '', text)
    
    # 去除单独的数字行（页码）
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    
    # 修复多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 去除行首行尾空格，但保留代码缩进
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # 检测代码特征（保留缩进）
        if is_code_line(line):
            cleaned_lines.append(line.rstrip())  # 保留左侧缩进
        else:
            cleaned_lines.append(line.strip())
    
    return '\n'.join(cleaned_lines)


def is_code_line(line: str) -> bool:
    """检测是否为代码行"""
    return any(re.search(pattern, line) for pattern in CODE_LINE_PATTERNS)


# ============ Token 估算工具 ============

def estimate_tokens(text: str) -> int:
    """估算 token 数（中文约 1 字符 = 0.5 token）"""
    return len(text) // 2


# ============ 内容类型检测工具 ============

def detect_content_type(text: str) -> str:
    """
    检测内容类型
    
    Args:
        text: chunk 文本内容
    
    Returns:
        str: 内容类型标记 (concept/code/table/exercise/answer/summary)
    """
    # 检测总结
    for pattern in CONTENT_TYPE_PATTERNS['summary']:
        if re.search(pattern, text[:100]):
            return 'summary'
    
    # 检测习题
    for pattern in CONTENT_TYPE_PATTERNS['exercise']:
        if re.search(pattern, text[:100]):
            return 'exercise'
    
    # 检测答案
    for pattern in CONTENT_TYPE_PATTERNS['answer']:
        if re.search(pattern, text[:200]):
            return 'answer'
    
    # 检测代码
    code_score = sum(score for pattern, score in CODE_PATTERNS if re.search(pattern, text))
    if code_score >= 3:
        return 'code'
    
    # 检测表格
    if '|' in text or '表' in text[:100] or has_table_structure(text):
        return 'table'
    
    # 默认概念讲解
    return 'concept'


def has_table_structure(text: str) -> bool:
    """检测是否有表格结构"""
    lines = text.split('\n')
    # 检测多行对齐的空格或制表符
    aligned_lines = 0
    for i in range(len(lines) - 1):
        if len(lines[i]) > 10 and len(lines[i+1]) > 10:
            # 简单检测：两行长度相近
            if abs(len(lines[i]) - len(lines[i+1])) < 5:
                aligned_lines += 1
    return aligned_lines >= 3


def would_split_code_block(prev_text: str, next_text: str) -> bool:
    """检测是否会在代码块中间切分"""
    code_patterns = [r'\{$', r'\($', r',$', r';$', r'\\$']
    is_prev_code = any(re.search(p, prev_text.rstrip()) for p in code_patterns)
    is_next_code = is_code_line(next_text)
    return is_prev_code and is_next_code


# ============ 关键词提取工具 ============

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    简单关键词提取（基于词频）
    
    Args:
        text: 文本内容
        max_keywords: 最大关键词数量
    
    Returns:
        List[str]: 关键词列表
    """
    # 简单的关键词提取：提取长度适中的中文字符串
    # 实际应用中可以使用更复杂的 NLP 方法
    words = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
    
    # 统计词频
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # 过滤常见停用词
    stop_words = {'本书', '本节', '本章', '如图', '所示', '可以', '进行', '通过', '使用'}
    for sw in stop_words:
        word_freq.pop(sw, None)
    
    # 返回高频词
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:max_keywords]]


# ============ Chunk 元数据工具 ============

def enrich_chunk_metadata(chunk: Dict) -> Dict:
    """
    丰富 chunk 元数据
    
    Args:
        chunk: 原始 chunk 字典
    
    Returns:
        Dict: 添加元数据后的 chunk
    """
    content = chunk['content']
    
    # 检测内容类型
    chunk['content_type'] = detect_content_type(content)
    
    # 检测代码
    chunk['has_code'] = chunk['content_type'] == 'code' or bool(
        re.search(r'(struct|int main|void \w+\(|#include)', content)
    )
    
    # 检测表格
    chunk['has_table'] = chunk['content_type'] == 'table'
    
    # 检测图片引用
    chunk['has_image_ref'] = bool(
        re.search(r'如图\s*\d+[-.]\d+|见图\s*\d+', content)
    )
    
    # 提取关键词
    chunk['keywords'] = extract_keywords(content)
    
    # 提取公式（简单检测）
    chunk['has_formula'] = bool(re.search(r'[\^_]|\w+\d+', content))
    
    # 估算 token
    chunk['token_count'] = estimate_tokens(content)
    
    return chunk


# ============ 统计工具 ============

def generate_stats(chunks: List[Dict], subject_name: str) -> Dict:
    """
    生成统计信息
    
    Args:
        chunks: chunk 列表
        subject_name: 科目名称
    
    Returns:
        Dict: 统计信息
    """
    tokens = [c.get('token_count', 0) for c in chunks]
    
    # 统计内容类型
    types = {}
    for c in chunks:
        t = c.get('content_type', 'unknown')
        types[t] = types.get(t, 0) + 1
    
    # 统计特征
    features = {
        'has_code': sum(1 for c in chunks if c.get('has_code')),
        'has_table': sum(1 for c in chunks if c.get('has_table')),
        'has_image_ref': sum(1 for c in chunks if c.get('has_image_ref')),
        'has_formula': sum(1 for c in chunks if c.get('has_formula')),
    }
    
    return {
        'subject': subject_name,
        'total_chunks': len(chunks),
        'avg_tokens': sum(tokens) // len(tokens) if tokens else 0,
        'min_tokens': min(tokens) if tokens else 0,
        'max_tokens': max(tokens) if tokens else 0,
        'content_types': types,
        'features': features,
    }
