"""
OCR 工具模块

使用 RapidOCR (基于 ONNX Runtime) 实现图片和 PDF 的文字识别。
轻量级 PaddleOCR 替代，无需安装 PaddlePaddle。

支持:
- 图片 OCR (PNG, JPG, JPEG)
- PDF 逐页转图 + OCR
- 图片预处理 (灰度化、自适应二值化)
"""

from pathlib import Path

from app.utils.logging import get_logger
from app.utils.exceptions import OCRError

logger = get_logger("ocr")


class OCREngine:
    """OCR 引擎 — 封装 RapidOCR 和 PDF 转图逻辑"""

    def __init__(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
            logger.info("RapidOCR 引擎初始化成功")
        except ImportError:
            logger.error("RapidOCR 未安装，请运行: uv add rapidocr-onnxruntime")
            self._engine = None
        except Exception as e:
            logger.error("RapidOCR 初始化失败: %s", str(e))
            self._engine = None

    @property
    def available(self) -> bool:
        return self._engine is not None

    def recognize_image(self, image_path: str | Path) -> str:
        """
        识别图片中的文字。

        Args:
            image_path: 图片文件路径

        Returns:
            识别出的文本（多行拼接）

        Raises:
            OCRError: 识别失败
        """
        if not self.available:
            raise OCRError(
                message="OCR 引擎不可用",
                detail="RapidOCR 未正确初始化",
            )

        image_path = Path(image_path)
        if not image_path.exists():
            raise OCRError(message=f"图片文件不存在: {image_path.name}")

        try:
            # 预处理
            preprocessed = self._preprocess_image(image_path)

            # OCR 识别
            result, _ = self._engine(preprocessed)

            if not result:
                logger.info("OCR 未识别到文字 file=%s", image_path.name)
                return ""

            # result 格式: [[box, text, confidence], ...]
            lines = [item[1] for item in result if item[1]]
            text = "\n".join(lines)

            logger.info(
                "OCR 识别完成 file=%s lines=%d chars=%d",
                image_path.name, len(lines), len(text),
            )
            return text

        except OCRError:
            raise
        except Exception as e:
            logger.error("OCR 识别失败 file=%s error=%s", image_path.name, str(e), exc_info=True)
            raise OCRError(
                message="图片文字识别失败",
                detail=f"file={image_path.name}, error={str(e)}",
            )

    def recognize_pdf(self, pdf_path: str | Path) -> str:
        """
        识别 PDF 中的文字（逐页转图后 OCR）。

        Args:
            pdf_path: PDF 文件路径

        Returns:
            所有页面识别文本拼接

        Raises:
            OCRError: 识别失败
        """
        if not self.available:
            raise OCRError(
                message="OCR 引擎不可用",
                detail="RapidOCR 未正确初始化",
            )

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise OCRError(message=f"PDF 文件不存在: {pdf_path.name}")

        try:
            import fitz  # pymupdf

            doc = fitz.open(str(pdf_path))
            all_text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                # 渲染为高分辨率图片 (2x 缩放 = 144 DPI)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")

                # 用 RapidOCR 识别 bytes
                result, _ = self._engine(img_bytes)

                if result:
                    page_lines = [item[1] for item in result if item[1]]
                    page_text = "\n".join(page_lines)
                    all_text_parts.append(f"--- 第 {page_num + 1} 页 ---\n{page_text}")

                logger.debug("PDF OCR 进度 page=%d/%d", page_num + 1, len(doc))

            doc.close()

            text = "\n\n".join(all_text_parts)
            logger.info(
                "PDF OCR 完成 file=%s pages=%d chars=%d",
                pdf_path.name, len(doc), len(text),
            )
            return text

        except OCRError:
            raise
        except ImportError:
            raise OCRError(
                message="PDF 处理库未安装",
                detail="请运行: uv add pymupdf",
            )
        except Exception as e:
            logger.error("PDF OCR 失败 file=%s error=%s", pdf_path.name, str(e), exc_info=True)
            raise OCRError(
                message="PDF 文字识别失败",
                detail=f"file={pdf_path.name}, error={str(e)}",
            )

    def recognize(self, file_path: str | Path) -> str:
        """
        自动根据文件后缀选择 OCR 方法。

        Args:
            file_path: 图片或 PDF 路径

        Returns:
            识别出的文本
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()

        if ext == ".pdf":
            return self.recognize_pdf(file_path)
        elif ext in (".png", ".jpg", ".jpeg"):
            return self.recognize_image(file_path)
        else:
            raise OCRError(
                message=f"不支持的 OCR 文件格式: {ext}",
                detail=f"支持: .png, .jpg, .jpeg, .pdf",
            )

    @staticmethod
    def _preprocess_image(image_path: Path) -> str:
        """
        图片预处理：灰度化 + 自适应二值化，提升 OCR 准确率。

        Returns:
            预处理后的图片路径（str）
        """
        try:
            from PIL import Image, ImageFilter

            img = Image.open(image_path)

            # 转灰度
            if img.mode != "L":
                img = img.convert("L")

            # 轻度锐化
            img = img.filter(ImageFilter.SHARPEN)

            # 保存预处理结果到临时文件
            preprocessed_path = image_path.parent / f"_ocr_prep_{image_path.name}"
            img.save(preprocessed_path)

            return str(preprocessed_path)
        except Exception:
            # 预处理失败时直接用原图
            return str(image_path)


# 全局单例（延迟初始化）
_ocr_engine: OCREngine | None = None


def get_ocr_engine() -> OCREngine:
    """获取 OCR 引擎单例"""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine()
    return _ocr_engine
