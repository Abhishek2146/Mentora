"""
Review API tests.

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
from app.api.v1.reviews import router as reviews_router


@pytest.fixture
async def db_engine(tmp_path):
    db_path = tmp_path / "test_reviews.db"
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
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="student@test.com",
        username="student",
        hashed_password="x",
        role="student",
        full_name="Student Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    user = User(
        email="other@test.com",
        username="other",
        hashed_password="x",
        role="student",
        full_name="Other Student",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def review_app(db_session: AsyncSession, test_user: User) -> FastAPI:
    app = FastAPI()
    app.include_router(reviews_router)
    app.dependency_overrides[get_current_user_id] = lambda: test_user.id

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return app


@pytest.fixture
async def review_client(review_app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=review_app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_create_review(review_client: AsyncClient):
    response = await review_client.post("/", json={"rating": 5, "comment": "Amazing!"})
    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 5
    assert data["comment"] == "Amazing!"


async def test_create_review_upserts_single_row(review_client: AsyncClient):
    first = await review_client.post("/", json={"rating": 3, "comment": "Okay"})
    second = await review_client.post("/", json={"rating": 5, "comment": "Better now"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["rating"] == 5
    assert second.json()["comment"] == "Better now"


async def test_rating_bounds_rejected(review_client: AsyncClient):
    too_high = await review_client.post("/", json={"rating": 6, "comment": "X"})
    too_low = await review_client.post("/", json={"rating": 0, "comment": "X"})
    assert too_high.status_code == 422
    assert too_low.status_code == 422


async def test_get_my_review(review_client: AsyncClient, test_user: User):
    await review_client.post("/", json={"rating": 4, "comment": "Nice"})
    response = await review_client.get("/me")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == test_user.id
    assert data["rating"] == 4


async def test_get_my_review_404_when_none(review_client: AsyncClient):
    response = await review_client.get("/me")
    assert response.status_code == 404


async def test_update_my_review(review_client: AsyncClient):
    await review_client.post("/", json={"rating": 2, "comment": "Meh"})
    response = await review_client.put("/me", json={"rating": 5, "comment": "Turned around!"})
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == 5
    assert data["comment"] == "Turned around!"


async def test_delete_my_review(review_client: AsyncClient):
    await review_client.post("/", json={"rating": 5, "comment": "Bye"})
    response = await review_client.delete("/me")
    assert response.status_code == 204
    assert (await review_client.get("/me")).status_code == 404


async def test_public_listing_shows_reviews(
    db_session: AsyncSession,
    test_user: User,
    other_user: User,
    review_app: FastAPI,
):
    from app.models.review import Review

    db_session.add_all(
        [
            Review(user_id=test_user.id, rating=5, comment="Love it"),
            Review(user_id=other_user.id, rating=4, comment="Pretty good"),
        ]
    )
    await db_session.commit()

    transport = ASGITransport(app=review_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 2
        names = {row["user_name"] for row in rows}
        assert "Student Test" in names
        assert "Other Student" in names


async def test_public_summary(
    db_session: AsyncSession,
    test_user: User,
    other_user: User,
    review_app: FastAPI,
):
    from app.models.review import Review

    db_session.add_all(
        [
            Review(user_id=test_user.id, rating=5, comment="A"),
            Review(user_id=other_user.id, rating=4, comment="B"),
        ]
    )
    await db_session.commit()

    transport = ASGITransport(app=review_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_reviews"] == 2
    assert data["average_rating"] == 4.5