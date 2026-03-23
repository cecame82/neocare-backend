"""
Módulo de rutas para la gestión de listas.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import database, models, schemas, security

router = APIRouter(
    prefix="/lists",
    tags=["Lists"]
)

# ACEPTA /lists Y /lists/
@router.get("", response_model=List[schemas.ListSchema])
@router.get("/", response_model=List[schemas.ListSchema])
def read_lists_for_board(
    board_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Obtiene todas las listas de un tablero."""
    board = db.query(models.Board).filter(
        models.Board.id == board_id
    ).first()
    if not board:
        raise HTTPException(status_code=404, detail="Tablero no encontrado")

    if board.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para ver las listas de este tablero"
        )

    lists = (
        db.query(models.List)
        .options(joinedload(models.List.cards))
        .filter(models.List.board_id == board_id)
        .order_by(models.List.position)
        .all()
    )

    return lists
