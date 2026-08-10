"""
Coding Generator module
"""
from app.services.coding_service import CodingService

coding_generator = CodingService()

__all__ = ["coding_generator", "CodingService"]
