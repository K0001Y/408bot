# 408考研教材数据预处理方案

## 1. 概述

### 1.1 目标
将扫描版 PDF 教材转换为结构化的文本数据，用于构建 RAG 知识库。核心原则是**保持知识点的完整性**，确保每个小节（如 3.2.10）的内容不被拆分到不同 chunk 中。

### 1.2 输入数据
- 4 本扫描版 PDF 教材（数据结构、操作系统、计算机组成原理、计算机网络）
- 共 1444 页（DS: 412, OS: 372, CO: 348, CN: 312）
- 每页包含固定水印：页眉广告文字
- **PDF 包含详细书签**：章 → 节 → 小节（三级层级）

### 1.3 输出数据
- 结构化 JSON 文件，按小节（subsection）组织 chunks
- 章节索引映射表
- 知识点标签映射表
- 内容类型标记（概念/代码/表格/习题/总结）

---

## 2. 技术方案

### 2.1 整体流程

```
PDF 文件
    ↓
[Step 1] 提取详细书签（三级层级）
    ↓
[Step 2] PDF 转图片 (pdf2image)
    ↓
[Step 3] 去水印处理 (PIL/OpenCV)
    ↓
[Step 4] OCR 文字识别 (PaddleOCR)
    ↓
[Step 5] 文本清洗与格式化
    ↓
[Step 6] 按书签合并页面 → 生成 chunks
    ↓
[Step 7] 智能切分（处理过长内容）
    ↓
[Step 8] 内容类型检测与标记
    ↓
结构化数据输出
```

---

### 2.2 各步骤详细说明

#### Step 1: 提取详细书签（三级层级）

**目标**：利用 PDF 书签获取精确的章节层级和页码范围

**书签层级结构**：
```
第3章 内存管理                    ← Level 0 (章)
├── 3.1 内存管理概念              ← Level 1 (节)
├── 3.2 虚拟内存                  ← Level 1 (节)
│   ├── 3.2.1 虚拟内存基本概念    ← Level 2 (小节) → Chunk
│   ├── 3.2.2 请求分页管理方式    ← Level 2 (小节) → Chunk
│   ├── 3.2.3 页框分配            ← Level 2 (小节) → Chunk
│   ├── 3.2.4 页面置换算法        ← Level 2 (小节) → Chunk
│   ├── 3.2.10 本节小结           ← Level 2 (小节) → Chunk
│   └── 3.2.11 本节习题精选       ← Level 2 (小节) → Chunk
└── 3.3 本章疑难点                ← Level 1 (节)
```

**代码实现**：
```python
import re
from pypdf import PdfReader

def extract_detailed_bookmarks(pdf_path, subject_code):
    """
    提取三级书签结构
    
    Returns:
        List[Dict]: 书签列表，每个包含 title, page, level, subsection 等
    """
    reader = PdfReader(pdf_path)
    outlines = reader.outline
    
    bookmarks = []
    current_chapter = None
    current_section = None
    
    def parse_outline(items, level=0):
        nonlocal current_chapter, current_section
        
        for item in items:
            if isinstance(item, list):
                parse_outline(item, level + 1)
            else:
                try:
                    page_num = reader.get_destination_page_number(item) + 1
                    title = item.title.strip()
                    
                    # 识别层级
                    if re.match(r'^第[一二三四五六七八九十\d]+章', title):
                        # Level 0: 章
                        current_chapter = {
                            'number': extract_chapter_number(title),
                            'title': extract_chapter_title(title)
                        }
                        bm_level = 0
                        
                    elif re.match(r'^\d+\.\d+\s+', title) and not re.match(r'^\d+\.\d+\.\d+', title):
                        # Level 1: 节 (如 "3.2 虚拟内存")
                        current_section = {
                            'number': extract_section_number(title),
                            'title': extract_section_title(title)
                        }
                        bm_level = 1
                        
                    else:
                        # Level 2: 小节 (如 "3.2.10 本节小结")
                        bm_level = 2
                    
                    bm = {
                        'title': title,
                        'page': page_num,
                        'level': bm_level,
                        'chapter': current_chapter.copy() if current_chapter else None,
                        'section': current_section.copy() if current_section else None,
                        'subsection': extract_subsection_number(title) if bm_level == 2 else None,
                        'subsection_title': extract_subsection_title(title) if bm_level == 2 else None,
                        'subject_code': subject_code
                    }
                    
                    bookmarks.append(bm)
                    
                except Exception as e:
                    print(f"解析书签失败: {e}, title: {item.title}")
    
    parse_outline(outlines)
    return bookmarks


def extract_chapter_number(title):
    """提取章编号，如 '第3章 内存管理' -> '3'"""
    match = re.search(r'第([一二三四五六七八九十\d]+)章', title)
    if match:
        num = match.group(1)
        chinese_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                       '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
        return str(chinese_nums.get(num, num))
    return None

def extract_chapter_title(title):
    """提取章标题，如 '第3章 内存管理' -> '内存管理'"""
    match = re.search(r'第[一二三四五六七八九十\d]+章\s+(.+)', title)
    return match.group(1) if match else title

def extract_section_number(title):
    """提取节编号，如 '3.2 虚拟内存' -> '3.2'"""
    match = re.match(r'^(\d+\.\d+)', title)
    return match.group(1) if match else None

def extract_section_title(title):
    """提取节标题，如 '3.2 虚拟内存' -> '虚拟内存'"""
    match = re.match(r'^\d+\.\d+\s+(.+)', title)
    return match.group(1) if match else title

def extract_subsection_number(title):
    """提取小节编号，如 '3.2.10 本节小结' -> '3.2.10'"""
    match = re.match(r'^(\d+\.\d+\.\d+)', title)
    return match.group(1) if match else None

def extract_subsection_title(title):
    """提取小节标题，如 '3.2.10 本节小结' -> '本节小结'"""
    match = re.match(r'^\d+\.\d+\.\d+\s+(.+)', title)
    return match.group(1) if match else title
```

---

#### Step 2: PDF 转图片

**工具**: `pdf2image` (基于 poppler)

**配置参数**:
| 参数 | 值 | 说明 |
|------|-----|------|
| dpi | 300 | 保证 OCR 识别精度 |
| fmt | "png" | 无损格式 |
| thread_count | 4 | 并行处理加速 |

**代码示例**:
```python
from pdf2image import convert_from_path

def pdf_to_images(pdf_path):
    """将 PDF 转换为图片列表"""
    images = convert_from_path(
        pdf_path,
        dpi=300,
        fmt="png",
        thread_count=4
    )
    return images
```

---

#### Step 3: 去水印处理

**分析**: 教材水印特点
- 位置：固定页眉（顶部约 5-8% 区域）
- 内容："后续课程更新+微信:1003019 每日同步QQ群:618427351"
- 形式：纯文字，无半透明斜向水印

**方案**: 裁剪法（最简单有效）

```python
from PIL import Image

def remove_watermark(image):
    """
    裁剪去除页眉页脚水印
    
    Args:
        image: PIL Image 对象
    
    Returns:
        裁剪后的 Image 对象
    """
    width, height = image.size
    
    # 裁剪参数（根据实际水印位置调整）
    top_crop = int(height * 0.08)      # 去除顶部 8%
    bottom_crop = int(height * 0.95)   # 保留到 95%，去除底部 5%
    
    # 裁剪中间区域
    cropped = image.crop((
        0,           # left
        top_crop,    # top
        width,       # right
        bottom_crop  # bottom
    ))
    
    return cropped
```

---

#### Step 4: OCR 文字识别

**推荐工具**: `PaddleOCR`

**优势**:
- 中文识别准确率高
- 支持版面分析（自动识别文字区域）
- 支持表格识别
- 支持 GPU 加速

**安装**:
```bash
pip install paddlepaddle paddleocr
```

**使用示例**:
```python
from paddleocr import PaddleOCR

class OCREngine:
    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=True,           # 方向分类
            lang='ch',                    # 中文
            use_gpu=False,                # CPU 运行（如无 GPU）
            show_log=False
        )
    
    def recognize(self, image_path):
        """
        识别单张图片
        
        Returns:
            str: 识别的文字内容
        """
        result = self.ocr.ocr(image_path, cls=True)
        
        texts = []
        if result[0]:
            for line in result[0]:
                text = line[1][0]          # 文字内容
                confidence = line[1][1]     # 置信度
                if confidence > 0.8:        # 过滤低置信度结果
                    texts.append(text)
        
        return "\n".join(texts)
```

---

#### Step 5: 文本清洗与格式化

**清洗规则**:

| 问题 | 处理方法 |
|------|----------|
| 多余空格 | 合并连续空格，但保留代码缩进 |
| 换行符混乱 | 按段落重新分段 |
| 页码识别错误 | 正则过滤纯数字行 |
| 特殊字符 | 统一替换为标准字符 |
| 代码块格式 | 识别缩进保留格式 |
| 水印残留 | 删除广告关键词 |

**代码示例**:
```python
import re

def clean_text(raw_text):
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
    
    # 去除单独的数字行（页码）
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    
    # 修复多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 去除行首行尾空格
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # 检测代码特征（保留缩进）
        if is_code_line(line):
            cleaned_lines.append(line.rstrip())  # 保留左侧缩进
        else:
            cleaned_lines.append(line.strip())
    
    return '\n'.join(cleaned_lines)


def is_code_line(line):
    """检测是否为代码行"""
    code_indicators = [
        r'^\s*(struct|int|void|char|float|double|bool|return|if|for|while|#include|#define|typedef)',
        r'^\s*\{',
        r'^\s*\}',
        r'^\s*//',
        r'^\s*\*',
        r'^\s*\w+\s*\(',
    ]
    return any(re.search(pattern, line) for pattern in code_indicators)
```

---

#### Step 6: 按书签合并页面 → 生成 Chunks

**核心逻辑**：根据 Level 2 书签（小节）合并跨页内容

```python
def create_chunks_by_bookmarks(pages_text, bookmarks):
    """
    根据书签将页面合并为 chunks
    
    Args:
        pages_text: List[str]，每页的 OCR 文本
        bookmarks: List[Dict]，书签列表
    
    Returns:
        List[Dict]: chunks 列表
    """
    chunks = []
    
    # 只处理 Level 2 书签（小节）
    subsection_bookmarks = [bm for bm in bookmarks if bm['level'] == 2]
    
    for i, bm in enumerate(subsection_bookmarks):
        # 确定页码范围
        start_page = bm['page']
        
        # 找到下一个小节的起始页
        if i + 1 < len(subsection_bookmarks):
            end_page = subsection_bookmarks[i + 1]['page'] - 1
        else:
            end_page = len(pages_text)
        
        # 合并页面内容
        content_parts = []
        for page_num in range(start_page, min(end_page + 1, len(pages_text) + 1)):
            page_idx = page_num - 1  # 转换为 0-based
            if 0 <= page_idx < len(pages_text):
                content_parts.append(pages_text[page_idx])
        
        full_content = '\n'.join(content_parts)
        
        # 创建 chunk
        chunk = {
            'chunk_id': f"{bm['subject_code']}_{bm['subsection']}",
            'subject_code': bm['subject_code'],
            'chapter_number': bm['chapter']['number'] if bm['chapter'] else None,
            'chapter_title': bm['chapter']['title'] if bm['chapter'] else None,
            'section_number': bm['section']['number'] if bm['section'] else None,
            'section_title': bm['section']['title'] if bm['section'] else None,
            'subsection': bm['subsection'],
            'subsection_title': bm['subsection_title'],
            'page_start': start_page,
            'page_end': end_page,
            'content': full_content,
            'char_count': len(full_content),
        }
        
        chunks.append(chunk)
    
    return chunks
```

---

#### Step 7: 智能切分（处理过长内容）

**策略**：
- 如果小节内容 > 3000 tokens，按自然段落切分
- 如果小节内容 < 200 tokens，与下一个小节合并
- 代码块、表格不跨 chunk 切分

```python
def smart_split_chunks(chunks, max_tokens=3000, min_tokens=200):
    """
    智能切分 chunks
    
    Args:
        chunks: List[Dict]，原始 chunks
        max_tokens: 最大 token 数
        min_tokens: 最小 token 数（低于此值则合并）
    
    Returns:
        List[Dict]: 处理后的 chunks
    """
    result = []
    pending_small = None
    
    for chunk in chunks:
        tokens = estimate_tokens(chunk['content'])
        
        # 处理过小 chunk：暂存，尝试与下一个合并
        if tokens < min_tokens:
            if pending_small:
                # 合并到前一个待处理 chunk
                pending_small['content'] += '\n\n' + chunk['content']
                pending_small['char_count'] = len(pending_small['content'])
                pending_small['page_end'] = chunk['page_end']
                # 更新 subsection 为组合标识
                pending_small['subsection'] += f",{chunk['subsection']}"
            else:
                pending_small = chunk.copy()
            continue
        
        # 如果有待处理的小 chunk，先处理它
        if pending_small:
            result.append(pending_small)
            pending_small = None
        
        # 处理过大 chunk：按段落切分
        if tokens > max_tokens:
            sub_chunks = split_large_chunk(chunk, max_tokens)
            result.extend(sub_chunks)
        else:
            result.append(chunk)
    
    # 处理最后待处理的小 chunk
    if pending_small:
        result.append(pending_small)
    
    return result


def split_large_chunk(chunk, max_tokens):
    """
    将大 chunk 按段落切分
    
    策略：
    1. 按段落分割
    2. 检测代码块边界，不跨代码块切分
    3. 累加段落直到接近 max_tokens
    """
    paragraphs = chunk['content'].split('\n\n')
    
    sub_chunks = []
    current_parts = []
    current_tokens = 0
    part_index = 0
    
    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        
        # 检查是否会在代码块中间切分
        if current_parts and would_split_code_block(current_parts[-1], para):
            # 强制开启新 chunk
            sub_chunk = create_sub_chunk(chunk, current_parts, part_index)
            sub_chunks.append(sub_chunk)
            
            current_parts = [para]
            current_tokens = para_tokens
            part_index += 1
        
        # 正常累加
        elif current_tokens + para_tokens > max_tokens and current_parts:
            # 保存当前 sub-chunk
            sub_chunk = create_sub_chunk(chunk, current_parts, part_index)
            sub_chunks.append(sub_chunk)
            
            # 重置
            current_parts = [para]
            current_tokens = para_tokens
            part_index += 1
        else:
            current_parts.append(para)
            current_tokens += para_tokens
    
    # 保存最后一个
    if current_parts:
        sub_chunk = create_sub_chunk(chunk, current_parts, part_index)
        sub_chunks.append(sub_chunk)
    
    return sub_chunks


def would_split_code_block(prev_text, next_text):
    """检测是否会在代码块中间切分"""
    # 如果前一段以代码特征结尾，且后一段也是代码
    code_patterns = [r'\{$', r'\($', r',$', r';$', r'\\$']
    is_prev_code = any(re.search(p, prev_text.rstrip()) for p in code_patterns)
    is_next_code = is_code_line(next_text)
    return is_prev_code and is_next_code


def create_sub_chunk(original_chunk, parts, part_index):
    """创建子 chunk"""
    return {
        **original_chunk,
        'chunk_id': f"{original_chunk['chunk_id']}_{part_index}",
        'content': '\n\n'.join(parts),
        'char_count': len('\n\n'.join(parts)),
        'is_partial': True,
        'part_index': part_index,
        'total_parts': None  # 后续更新
    }


def estimate_tokens(text):
    """估算 token 数（中文约 1 字符 = 0.5 token）"""
    return len(text) // 2
```

---

#### Step 8: 内容类型检测与标记

**检测类型**：

| 类型 | 识别特征 | 标记值 |
|------|---------|--------|
| 概念讲解 | 正文段落，无特殊标记 | `concept` |
| 代码示例 | 包含代码关键字、缩进 | `code` |
| 表格数据 | 包含表格结构、对齐文本 | `table` |
| 习题 | 包含题号、选项 | `exercise` |
| 答案解析 | 包含"答案"、"解析" | `answer` |
| 总结 | 包含"小结"、"总结" | `summary` |

```python
def detect_content_type(text):
    """
    检测内容类型
    
    Args:
        text: chunk 文本内容
    
    Returns:
        str: 内容类型标记
    """
    # 检测总结
    if re.search(r'^(\d+\.\d+\.\d+\s+)?(本节小结|本章小结|总结)', text[:100]):
        return 'summary'
    
    # 检测习题
    if re.search(r'^(\d+\.\d+\.\d+\s+)?(本节习题|习题精选|练习题)', text[:100]):
        return 'exercise'
    
    # 检测答案
    if re.search(r'答案与解析|参考答案|【答案】', text[:200]):
        return 'answer'
    
    # 检测代码
    code_score = 0
    code_patterns = [
        (r'#include', 3),
        (r'struct\s+\w+', 2),
        (r'int\s+main\s*\(', 3),
        (r'void\s+\w+\s*\(', 2),
        (r'return\s+\d+', 1),
        (r'\{\s*$', 1),
        (r'^\s+\w+', 1),  # 缩进行
    ]
    for pattern, score in code_patterns:
        if re.search(pattern, text):
            code_score += score
    
    if code_score >= 3:
        return 'code'
    
    # 检测表格
    if '|' in text or '表' in text[:100] or has_table_structure(text):
        return 'table'
    
    # 默认概念讲解
    return 'concept'


def has_table_structure(text):
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


def enrich_chunk_metadata(chunk):
    """丰富 chunk 元数据"""
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
    
    return chunk
```

---

## 3. 完整处理脚本

```python
#!/usr/bin/env python3
"""
408 教材数据预处理脚本
基于书签层级的智能 chunk 切分
"""

import os
import json
import re
from pathlib import Path
from tqdm import tqdm

from pdf2image import convert_from_path
from PIL import Image
from paddleocr import PaddleOCR
from pypdf import PdfReader

# ============ 配置 ============
CONFIG = {
    'input_dir': './data',
    'output_dir': './processed',
    'temp_dir': '/tmp/408_ocr',
    'dpi': 300,
    'watermark_crop_top': 0.08,
    'watermark_crop_bottom': 0.95,
    'ocr_lang': 'ch',
    'min_confidence': 0.8,
    'max_chunk_tokens': 3000,
    'min_chunk_tokens': 200,
}

# 科目映射
SUBJECTS = {
    '数据结构': 'ds',
    '操作系统': 'os',
    '计算机组成原理': 'co',
    '计算机网络': 'cn'
}

# ============ 核心类 ============

class PDFProcessor:
    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang=CONFIG['ocr_lang'],
            use_gpu=False,
            show_log=False
        )
        os.makedirs(CONFIG['output_dir'], exist_ok=True)
        os.makedirs(CONFIG['temp_dir'], exist_ok=True)
    
    def process_pdf(self, pdf_path, subject_name):
        """处理单个 PDF 文件"""
        print(f"\n{'='*60}")
        print(f"处理: {subject_name}")
        print('='*60)
        
        subject_code = SUBJECTS.get(subject_name, 'unknown')
        
        # Step 1: 提取书签
        print("[Step 1/8] 提取书签...")
        bookmarks = self._extract_bookmarks(pdf_path, subject_code)
        print(f"  提取到 {len(bookmarks)} 个书签")
        
        # Step 2: PDF 转图片
        print("[Step 2/8] PDF 转图片...")
        images = convert_from_path(
            pdf_path,
            dpi=CONFIG['dpi'],
            fmt="png",
            thread_count=4
        )
        print(f"  共 {len(images)} 页")
        
        # Step 3-5: 处理每一页（去水印 + OCR + 清洗）
        print("[Step 3-5/8] 去水印、OCR、清洗...")
        pages_text = []
        for i, image in enumerate(tqdm(images, desc="  处理页面")):
            # 去水印
            cleaned_image = self._remove_watermark(image)
            
            # 临时保存
            temp_path = os.path.join(CONFIG['temp_dir'], f"{subject_code}_{i:04d}.png")
            cleaned_image.save(temp_path)
            
            # OCR
            text = self._ocr_image(temp_path)
            
            # 清洗
            text = self._clean_text(text)
            
            pages_text.append(text)
            
            # 清理临时文件
            os.remove(temp_path)
        
        # Step 6: 按书签合并页面
        print("[Step 6/8] 按书签合并页面...")
        chunks = self._create_chunks_by_bookmarks(pages_text, bookmarks)
        print(f"  生成 {len(chunks)} 个初始 chunks")
        
        # Step 7: 智能切分
        print("[Step 7/8] 智能切分...")
        chunks = self._smart_split_chunks(chunks)
        print(f"  切分后共 {len(chunks)} 个 chunks")
        
        # Step 8: 内容类型检测
        print("[Step 8/8] 内容类型检测...")
        chunks = [self._enrich_chunk_metadata(chunk) for chunk in tqdm(chunks, desc="  检测")]
        
        # 保存结果
        output_file = os.path.join(
            CONFIG['output_dir'],
            f"{subject_code}_chunks.json"
        )
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        # 生成统计信息
        stats = self._generate_stats(chunks, subject_name)
        print(f"\n  完成! 输出: {output_file}")
        print(f"  统计: {stats['total_chunks']} chunks, "
              f"平均 {stats['avg_tokens']} tokens/chunk")
        
        return chunks, stats
    
    def _extract_bookmarks(self, pdf_path, subject_code):
        """提取三级书签"""
        reader = PdfReader(pdf_path)
        outlines = reader.outline
        
        bookmarks = []
        current_chapter = None
        current_section = None
        
        def parse_outline(items, level=0):
            nonlocal current_chapter, current_section
            
            for item in items:
                if isinstance(item, list):
                    parse_outline(item, level + 1)
                else:
                    try:
                        page_num = reader.get_destination_page_number(item) + 1
                        title = item.title.strip()
                        
                        # 识别层级
                        if re.match(r'^第[一二三四五六七八九十\d]+章', title):
                            current_chapter = {
                                'number': self._extract_chapter_number(title),
                                'title': self._extract_chapter_title(title)
                            }
                            bm_level = 0
                        elif re.match(r'^\d+\.\d+\s+', title) and not re.match(r'^\d+\.\d+\.\d+', title):
                            current_section = {
                                'number': self._extract_section_number(title),
                                'title': self._extract_section_title(title)
                            }
                            bm_level = 1
                        else:
                            bm_level = 2
                        
                        bm = {
                            'title': title,
                            'page': page_num,
                            'level': bm_level,
                            'chapter': current_chapter.copy() if current_chapter else None,
                            'section': current_section.copy() if current_section else None,
                            'subsection': self._extract_subsection_number(title) if bm_level == 2 else None,
                            'subsection_title': self._extract_subsection_title(title) if bm_level == 2 else None,
                            'subject_code': subject_code
                        }
                        bookmarks.append(bm)
                        
                    except Exception as e:
                        print(f"  警告: 解析书签失败 - {e}")
        
        parse_outline(outlines)
        return bookmarks
    
    def _remove_watermark(self, image):
        """去除水印"""
        width, height = image.size
        top = int(height * CONFIG['watermark_crop_top'])
        bottom = int(height * CONFIG['watermark_crop_bottom'])
        return image.crop((0, top, width, bottom))
    
    def _ocr_image(self, image_path):
        """OCR 识别"""
        result = self.ocr.ocr(image_path, cls=True)
        texts = []
        if result[0]:
            for line in result[0]:
                text, confidence = line[1][0], line[1][1]
                if confidence >= CONFIG['min_confidence']:
                    texts.append(text)
        return "\n".join(texts)
    
    def _clean_text(self, text):
        """清洗文本"""
        text = re.sub(r'后续课程更新.*QQ群:\d+', '', text)
        text = re.sub(r'公众号.*料最全', '', text)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def _create_chunks_by_bookmarks(self, pages_text, bookmarks):
        """按书签合并页面"""
        chunks = []
        subsection_bms = [bm for bm in bookmarks if bm['level'] == 2]
        
        for i, bm in enumerate(subsection_bms):
            start_page = bm['page']
            if i + 1 < len(subsection_bms):
                end_page = subsection_bms[i + 1]['page'] - 1
            else:
                end_page = len(pages_text)
            
            content_parts = []
            for page_num in range(start_page, min(end_page + 1, len(pages_text) + 1)):
                page_idx = page_num - 1
                if 0 <= page_idx < len(pages_text):
                    content_parts.append(pages_text[page_idx])
            
            chunk = {
                'chunk_id': f"{bm['subject_code']}_{bm['subsection']}",
                'subject_code': bm['subject_code'],
                'chapter_number': bm['chapter']['number'] if bm['chapter'] else None,
                'chapter_title': bm['chapter']['title'] if bm['chapter'] else None,
                'section_number': bm['section']['number'] if bm['section'] else None,
                'section_title': bm['section']['title'] if bm['section'] else None,
                'subsection': bm['subsection'],
                'subsection_title': bm['subsection_title'],
                'page_start': start_page,
                'page_end': end_page,
                'content': '\n'.join(content_parts),
                'char_count': len('\n'.join(content_parts)),
            }
            chunks.append(chunk)
        
        return chunks
    
    def _smart_split_chunks(self, chunks):
        """智能切分"""
        result = []
        pending_small = None
        
        for chunk in chunks:
            tokens = chunk['char_count'] // 2
            
            if tokens < CONFIG['min_chunk_tokens']:
                if pending_small:
                    pending_small['content'] += '\n\n' + chunk['content']
                    pending_small['char_count'] = len(pending_small['content'])
                    pending_small['page_end'] = chunk['page_end']
                    pending_small['subsection'] += f",{chunk['subsection']}"
                else:
                    pending_small = chunk.copy()
                continue
            
            if pending_small:
                result.append(pending_small)
                pending_small = None
            
            if tokens > CONFIG['max_chunk_tokens']:
                sub_chunks = self._split_large_chunk(chunk)
                result.extend(sub_chunks)
            else:
                result.append(chunk)
        
        if pending_small:
            result.append(pending_small)
        
        return result
    
    def _split_large_chunk(self, chunk):
        """切分大 chunk"""
        paragraphs = chunk['content'].split('\n\n')
        sub_chunks = []
        current_parts = []
        current_tokens = 0
        part_index = 0
        
        for para in paragraphs:
            para_tokens = len(para) // 2
            
            if current_tokens + para_tokens > CONFIG['max_chunk_tokens'] and current_parts:
                sub_chunk = {
                    **chunk,
                    'chunk_id': f"{chunk['chunk_id']}_{part_index}",
                    'content': '\n\n'.join(current_parts),
                    'char_count': len('\n\n'.join(current_parts)),
                    'is_partial': True,
                    'part_index': part_index,
                }
                sub_chunks.append(sub_chunk)
                
                current_parts = [para]
                current_tokens = para_tokens
                part_index += 1
            else:
                current_parts.append(para)
                current_tokens += para_tokens
        
        if current_parts:
            sub_chunk = {
                **chunk,
                'chunk_id': f"{chunk['chunk_id']}_{part_index}",
                'content': '\n\n'.join(current_parts),
                'char_count': len('\n\n'.join(current_parts)),
                'is_partial': True,
                'part_index': part_index,
            }
            sub_chunks.append(sub_chunk)
        
        # 更新 total_parts
        for sc in sub_chunks:
            sc['total_parts'] = len(sub_chunks)
        
        return sub_chunks
    
    def _enrich_chunk_metadata(self, chunk):
        """丰富元数据"""
        content = chunk['content']
        
        # 检测内容类型
        chunk['content_type'] = self._detect_content_type(content)
        
        # 检测特征
        chunk['has_code'] = chunk['content_type'] == 'code' or bool(
            re.search(r'(struct|int main|void \w+\(|#include)', content)
        )
        chunk['has_table'] = chunk['content_type'] == 'table'
        chunk['has_image_ref'] = bool(re.search(r'如图\s*\d+[-.]\d+', content))
        chunk['has_formula'] = bool(re.search(r'[\^_]|\w+\d+', content))
        
        # 估算 token
        chunk['token_count'] = chunk['char_count'] // 2
        
        return chunk
    
    def _detect_content_type(self, text):
        """检测内容类型"""
        if re.search(r'^(\d+\.\d+\.\d+\s+)?(本节小结|本章小结|总结)', text[:100]):
            return 'summary'
        if re.search(r'^(\d+\.\d+\.\d+\s+)?(本节习题|习题精选|练习题)', text[:100]):
            return 'exercise'
        if re.search(r'答案与解析|参考答案|【答案】', text[:200]):
            return 'answer'
        
        code_score = sum(1 for p in [r'#include', r'struct\s+\w+', r'int\s+main']
                        if re.search(p, text))
        if code_score >= 2:
            return 'code'
        
        if '|' in text or '表' in text[:100]:
            return 'table'
        
        return 'concept'
    
    def _generate_stats(self, chunks, subject_name):
        """生成统计信息"""
        tokens = [c['token_count'] for c in chunks]
        types = {}
        for c in chunks:
            t = c['content_type']
            types[t] = types.get(t, 0) + 1
        
        return {
            'subject': subject_name,
            'total_chunks': len(chunks),
            'avg_tokens': sum(tokens) // len(tokens) if tokens else 0,
            'min_tokens': min(tokens) if tokens else 0,
            'max_tokens': max(tokens) if tokens else 0,
            'content_types': types,
        }
    
    # 辅助方法
    def _extract_chapter_number(self, title):
        match = re.search(r'第([一二三四五六七八九十\d]+)章', title)
        if match:
            num = match.group(1)
            mapping = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                      '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
            return str(mapping.get(num, num))
        return None
    
    def _extract_chapter_title(self, title):
        match = re.search(r'第[一二三四五六七八九十\d]+章\s+(.+)', title)
        return match.group(1) if match else title
    
    def _extract_section_number(self, title):
        match = re.match(r'^(\d+\.\d+)', title)
        return match.group(1) if match else None
    
    def _extract_section_title(self, title):
        match = re.match(r'^\d+\.\d+\s+(.+)', title)
        return match.group(1) if match else title
    
    def _extract_subsection_number(self, title):
        match = re.match(r'^(\d+\.\d+\.\d+)', title)
        return match.group(1) if match else None
    
    def _extract_subsection_title(self, title):
        match = re.match(r'^\d+\.\d+\.\d+\s+(.+)', title)
        return match.group(1) if match else title


def main():
    """主函数"""
    processor = PDFProcessor()
    
    pdf_files = [
        ('2026数据结构_带书签【公众号：研料库，料最全】.pdf', '数据结构'),
        ('2026操作系统_带书签【公众号：研料库，料最全】.pdf', '操作系统'),
        ('2026计算机组成原理_带书签【公众号：研料库，料最全】.pdf', '计算机组成原理'),
        ('2026计算机网络_带书签【公众号：研料库，料最全】.pdf', '计算机网络'),
    ]
    
    all_stats = []
    for filename, subject in pdf_files:
        pdf_path = os.path.join(CONFIG['input_dir'], filename)
        if os.path.exists(pdf_path):
            _, stats = processor.process_pdf(pdf_path, subject)
            all_stats.append(stats)
        else:
            print(f"文件不存在: {pdf_path}")
    
    # 保存汇总统计
    summary_file = os.path.join(CONFIG['output_dir'], 'processing_summary.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print("全部处理完成!")
    print(f"汇总统计已保存: {summary_file}")
    print("="*60)


if __name__ == '__main__':
    main()
```

---

## 4. 依赖安装

```bash
# 系统依赖（macOS）
brew install poppler

# Python 依赖
pip install pdf2image pillow paddleocr pypdf tqdm

# PaddlePaddle（CPU 版本）
pip install paddlepaddle

# 如需 GPU 加速
# pip install paddlepaddle-gpu
```

---

## 5. 输出文件结构

```
processed/
├── ds_chunks.json          # 数据结构 chunks
├── os_chunks.json          # 操作系统 chunks
├── co_chunks.json          # 计算机组成原理 chunks
├── cn_chunks.json          # 计算机网络 chunks
└── processing_summary.json # 处理汇总统计
```

**Chunk 示例**（3.2.10 本节小结）：
```json
{
  "chunk_id": "os_3.2.10",
  "subject_code": "os",
  "chapter_number": "3",
  "chapter_title": "内存管理",
  "section_number": "3.2",
  "section_title": "虚拟内存",
  "subsection": "3.2.10",
  "subsection_title": "本节小结",
  "page_start": 238,
  "page_end": 239,
  "content": "虚拟内存技术允许进程部分装入内存即可运行...",
  "char_count": 1856,
  "token_count": 928,
  "content_type": "summary",
  "has_code": false,
  "has_table": false,
  "has_image_ref": false,
  "has_formula": false,
  "is_partial": false
}
```

---

## 6. Chunk 切分策略总结

| 策略 | 说明 |
|------|------|
| **主要切分单位** | 小节（subsection，如 3.2.10） |
| **跨页合并** | 同一小节跨多页时合并为一个 chunk |
| **过长切分** | >3000 tokens 时按段落切分，标记 `is_partial` |
| **过短合并** | <200 tokens 时与下一个小节合并 |
| **代码保护** | 不在代码块中间切分 |
| **内容标记** | 自动识别 concept/code/table/exercise/answer/summary |

---

## 7. 预估处理时间

| 步骤 | 预估时间（1444 页） |
|------|-------------------|
| 提取书签 | 1 分钟 |
| PDF 转图片 | 10-15 分钟 |
| 去水印处理 | 5 分钟 |
| OCR 识别（CPU） | 2-3 小时 |
| OCR 识别（GPU） | 30-45 分钟 |
| 文本清洗 | 5 分钟 |
| 书签合并 | 2 分钟 |
| 智能切分 | 2 分钟 |
| 类型检测 | 3 分钟 |
| **总计（CPU）** | **约 3 小时** |
| **总计（GPU）** | **约 1 小时** |

---

## 8. 后续步骤

预处理完成后，可将生成的 JSON 文件导入向量数据库（如 Chroma、Milvus），构建 RAG 知识库。每个 chunk 包含完整的元数据，支持按科目、章节、内容类型等多维度检索。

---

*文档版本: 2.0*
*更新日期: 2025-03-24*
*更新内容: 基于书签层级的智能 chunk 切分策略*
