from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta

from app import database, models, schemas, security

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    """
    Devuelve los datos del usuario que está actualmente autenticado.
    """
    return current_user

@router.get("/", response_model=List[schemas.User])
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Obtiene la lista de todos los usuarios registrados (para filtros de UI).
    """
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@router.get("/me/worklogs", response_model=List[schemas.Worklog])
def get_my_worklogs(
    week: Optional[str] = Query(None, description="Semana en formato YYYY-WW (ej: 2025-01)"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Obtiene los registros de horas del usuario actual.
    Si se proporciona 'week', filtra por semana específica.
    Si no se proporciona, devuelve las horas de la semana actual.
    """
    query = db.query(models.Worklog).filter(models.Worklog.user_id == current_user.id)
    
    if week:
        # Parsear semana YYYY-WW
        try:
            year, week_num = map(int, week.split('-'))
            # Calcular fecha de inicio de semana (lunes)
            jan1 = date(year, 1, 1)
            days_offset = (week_num - 1) * 7
            week_start = jan1 + timedelta(days=days_offset - jan1.weekday())
            week_end = week_start + timedelta(days=6)
            
            query = query.filter(
                models.Worklog.date >= week_start,
                models.Worklog.date <= week_end
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de semana inválido. Use YYYY-WW (ej: 2025-01)"
            )
    else:
        # Semana actual por defecto
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        query = query.filter(
            models.Worklog.date >= week_start,
            models.Worklog.date <= week_end
        )
            
    return query.all()
