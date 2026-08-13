# """
# Database connection and initialization
# """
# import asyncpg
# from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker, declarative_base

# from app.core.config import settings
# from app.core.logger import get_logger

# logger = get_logger(__name__)

# engine: AsyncEngine = create_async_engine(
#     settings.DATABASE_URL,
#     echo=settings.DB_ECHO,
#     pool_pre_ping=True,
#     pool_size=20,
#     max_overflow=10,
# )

# AsyncSessionLocal = sessionmaker(
#     bind=engine,
#     class_=AsyncSession,
#     expire_on_commit=False,
#     autoflush=False,
#     autocommit=False,
# )

# Base = declarative_base()


# async def init_db():
#     """Initialize database - create tables for both SQLite and PostgreSQL."""
#     try:
#         async with engine.begin() as conn:
#             await conn.run_sync(Base.metadata.create_all)
#         logger.info("Database tables initialized successfully")
#     except Exception as e:
#         logger.error(f"Database initialization/connection check failed: {e}")


# async def get_db() -> AsyncSession:
#     async with AsyncSessionLocal() as session:
#         yield session

"""
Database connection and initialization
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logger import get_logger
from app.database.base import Base

logger = get_logger(__name__)

# --------------------------------------------------
# Database Engine
# --------------------------------------------------

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)

# --------------------------------------------------
# Async Session
# --------------------------------------------------

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# # --------------------------------------------------
# # Import Models
# # --------------------------------------------------
# # These imports make sure SQLAlchemy knows about
# # all models before create_all() is executed.

# from app.models.user import User
# from app.models.syllabus import Syllabus
# from app.models.study_plan import StudyPlan
# from app.models.revision import Revision
# from app.models.quiz import Quiz
# from app.models.flashcard import Flashcard
# from app.models.progress import Progress
# from app.models.chat_history import ChatHistory
# from app.models.analytics import Analytics
# from app.models.coding_problem import CodingProblem


# # --------------------------------------------------
# # Initialize Database
# # --------------------------------------------------

# async def init_db():
#     """
#     Initialize database and create all registered tables.
#     """

#     try:
#         async with engine.begin() as conn:
#             await conn.run_sync(Base.metadata.create_all)

#         logger.info("Database tables initialized successfully")

#     except Exception as e:
#         logger.error(
#             f"Database initialization/connection check failed: {e}"
#         )
#         raise


# # --------------------------------------------------
# # Database Dependency
# # --------------------------------------------------

# async def get_db():
#     """
#     Provide an async database session.
#     """

#     async with AsyncSessionLocal() as session:
#         yield session

# """
# Database connection and initialization
# """

# from sqlalchemy.ext.asyncio import (
#     AsyncEngine,
#     AsyncSession,
#     create_async_engine,
# )
# from sqlalchemy.orm import sessionmaker, declarative_base

# from app.core.config import settings
# from app.core.logger import get_logger


# # --------------------------------------------------
# # Logger
# # --------------------------------------------------

# logger = get_logger(__name__)


# # --------------------------------------------------
# # Database Engine
# # --------------------------------------------------

# engine: AsyncEngine = create_async_engine(
#     settings.DATABASE_URL,
#     echo=settings.DB_ECHO,
#     pool_pre_ping=True,
#     pool_size=20,
#     max_overflow=10,
# )


# # --------------------------------------------------
# # Async Session
# # --------------------------------------------------

# AsyncSessionLocal = sessionmaker(
#     bind=engine,
#     class_=AsyncSession,
#     expire_on_commit=False,
#     autoflush=False,
#     autocommit=False,
# )


# # --------------------------------------------------
# # Base Model
# # --------------------------------------------------

# Base = declarative_base()


# # --------------------------------------------------
# # Import Models
# # --------------------------------------------------

# # These imports make sure SQLAlchemy knows about
# # all models before create_all() is executed.

# from app.models.user import User
# from app.models.syllabus import Syllabus
# from app.models.study_plan import StudyPlan
# from app.models.revision import RevisionSchedule
# from app.models.quiz import Quiz
# from app.models.flashcard import Flashcard
# from app.models.progress import Progress
# from app.models.chat_history import ChatSession
# from app.models.analytics import AnalyticsSummary
# from app.models.coding_problem import CodingProblem


# # --------------------------------------------------
# # Initialize Database
# # --------------------------------------------------

# async def init_db():
#     """
#     Initialize database and create all registered tables.
#     """

#     try:
#         async with engine.begin() as conn:
#             await conn.run_sync(Base.metadata.create_all)

#         logger.info(
#             "Database tables initialized successfully"
#         )

#     except Exception as e:
#         logger.error(
#             f"Database initialization/connection check failed: {e}"
#         )
#         raise


# # --------------------------------------------------
# # Database Dependency
# # --------------------------------------------------

# async def get_db():
#     """
#     Provide an async database session.
#     """

#     async with AsyncSessionLocal() as session:
#         yield session

"""
Database connection and initialization
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logger import get_logger

# IMPORTANT:
# Import the SAME Base that your models inherit from.
from app.database.base import Base

logger = get_logger(__name__)


# ==========================================================
# Database Engine
# ==========================================================

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)


# ==========================================================
# Async Session
# ==========================================================

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ==========================================================
# Import Models
# ==========================================================
#
# IMPORTANT:
# These imports must happen BEFORE create_all().
# This registers all models with the SAME Base.metadata.
#

from app.models.user import User
from app.models.syllabus import Syllabus
from app.models.study_plan import StudyPlan
from app.models.revision import RevisionSchedule
from app.models.quiz import Quiz
from app.models.flashcard import Flashcard
from app.models.progress import Progress
from app.models.chat_history import ChatSession
from app.models.analytics import AnalyticsSummary
from app.models.coding_problem import CodingProblem


# ==========================================================
# Initialize Database
# ==========================================================

async def init_db():
    """
    Initialize database and create all registered tables.
    """

    try:
        async with engine.begin() as conn:

            await conn.run_sync(
                Base.metadata.create_all
            )

        logger.info(
            "Database tables initialized successfully"
        )

    except Exception as e:

        logger.error(
            f"Database initialization/connection check failed: {e}"
        )

        raise


# ==========================================================
# Database Dependency
# ==========================================================

async def get_db():
    """
    Provide an async database session.
    """

    async with AsyncSessionLocal() as session:
        yield session