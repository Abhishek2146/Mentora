"""
Public landing-page stats tests.

Runs against an in-memory SQLite database (aiosqlite) so no external
PostgreSQL is required.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


from app.core.auth import get_current_user_id
from app.database.base import Base
from app.database.database import get_db
from app.models.user import User
from app.api.v1.stats import router as stats_router


@pytest.fixture
async def db_engine(tmp_path):
    db_path = tmp_path / "test_stats.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    maker = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest.fixture
async def test_student(db_session: AsyncSession) -> User:
    user = User(
        email="s1@test.com",
        username="s1",
        hashed_password="x",
        role="student",
        full_name="Student One",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    user = User(
        email="a1@test.com",
        username="a1",
        hashed_password="x",
        role="admin",
        full_name="Admin One",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def make_app(db_session: AsyncSession) -> FastAPI:
    app = FastAPI()
    app.include_router(stats_router)
    app.dependency_overrides[get_current_user_id] = lambda: 1

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return app


async def test_stats_empty_db(db_session: AsyncSession):
    app = make_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/public")

    assert response.status_code == 200
    data = response.json()
    assert data["total_students"] == 0
    assert data["total_flashcards"] == 0
    assert data["quiz_pass_rate"] is None
    assert data["total_reviews"] == 0
    assert data["average_rating"] is None


async def test_stats_with_data(
    db_session: AsyncSession,
    test_student: User,
    test_admin: User,
):
    from app.models.flashcard import FlashcardDeck, Flashcard
    from app.models.quiz import Quiz, QuizAttempt
    from app.models.review import Review

    deck = FlashcardDeck(user_id=test_student.id, title="Deck")
    quiz = Quiz(title="Q", user_id=test_student.id)
    db_session.add_all([deck, quiz, Review(user_id=test_student.id, rating=5, comment="Great")])
    await db_session.flush()

    db_session.add_all(
        [
            Flashcard(deck_id=deck.id, front="f1", back="b1"),
            Flashcard(deck_id=deck.id, front="f2", back="b2"),
            QuizAttempt(
                user_id=test_student.id,
                quiz_id=quiz.id,
                score=34,
                total_questions=40,
                correct_answers=34,
                is_passed=True,
            ),
            QuizAttempt(
                user_id=test_student.id,
                quiz_id=quiz.id,
                score=20,
                total_questions=40,
                correct_answers=20,
                is_passed=False,
            ),
        ]
    )
    await db_session.commit()

    app = make_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/public")

    assert response.status_code == 200
    data = response.json()
    # Only the student is counted, not the admin.
    assert data["total_students"] == 1
    assert data["total_flashcards"] == 2
    assert data["quiz_pass_rate"] == 50.0
    assert data["total_reviews"] == 1
    assert data["average_rating"] == 5.0