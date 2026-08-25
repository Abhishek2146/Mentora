# """
# OCR Service - extracts text from uploaded syllabus files
# """
# import os
# import pytesseract
# from pdf2image import convert_from_path
# from PIL import Image
# from typing import Optional

# from app.core.logger import get_logger

# logger = get_logger(__name__)


# class OCRService:
#     def __init__(self):
#         self.supported_extensions = ["pdf", "png", "jpg", "jpeg", "gif", "bmp"]

#     async def extract_text(self, file_path: str, file_type: str) -> str:
#         """Extract text from a file using OCR."""
#         if file_type.lower() not in self.supported_extensions:
#             raise ValueError(f"Unsupported file type: {file_type}")

#         try:
#             if file_type.lower() == "pdf":
#                 return await self._extract_from_pdf(file_path)
#             else:
#                 return await self._extract_from_image(file_path)
#         except Exception as e:
#             logger.error(f"OCR extraction failed for {file_path}: {e}")
#             raise

#     async def _extract_from_pdf(self, file_path: str) -> str:
#         """Extract text from PDF file."""
#         pages = convert_from_path(file_path, dpi=300)
#         text = ""
#         for page in pages:
#             page_text = pytesseract.image_to_string(page, lang="eng+spa+fra")
#             text += page_text + "\n"
#         return text.strip()

#     async def _extract_from_image(self, file_path: str) -> str:
#         """Extract text from image file."""
#         image = Image.open(file_path)
#         text = pytesseract.image_to_string(image, lang="eng+spa+fra")
#         return text.strip()


"""
OCR Service - extracts text from uploaded syllabus files
"""

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger(__name__)


if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


class OCRService:
    def __init__(self):
        self.supported_extensions = [
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "gif",
            "bmp",
            "docx",
            "txt",
        ]

    async def extract_text(self, file_path: str, file_type: str) -> str:
        """Extract text from a file using OCR."""

        extension = file_type.lower().replace(".", "")

        if extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {file_type}")

        try:
            if extension == "pdf":
                return await self._extract_from_pdf(file_path)

            if extension == "docx":
                return await self._extract_from_docx(file_path)

            if extension == "txt":
                return await self._extract_from_txt(file_path)

            return await self._extract_from_image(file_path)

        except pytesseract.TesseractNotFoundError:
            logger.error(
                "Tesseract OCR is not installed or not in PATH. "
                "Install Tesseract and set TESSERACT_CMD in config."
            )
            raise

        except Exception as e:
            logger.error(
                f"OCR extraction failed for {file_path}: {e}"
            )
            raise

    async def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF.

        For digital (text-based) PDFs the text is read directly with pypdf,
        which requires no external tools.  Only scanned/image-only PDFs fall
        back to Tesseract OCR.
        """

        # 1. Direct text extraction (no Tesseract needed)
        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            text_parts = []

            for page in reader.pages:
                try:
                    page_text = page.extract_text() or ""
                except Exception:
                    page_text = ""
                if page_text.strip():
                    text_parts.append(page_text.strip())

            direct_text = "\n".join(text_parts).strip()
            if direct_text:
                logger.info(
                    "Extracted text directly from PDF (OCR not required)"
                )
                return direct_text

            logger.info(
                "No selectable text found in PDF; falling back to OCR"
            )

        except Exception as e:
            logger.warning(
                f"Direct PDF text extraction failed: {e}; "
                "falling back to OCR"
            )

        # 2. OCR fallback (requires Tesseract, only for scanned PDFs)
        pages = convert_from_path(
            file_path,
            dpi=300
        )

        text_parts = []

        for page_number, page in enumerate(pages, start=1):
            logger.info(
                f"Processing PDF page {page_number}"
            )

            page_text = pytesseract.image_to_string(
                page,
                lang="eng"
            )

            if page_text:
                text_parts.append(page_text)

        return "\n".join(text_parts).strip()

    async def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from a DOCX file using python-docx."""
        try:
            from docx import Document
        except ImportError:
            logger.error(
                "python-docx is not installed. "
                "Install with: pip install python-docx"
            )
            raise RuntimeError(
                "DOCX extraction is not available - python-docx is not installed."
            )

        doc = Document(file_path)
        text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(text_parts).strip()

    async def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from a plain-text file."""
        import codecs

        with codecs.open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    async def _extract_from_image(self, file_path: str) -> str:
        """Extract text from an image using OCR."""

        image = Image.open(file_path)

        text = pytesseract.image_to_string(
            image,
            lang="eng"
        )

        return text.strip()

