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

from app.core.logger import get_logger


logger = get_logger(__name__)


class OCRService:
    def __init__(self):
        self.supported_extensions = [
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "gif",
            "bmp",
        ]

    async def extract_text(self, file_path: str, file_type: str) -> str:
        """Extract text from a file using OCR."""

        extension = file_type.lower().replace(".", "")

        if extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {file_type}")

        try:
            if extension == "pdf":
                return await self._extract_from_pdf(file_path)

            return await self._extract_from_image(file_path)

        except Exception as e:
            logger.error(
                f"OCR extraction failed for {file_path}: {e}"
            )
            raise

    async def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF using OCR."""

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

    async def _extract_from_image(self, file_path: str) -> str:
        """Extract text from an image using OCR."""

        image = Image.open(file_path)

        text = pytesseract.image_to_string(
            image,
            lang="eng"
        )

        return text.strip()

