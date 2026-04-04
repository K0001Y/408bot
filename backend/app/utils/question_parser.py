"""
题号解析与内容提取工具

从整个小节 chunk 内容中，根据题号精确提取单道题目或答案。

支持格式:
- 01．对特殊矩阵采用压缩存储...  (零填充 + 全角句号)
- 06.B                            (零填充 + 半角句号)
- 12.【2017统考真题】              (无零填充)
- 02. C                           (句号后有空格)
"""

import re
from typing import Optional

# 匹配行首题号标记:
#   (?:^|\n)  - 行首或换行后
#   \s*       - 可选前导空白
#   0?        - 可选零填充
#   (\d{1,2}) - 1~2 位数字 (捕获组)
#   \s*       - 可选空白
#   [.．]     - 半角或全角句号
#   (?!\d)    - 后面不是数字 (避免匹配 "3.4" 这种小节号)
_ITEM_PATTERN = re.compile(r"(?:^|\n)\s*0?(\d{1,2})\s*[.．](?!\d)")


def find_numbered_items(content: str) -> list[tuple[int, int, int]]:
    """
    扫描内容中所有带编号的条目。

    Returns:
        [(题号, 起始位置, 结束位置), ...] — 按出现顺序排列，
        结束位置为下一条目的起始位置或内容末尾。
    """
    matches = []
    for m in _ITEM_PATTERN.finditer(content):
        number = int(m.group(1))
        # 起始位置：跳过匹配到的换行符
        start = m.start()
        if content[start] == "\n":
            start += 1
        matches.append((number, start))

    items = []
    for i, (number, start) in enumerate(matches):
        end = matches[i + 1][1] if i + 1 < len(matches) else len(content)
        items.append((number, start, end))

    return items


def _extract_by_number(content: str, number: int) -> str:
    """从内容中提取指定编号的条目文本。"""
    items = find_numbered_items(content)
    for item_num, start, end in items:
        if item_num == number:
            return content[start:end].strip()
    return ""


def extract_question_by_number(content: str, number: int) -> str:
    """
    从习题 chunk 内容中提取指定题号的题目文本。

    Args:
        content: 整个习题小节的内容 (如 "3.4.5 本节试题精选" chunk)
        number: 题号 (如 6)

    Returns:
        该题的完整文本，未找到返回空字符串。
    """
    return _extract_by_number(content, number)


def extract_answer_by_number(content: str, number: int) -> str:
    """
    从答案 chunk 内容中提取指定题号的答案文本。

    Args:
        content: 整个答案小节的内容 (如 "3.4.6 答案与解析" chunk)
        number: 题号 (如 6)

    Returns:
        该题的答案文本，未找到返回空字符串。
    """
    return _extract_by_number(content, number)
