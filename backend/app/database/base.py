"""
Base model definitions
"""
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, DateTime, func

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
