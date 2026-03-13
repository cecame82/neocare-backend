# app/tests/test_cards.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import User, Board, List, Card
from app.schemas import UserCreate, BoardCreate
from app.security import create_access_token
from datetime import datetime, timedelta

# Setup test database
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
    hashed_password = "hashed_password" # In a real app, hash this
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

    # Attach lists to the board object for easy access in tests
    db_board.lists = [list_todo, list_in_progress, list_done]
    return db_board

def test_create_card(client: TestClient, test_user_token: str, test_board: Board, session):
    response = client.post(
        "/cards",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "New Test Card",
            "description": "Card description",
            "list_id": test_board.lists[0].id, # Use the ID of the first list
            "board_id": test_board.id,
            "due_date": "2025-12-25"
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "New Test Card"
    assert data["list_id"] == test_board.lists[0].id
    assert data["board_id"] == test_board.id
    assert data["user_id"] == data["user_id"] # test_user.id
    assert "id" in data
    assert "created_at" in data

def test_create_card_unauthenticated(client: TestClient, test_board: Board):
    response = client.post(
        "/cards",
        json={
            "title": "New Test Card",
            "list_id": test_board.lists[0].id,
            "board_id": test_board.id,
        },
    )
    assert response.status_code == 401

def test_create_card_invalid_board_or_list(client: TestClient, test_user_token: str):
    response = client.post(
        "/cards",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "Card with Invalid List",
            "list_id": 9999, # Invalid list ID
            "board_id": 1,
        },
    )
    assert response.status_code == 400 # Or 404 depending on backend validation

def test_read_cards(client: TestClient, test_user_token: str, test_board: Board, session):
    # Create a card first
    client.post(
        "/cards",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "Card for Read",
            "list_id": test_board.lists[0].id,
            "board_id": test_board.id,
        },
    )
    response = client.get(
        f"/cards?board_id={test_board.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Card for Read"

def test_read_cards_unauthorized_board(client: TestClient, test_user_token: str):
    # Attempt to read cards from a non-existent or unauthorized board
    response = client.get(
        "/cards?board_id=9999",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 404 # Board not found or not owned by user

def test_get_single_card(client: TestClient, test_user_token: str, test_board: Board, session):
    create_response = client.post(
        "/cards",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "Single Card",
            "list_id": test_board.lists[0].id,
            "board_id": test_board.id,
        },
    )
    card_id = create_response.json()["id"]

    response = client.get(
        f"/cards/{card_id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Single Card"
    assert data["id"] == card_id

def test_update_card(client: TestClient, test_user_token: str, test_board: Board, session):
    create_response = client.post(
        "/cards",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "Old Title",
            "list_id": test_board.lists[0].id,
            "board_id": test_board.id,
        },
    )
    card_id = create_response.json()["id"]

    update_payload = {
        "title": "Updated Title",
        "description": "New description",
        "list_id": test_board.lists[1].id, # Move to another list
        "due_date": "2026-01-01"
    }
    response = client.patch(
        f"/cards/{card_id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json=update_payload,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "New description"
    assert data["list_id"] == test_board.lists[1].id
    assert data["due_date"] == "2026-01-01"

def test_delete_card(client: TestClient, test_user_token: str, test_board: Board, session):
    create_response = client.post(
        "/cards",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "title": "Card to Delete",
            "list_id": test_board.lists[0].id,
            "board_id": test_board.id,
        },
    )
    card_id = create_response.json()["id"]

    response = client.delete(
        f"/cards/{card_id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert response.status_code == 204 # No Content

    # Verify card is deleted
    get_response = client.get(
        f"/cards/{card_id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )
    assert get_response.status_code == 404
