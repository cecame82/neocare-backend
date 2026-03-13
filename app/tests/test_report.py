import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime, timedelta

from app.main import app
from app.database import Base
from app.models import Card, List, Worklog, Board
from app.schemas import UserCreate, BoardCreate


def iso_week_str_for_date(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-{w:02d}"


def test_report_summary_and_hours(client: TestClient, session, test_user_token: str, test_board: Board):
    # Calcular semana actual
    today = date.today()
    week_str = iso_week_str_for_date(today)
    year, weeknum = today.isocalendar()[0], today.isocalendar()[1]
    start_date = date.fromisocalendar(year, weeknum, 1)
    mid_date = start_date + timedelta(days=2)

    # Crear tarjetas: una completada (lista Hecho), una vencida (due_date en semana y lista != Hecho), una nueva (created_at en semana)
    list_done = session.query(List).filter(List.board_id == test_board.id, List.title.ilike("Hecho")).first()
    list_todo = session.query(List).filter(List.board_id == test_board.id, List.title.ilike("Por Hacer")).first()

    # Completada
    card_done = Card(title="Done Card", list_id=list_done.id, board_id=test_board.id, user_id=test_board.owner_id)
    card_done.updated_at = datetime.combine(mid_date, datetime.min.time())
    session.add(card_done)

    # Vencida
    card_overdue = Card(title="Overdue Card", list_id=list_todo.id, board_id=test_board.id, user_id=test_board.owner_id, due_date=mid_date)
    session.add(card_overdue)

    # Nueva
    created_dt = datetime.combine(mid_date, datetime.min.time())
    card_new = Card(title="New Card", list_id=list_todo.id, board_id=test_board.id, user_id=test_board.owner_id, created_at=created_dt)
    session.add(card_new)

    session.commit()

    # Añadir worklogs para usuarios (owner)
    wl1 = Worklog(card_id=card_done.id, user_id=test_board.owner_id, date=mid_date, hours=2.5)
    wl2 = Worklog(card_id=card_overdue.id, user_id=test_board.owner_id, date=mid_date, hours=1.5)
    wl3 = Worklog(card_id=card_new.id, user_id=test_board.owner_id, date=mid_date, hours=3.0)
    session.add_all([wl1, wl2, wl3])
    session.commit()

    # Llamar endpoints
    headers = {"Authorization": f"Bearer {test_user_token}"}

    summary_resp = client.get(f"/report/{test_board.id}/summary?week={week_str}", headers=headers)
    assert summary_resp.status_code == 200, summary_resp.text
    summary = summary_resp.json()
    assert summary["completed"]["count"] >= 1
    assert summary["overdue"]["count"] >= 1
    assert summary["new"]["count"] >= 1

    hours_user_resp = client.get(f"/report/{test_board.id}/hours-by-user?week={week_str}", headers=headers)
    assert hours_user_resp.status_code == 200, hours_user_resp.text
    user_data = hours_user_resp.json()["data"]
    assert len(user_data) >= 1
    total_hours = sum(u["total_hours"] for u in user_data)
    assert total_hours == pytest.approx(2.5 + 1.5 + 3.0, rel=1e-3)

    hours_card_resp = client.get(f"/report/{test_board.id}/hours-by-card?week={week_str}", headers=headers)
    assert hours_card_resp.status_code == 200, hours_card_resp.text
    card_data = hours_card_resp.json()["data"]
    # Each card must appear with total_hours
    ids = {c["title"]: c["total_hours"] for c in card_data}
    assert ids.get("Done Card") == pytest.approx(2.5, rel=1e-3)
    assert ids.get("Overdue Card") == pytest.approx(1.5, rel=1e-3)
    assert ids.get("New Card") == pytest.approx(3.0, rel=1e-3)


def test_report_unauthorized_access(client: TestClient, session, test_board: Board):
    # Sin token -> 401
    resp = client.get(f"/report/{test_board.id}/summary?week=2025-01")
    assert resp.status_code == 401


def test_report_invalid_week_format(client: TestClient, session, test_user_token: str, test_board: Board):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    resp = client.get(f"/report/{test_board.id}/summary?week=2025-99", headers=headers)
    assert resp.status_code == 400


def test_report_forbidden_access(client: TestClient, session, test_user, test_user_token: str):
    # Crear otro usuario y su tablero
    from app.models import User as UserModel
    other = UserModel(email="other@example.com", hashed_password="x")
    session.add(other)
    session.commit()
    session.refresh(other)

    from app.models import Board as BoardModel
    b = BoardModel(title="Other Board", owner_id=other.id)
    session.add(b)
    session.commit()

    headers = {"Authorization": f"Bearer {test_user_token}"}
    resp = client.get(f"/report/{b.id}/summary?week=2025-01", headers=headers)
    assert resp.status_code == 403
