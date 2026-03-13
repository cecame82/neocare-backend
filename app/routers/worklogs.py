"""
Módulo de rutas para la gestión de Worklogs (registro de horas).
Maneja la creación, consulta, actualización y borrado de registros de tiempo.
"""
from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app import database, models, schemas, security
from app.services.date_utils import week_str_to_range

router = APIRouter(
    prefix="/worklogs",
    tags=["Worklogs"]
)

@router.get("/card/{card_id}", response_model=List[schemas.WorklogResponse])
def get_worklogs_by_card(
    card_id: int,
    db: Session = Depends(database.get_db),
    _current_user: models.User = Depends(security.get_current_user)
):
    """
    Obtiene todos los registros de horas asociados a una tarjeta específica.
    """
    worklogs = db.query(models.Worklog).filter(models.Worklog.card_id == card_id).all()

    # Enriquecer cada worklog con el título de la tarjeta
    result = []
    for worklog in worklogs:
        card = db.query(models.Card).filter(models.Card.id == worklog.card_id).first()
        result.append({
            "id": worklog.id,
            "card_id": worklog.card_id,
            "card_title": card.title if card else "Tarjeta desconocida",
            "date": worklog.date,
            "hours": worklog.hours,
            "note": worklog.note,
            "user_id": worklog.user_id,
            "created_at": worklog.created_at,
            "updated_at": worklog.updated_at,
        })

    return result

@router.get("/me", response_model=List[schemas.WorklogResponse])
def get_my_worklogs(
    week: Optional[str] = None,
    board_id: Optional[int] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Obtiene la lista de registros de horas del usuario autenticado.
    Puede filtrar por semana usando el parámetro 'week' en formato YYYY-WW.
    Si no se proporciona semana, devuelve la semana actual.
    """
    # Si no se proporciona semana, usar la semana actual
    if not week:
        today = date.today()
        week = today.isocalendar()[0:2]  # (year, week)
        week = f"{week[0]}-{week[1]:02d}"
    
    try:
        start_date, end_date = week_str_to_range(week)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Filtrar worklogs del usuario actual dentro del rango de fechas
    # Si se proporciona board_id, hacer join con Card y filtrar por board
    query = db.query(models.Worklog).join(models.Card).filter(
        models.Worklog.user_id == current_user.id,
        models.Worklog.date >= start_date,
        models.Worklog.date <= end_date
    )

    if board_id:
        query = query.filter(models.Card.board_id == board_id)

    worklogs = query.all()

    # Enriquecer cada worklog con el título de la tarjeta
    result = []
    for worklog in worklogs:
        card = db.query(models.Card).filter(models.Card.id == worklog.card_id).first()
        result.append({
            "id": worklog.id,
            "card_id": worklog.card_id,
            "card_title": card.title if card else "Tarjeta desconocida",
            "date": worklog.date,
            "hours": worklog.hours,
            "note": worklog.note,
            "user_id": worklog.user_id,
            "created_at": worklog.created_at,
            "updated_at": worklog.updated_at,
        })

    return result

@router.post("/", response_model=schemas.Worklog)
def create_worklog(
    worklog: schemas.WorklogCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Crea un nuevo registro de horas vinculado al usuario actual.
    """
    try:
        db_worklog = models.Worklog(**worklog.model_dump(), user_id=current_user.id)
        db.add(db_worklog)
        db.commit()
        db.refresh(db_worklog)
        return db_worklog
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear registro") from exc

@router.patch("/{worklog_id}", response_model=schemas.Worklog)
def update_worklog(
    worklog_id: int,
    worklog_update: schemas.WorklogUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Actualiza un registro de horas existente si el usuario es el propietario.
    Acepta: date (YYYY-MM-DD), hours (float), note (str)
    """
    db_worklog = db.query(models.Worklog).filter(models.Worklog.id == worklog_id).first()
    if not db_worklog:
        raise HTTPException(status_code=404, detail="No encontrado")
    if db_worklog.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")

    try:
        # Obtener solo los campos enviados por el cliente (Pydantic v2)
        update_data = worklog_update.model_dump(exclude_unset=True)

        if "date" in update_data:
            # Parsear la fecha string a date object
            db_worklog.date = date.fromisoformat(update_data["date"]) if update_data["date"] else None
        if "hours" in update_data:
            db_worklog.hours = update_data["hours"]
        if "note" in update_data:
            db_worklog.note = update_data["note"]

        db.commit()
        db.refresh(db_worklog)
        return db_worklog
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar") from exc

@router.delete("/{worklog_id}")
def delete_worklog(
    worklog_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Elimina un registro de horas si el usuario es el propietario.
    """
    db_worklog = db.query(models.Worklog).filter(models.Worklog.id == worklog_id).first()
    if not db_worklog:
        raise HTTPException(status_code=404, detail="No encontrado")
    if db_worklog.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")

    db.delete(db_worklog)
    db.commit()
    return {"detail": "Eliminado"}

