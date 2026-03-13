import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import timedelta

from app.main import app
from app.database import Base, get_db
from app.models import User, Board, List
from app.schemas import UserCreate, BoardCreate
from app.security import create_access_token

# Setup test database (SQLite in-memory or file)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="session")
def session_fixture():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def client_fixture(session):
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session):
    user_data = UserCreate(email="test@example.com", password="password123")
    hashed_password = "hashed_password"
    db_user = User(email=user_data.email, hashed_password=hashed_password, is_active=True)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@pytest.fixture(name="test_user_token")
def test_user_token_fixture(test_user):
    access_token_expires = timedelta(minutes=30)
    to_encode = {"sub": test_user.email}
    return create_access_token(to_encode, access_token_expires)


@pytest.fixture(name="test_board")
def test_board_fixture(session, test_user):
    board_data = BoardCreate(title="Test Board")
    db_board = Board(title=board_data.title, owner_id=test_user.id)
    session.add(db_board)
    session.commit()
    session.refresh(db_board)

    # Add default lists for the board
    list_todo = List(title="Por Hacer", position=0, board_id=db_board.id)
    list_in_progress = List(title="En Progreso", position=1, board_id=db_board.id)
    list_done = List(title="Hecho", position=2, board_id=db_board.id)
    session.add_all([list_todo, list_in_progress, list_done])
    session.commit()
    session.refresh(list_todo)
    session.refresh(list_in_progress)
    session.refresh(list_done)

    db_board.lists = [list_todo, list_in_progress, list_done]
    return db_board
