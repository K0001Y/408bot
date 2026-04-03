#!/usr/bin/env python3
"""
408 教材数据预处理脚本
基于书签层级的智能 chunk 切分
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from tqdm import tqdm

# 导入配置和工具函数
from .config import (
    CONFIG, SUBJECTS, PDF_FILES,
    ensure_directories, get_pdf_path, get_output_path,
    OUTPUT_DIR
)
from .utils import (
    extract_chapter_number, extract_chapter_title,
    extract_section_number, extract_section_title,
    extract_subsection_number, extract_subsection_title,
    determine_bookmark_level, clean_text,
    detect_content_type, would_split_code_block,
    enrich_chunk_metadata, generate_stats,
    estimate_tokens
)

# 延迟导入重型依赖（在类初始化时再导入）


class PDFProcessor:
    """PDF 处理器主类"""
    
    def __init__(self):
        self.ocr = None
        self.pdf2image = None
        self.pypdf = None
        self._init_ocr()
        ensure_directories()
    
    def _init_ocr(self):
        """初始化 OCR 引擎"""
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                lang=CONFIG['ocr_lang']
            )
            print("✓ OCR 引擎初始化成功")
        except ImportError:
            print("✗ PaddleOCR 未安装，请先安装: pip install paddleocr")
            raise
    
    def process_pdf(self, pdf_path: Path, subject_name: str) -> Tuple[List[Dict], Dict]:
        """
        处理单个 PDF 文件
        
        Args:
            pdf_path: PDF 文件路径
            subject_name: 科目名称
        
        Returns:
            Tuple[List[Dict], Dict]: (chunks 列表, 统计信息)
        """
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
        images = self._pdf_to_images(pdf_path)
        print(f"  共 {len(images)} 页")
        
        # Step 3-5: 处理每一页（去水印 + OCR + 清洗）
        print("[Step 3-5/8] 去水印、OCR、清洗...")
        pages_text = self._process_pages(images, subject_code)
        print(f"  完成 {len(pages_text)} 页处理")
        
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
        output_file = get_output_path(subject_code)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        # 生成统计信息
        stats = generate_stats(chunks, subject_name)
        print(f"\n  完成! 输出: {output_file}")
        print(f"  统计: {stats['total_chunks']} chunks, "
              f"平均 {stats['avg_tokens']} tokens/chunk")
        
        return chunks, stats
    
    def _extract_bookmarks(self, pdf_path: Path, subject_code: str) -> List[Dict]:
        """
        提取三级书签
        
        Args:
            pdf_path: PDF 文件路径
            subject_code: 科目代码
        
        Returns:
            List[Dict]: 书签列表
        """
        from pypdf import PdfReader
        
        reader = PdfReader(str(pdf_path))
        outlines = reader.outline
        
        bookmarks = []
        current_chapter = None
        current_section = None
        
        # 先统计总数用于进度条
        def count_items(items):
            count = 0
            for item in items:
                if isinstance(item, list):
                    count += count_items(item)
                else:
                    count += 1
            return count
        
        total_items = count_items(outlines)
        
        def parse_outline(items, level=0, pbar=None):
            nonlocal current_chapter, current_section
            
            for item in items:
                if isinstance(item, list):
                    parse_outline(item, level + 1, pbar)
                else:
                    try:
                        page_num = reader.get_destination_page_number(item) + 1
                        title = item.title.strip()
                        
                        bm_level = determine_bookmark_level(title)
                        
                        # 更新当前章/节
                        if bm_level == 0:
                            current_chapter = {
                                'number': extract_chapter_number(title),
                                'title': extract_chapter_title(title)
                            }
                        elif bm_level == 1:
                            current_section = {
                                'number': extract_section_number(title),
                                'title': extract_section_title(title)
                            }
                        
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
                        print(f"  警告: 解析书签失败 - {e}")
                    finally:
                        if pbar:
                            pbar.update(1)
        
        with tqdm(total=total_items, desc="  提取书签", unit="个") as pbar:
            parse_outline(outlines, pbar=pbar)
        
        return bookmarks
    
    def _pdf_to_images(self, pdf_path: Path) -> List:
        """
        将 PDF 转换为图片列表
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            List: PIL Image 对象列表
        """
        import fitz  # PyMuPDF
        from PIL import Image
        import io
        
        doc = fitz.open(str(pdf_path))
        images = []
        total_pages = len(doc)
        
        for page_num in tqdm(range(total_pages), desc="  PDF转图片", total=total_pages, unit="页"):
            page = doc[page_num]
            # 设置缩放比例以达到目标 DPI
            mat = fitz.Matrix(CONFIG['dpi']/72, CONFIG['dpi']/72)
            pix = page.get_pixmap(matrix=mat)
            
            # 转换为 PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
        
        doc.close()
        return images
    
    def _process_pages(self, images: List, subject_code: str) -> List[str]:
        """
        处理所有页面（去水印 + OCR + 清洗）
        
        Args:
            images: PIL Image 对象列表
            subject_code: 科目代码
        
        Returns:
            List[str]: 每页的清洗后文本
        """
        from .config import TEMP_DIR
        
        pages_text = []
        
        for i, image in enumerate(tqdm(images, desc="  处理页面")):
            # 去水印
            cleaned_image = self._remove_watermark(image)
            
            # 临时保存
            temp_path = TEMP_DIR / f"{subject_code}_{i:04d}.png"
            cleaned_image.save(temp_path)
            
            # OCR
            text = self._ocr_image(str(temp_path))
            
            # 清洗
            text = clean_text(text)
            
            pages_text.append(text)
            
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
        
        return pages_text
    
    def _remove_watermark(self, image):
        """
        去除水印（裁剪法）
        
        Args:
            image: PIL Image 对象
        
        Returns:
            PIL Image 对象
        """
        from PIL import Image
        
        width, height = image.size
        top = int(height * CONFIG['watermark_crop_top'])
        bottom = int(height * CONFIG['watermark_crop_bottom'])
        return image.crop((0, top, width, bottom))
    
    def _ocr_image(self, image_path: str) -> str:
        """
        OCR 识别
        
        Args:
            image_path: 图片路径
        
        Returns:
            str: 识别的文字内容
        """
        result = self.ocr.ocr(image_path)
        texts = []
        if result and len(result) > 0 and result[0]:
            for line in result[0]:
                text = line[1][0]
                confidence = line[1][1]
                if confidence >= CONFIG['min_confidence']:
                    texts.append(text)
        return "\n".join(texts)
    
    def _create_chunks_by_bookmarks(self, pages_text: List[str], bookmarks: List[Dict]) -> List[Dict]:
        """
        按书签合并页面
        
        Args:
            pages_text: 每页的 OCR 文本
            bookmarks: 书签列表
        
        Returns:
            List[Dict]: chunk 列表
        """
        chunks = []
        subsection_bms = [bm for bm in bookmarks if bm['level'] == 2]
        
        for i, bm in enumerate(tqdm(subsection_bms, desc="  合并页面", unit="个")):
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
    
    def _smart_split_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        智能切分 chunks
        
        Args:
            chunks: 原始 chunk 列表
        
        Returns:
            List[Dict]: 处理后的 chunk 列表
        """
        result = []
        pending_small = None
        
        for chunk in tqdm(chunks, desc="  智能切分", unit="个"):
            tokens = estimate_tokens(chunk['content'])
            
            # 处理过小 chunk：暂存，尝试与下一个合并
            if tokens < CONFIG['min_chunk_tokens']:
                if pending_small:
                    # 合并到前一个待处理 chunk
                    pending_small['content'] += '\n\n' + chunk['content']
                    pending_small['char_count'] = len(pending_small['content'])
                    pending_small['page_end'] = chunk['page_end']
                    # 处理 subsection 可能为 None 的情况
                    if pending_small['subsection'] and chunk['subsection']:
                        pending_small['subsection'] += f",{chunk['subsection']}"
                    elif chunk['subsection']:
                        pending_small['subsection'] = chunk['subsection']
                else:
                    pending_small = chunk.copy()
                continue
            
            # 如果有待处理的小 chunk，先处理它
            if pending_small:
                result.append(pending_small)
                pending_small = None
            
            # 处理过大 chunk：按段落切分
            if tokens > CONFIG['max_chunk_tokens']:
                sub_chunks = self._split_large_chunk(chunk)
                result.extend(sub_chunks)
            else:
                result.append(chunk)
        
        # 处理最后待处理的小 chunk
        if pending_small:
            result.append(pending_small)
        
        return result
    
    def _split_large_chunk(self, chunk: Dict) -> List[Dict]:
        """
        切分大 chunk
        
        Args:
            chunk: 原始 chunk
        
        Returns:
            List[Dict]: 切分后的子 chunk 列表
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
                sub_chunk = self._create_sub_chunk(chunk, current_parts, part_index)
                sub_chunks.append(sub_chunk)
                
                current_parts = [para]
                current_tokens = para_tokens
                part_index += 1
            
            # 正常累加
            elif current_tokens + para_tokens > CONFIG['max_chunk_tokens'] and current_parts:
                # 保存当前 sub-chunk
                sub_chunk = self._create_sub_chunk(chunk, current_parts, part_index)
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
            sub_chunk = self._create_sub_chunk(chunk, current_parts, part_index)
            sub_chunks.append(sub_chunk)
        
        # 更新 total_parts
        for sc in sub_chunks:
            sc['total_parts'] = len(sub_chunks)
        
        return sub_chunks
    
    def _create_sub_chunk(self, original_chunk: Dict, parts: List[str], part_index: int) -> Dict:
        """
        创建子 chunk
        
        Args:
            original_chunk: 原始 chunk
            parts: 内容段落列表
            part_index: 部分索引
        
        Returns:
            Dict: 子 chunk
        """
        content = '\n\n'.join(parts)
        return {
            **original_chunk,
            'chunk_id': f"{original_chunk['chunk_id']}_{part_index}",
            'content': content,
            'char_count': len(content),
            'is_partial': True,
            'part_index': part_index,
        }
    
    def _enrich_chunk_metadata(self, chunk: Dict) -> Dict:
        """
        丰富 chunk 元数据
        
        Args:
            chunk: 原始 chunk
        
        Returns:
            Dict: 添加元数据后的 chunk
        """
        return enrich_chunk_metadata(chunk)


def main():
    """主函数"""
    processor = PDFProcessor()
    
    all_stats = []
    # 只处理后两本：计算机组成原理和计算机网络
    remaining_pdfs = [
        ('2026计算机组成原理_带书签【公众号：研料库，料最全】.pdf', '计算机组成原理'),
        ('2026计算机网络_带书签【公众号：研料库，料最全】.pdf', '计算机网络'),
    ]
    existing_pdfs = [(f, s) for f, s in remaining_pdfs if get_pdf_path(f).exists()]
    
    if not existing_pdfs:
        print("警告: 没有找到任何PDF文件!")
        return
    
    print(f"\n准备处理 {len(existing_pdfs)} 个PDF文件...")
    print("="*60)
    
    for filename, subject in tqdm(existing_pdfs, desc="总体进度", unit="个"):
        pdf_path = get_pdf_path(filename)
        _, stats = processor.process_pdf(pdf_path, subject)
        all_stats.append(stats)
    
    # 保存汇总统计
    summary_file = OUTPUT_DIR / 'processing_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print("全部处理完成!")
    print(f"汇总统计已保存: {summary_file}")
    print("="*60)
    
    # 打印汇总信息
    total_chunks = sum(s['total_chunks'] for s in all_stats)
    print(f"\n总计处理: {len(all_stats)} 个科目, {total_chunks} 个 chunks")


if __name__ == '__main__':
    main()
