"""Módulo de rutas para generar reportes semanales y análisis de horas."""
from datetime import datetime, time, date as date_class
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import database, models
from app.security import get_current_user
from app.services.date_utils import week_str_to_range

router = APIRouter(prefix="/report", tags=["Report"])


def week_bounds_to_datetimes(start_date, end_date):
    """Convertir fechas de semana a datetimes con horas min/max."""
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)
    return start_dt, end_dt


@router.get("/{board_id}/summary")
def get_summary(
    board_id: int,
    week: str = Query(..., description="Formato YYYY-WW"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Obtener resumen semanal de tarjetas completadas, vencidas y nuevas."""
    board = db.query(models.Board).filter(
        models.Board.id == board_id
    ).first()
    if not board or board.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="No autorizado para ver este tablero"
        )

    try:
        start_date, end_date = week_str_to_range(week)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    start_dt, end_dt = week_bounds_to_datetimes(start_date, end_date)
    print(f"📊 [Backend] Summary - Semana: {week}, Start: {start_date}, End: {end_date}")

    # Completadas: cards en lista 'Hecho' con updated_at en rango
    done_list = db.query(models.List).filter(
        models.List.board_id == board_id,
        models.List.title.ilike('Hecho')
    ).first()
    if done_list:
        # Count cards that were completed during the week.
        # Consider cards that either were updated to 'Hecho' during the week
        # or were created in the week already in 'Hecho'. This covers cases
        # where updated_at may be null or not reflect the move.
        completed_q = db.query(models.Card).filter(
            models.Card.list_id == done_list.id
        )
        completed_count = completed_q.filter(
            (
                models.Card.updated_at.is_not(None)
                & (models.Card.updated_at >= start_dt)
                & (models.Card.updated_at <= end_dt)
            )
            | (
                models.Card.created_at.is_not(None)
                & (models.Card.created_at >= start_dt)
                & (models.Card.created_at <= end_dt)
            )
        ).count()
    else:
        completed_count = 0

    # Vencidas: Tarjetas con due_date < fin de la semana seleccionada en "Por hacer" o "En progreso"
    # Solo mostrar tareas que estén dentro del rango de la semana
    todo_list = db.query(models.List).filter(
        models.List.board_id == board_id,
        models.List.title.ilike('Por hacer')
    ).first()
    in_progress_list = db.query(models.List).filter(
        models.List.board_id == board_id,
        models.List.title.ilike('En progreso')
    ).first()

    overdue_q = db.query(models.Card).filter(
        models.Card.board_id == board_id,
        models.Card.due_date.is_not(None),
        models.Card.due_date < end_date,  # Due date antes del fin de la semana seleccionada
        models.Card.created_at <= end_dt  # Tarjeta debe haber sido creada antes o durante la semana
    )

    list_ids = []
    if todo_list:
        list_ids.append(todo_list.id)
    if in_progress_list:
        list_ids.append(in_progress_list.id)

    if list_ids:
        overdue_q = overdue_q.filter(models.Card.list_id.in_(list_ids))
    else:
        overdue_q = overdue_q.filter(False)

    overdue_count = overdue_q.count()

    # Nuevas: created_at en rango
    new_q = db.query(models.Card).filter(
        models.Card.created_at.is_not(None),
        models.Card.created_at >= start_dt,
        models.Card.created_at <= end_dt,
        models.Card.board_id == board_id
    )
    new_count = new_q.count()
    
    print(f"📊 [Backend] Resultados - Completadas: {completed_count if done_list else 0}, Vencidas: {overdue_count}, Nuevas: {new_count}")

    def short_list_from_query(q):
        """Construir lista corta de tarjetas con detalles."""
        items = []
        for c in q.limit(10).all():
            items.append({
                "id": c.id,
                "title": c.title,
                "responsible": c.user.email if c.user else None,
                "state": c.list.title if c.list else None,
            })
        return items

    if done_list:
        completed_items = short_list_from_query(
            completed_q.order_by(models.Card.updated_at.desc())
        )
    else:
        completed_items = []
    overdue_items = short_list_from_query(
        overdue_q.order_by(models.Card.due_date.asc())
    )
    new_items = short_list_from_query(
        new_q.order_by(models.Card.created_at.desc())
    )

    return {
        "week": week,
        "start_date": start_date,
        "end_date": end_date,
        "completed": {"count": completed_count, "items": completed_items},
        "overdue": {"count": overdue_count, "items": overdue_items},
        "new": {"count": new_count, "items": new_items},
    }


@router.get("/{board_id}/hours-by-user")
def hours_by_user(
    board_id: int,
    week: str = Query(..., description="Formato YYYY-WW"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Obtener horas totales por usuario en una semana específica."""
    board = db.query(models.Board).filter(
        models.Board.id == board_id
    ).first()
    if not board or board.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="No autorizado para ver este tablero"
        )

    try:
        start_date, end_date = week_str_to_range(week)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    q = (
        db.query(
            models.Worklog.user_id.label("user_id"),
            func.coalesce(func.sum(models.Worklog.hours), 0).label(
                "total_hours"
            ),
            func.count(models.Worklog.card_id.distinct()).label("tasks_count"),
        )
        .join(models.Card, models.Worklog.card_id == models.Card.id)
        .filter(models.Card.board_id == board_id)
        .filter(
            models.Worklog.date >= start_date,
            models.Worklog.date <= end_date
        )
        .group_by(models.Worklog.user_id)
    )

    results = []
    for row in q.all():
        user = db.query(models.User).filter(
            models.User.id == row.user_id
        ).first()
        results.append({
            "user_id": row.user_id,
            "user_email": user.email if user else None,
            "total_hours": float(row.total_hours) if row.total_hours is not None else 0.0,
            "tasks_count": int(row.tasks_count),
        })

    return {"week": week, "start_date": start_date, "end_date": end_date, "data": results}


@router.get("/{board_id}/hours-by-card")
def hours_by_card(
    board_id: int,
    week: str = Query(..., description="Formato YYYY-WW"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    order_desc: Optional[bool] = Query(True, description="Ordenar por horas"),
):
    """Obtener horas totales por tarjeta en una semana específica."""
    board = db.query(models.Board).filter(
        models.Board.id == board_id
    ).first()
    if not board or board.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="No autorizado para ver este tablero"
        )

    try:
        start_date, end_date = week_str_to_range(week)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    start_dt, end_dt = week_bounds_to_datetimes(start_date, end_date)

    # Solo mostrar tarjetas que tienen worklogs EN la semana seleccionada
    q = (
        db.query(
            models.Card.id.label("card_id"),
            models.Card.title.label("title"),
            models.Card.user_id.label("responsible_id"),
            models.List.title.label("state"),
            func.coalesce(func.sum(models.Worklog.hours), 0).label(
                "total_hours"
            ),
        )
        .outerjoin(models.Worklog, models.Worklog.card_id == models.Card.id)
        .outerjoin(models.List, models.Card.list_id == models.List.id)
        .filter(models.Card.board_id == board_id)
        .filter(
            # Solo mostrar si tiene worklogs en el rango de fechas
            (models.Worklog.date >= start_date) &
            (models.Worklog.date <= end_date) &
            (models.Worklog.id.is_not(None))  # Asegurar que existe worklog
        )
        .group_by(
            models.Card.id,
            models.Card.title,
            models.Card.user_id,
            models.List.title
        )
    )

    if order_desc:
        q = q.order_by(func.sum(models.Worklog.hours).desc())
    else:
        q = q.order_by(func.sum(models.Worklog.hours).asc())

    results = []
    for row in q.all():
        user = (
            db.query(models.User).filter(models.User.id == row.responsible_id)
            .first()
            if row.responsible_id
            else None
        )
        results.append({
            "card_id": row.card_id,
            "title": row.title,
            "responsible": user.email if user else None,
            "state": row.state,
            "total_hours": float(row.total_hours)
            if row.total_hours is not None
            else 0.0,
        })

    print(f"📊 [Backend] Hours-by-card - Semana: {week}, Tarjetas encontradas: {len(results)}")
    return {
        "week": week,
        "start_date": start_date,
        "end_date": end_date,
        "data": results
    }
