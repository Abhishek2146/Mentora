"""
OCR module - Optical Character Recognition for document processing
"""
from app.services.ocr_service import OCRService

ocr_service = OCRService()

__all__ = ["ocr_service", "OCRService"]
