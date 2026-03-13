"""
Módulo de rutas para la gestión de Checklist Items.
Permite crear, actualizar y eliminar items de checklist en tarjetas.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app import database, models, schemas, security

router = APIRouter(
    prefix="/subtasks",
    tags=["Subtasks"],
)


@router.post("/cards/{card_id}", response_model=schemas.Subtask)
def create_subtask(
    card_id: int,
    item: schemas.SubtaskCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Crear una nueva subtask para una tarjeta."""
    card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    board = db.query(models.Board).filter(models.Board.id == card.board_id).first()
    if not board or board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para esta tarjeta")

    try:
        db_item = models.Subtask(
            card_id=card_id,
            title=item.title,
            completed=item.completed,
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear subtask") from exc


@router.get("/cards/{card_id}", response_model=List[schemas.Subtask])
def get_subtasks(
    card_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Obtener todas las subtasks de una tarjeta."""
    card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    board = db.query(models.Board).filter(models.Board.id == card.board_id).first()
    if not board or board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")

    return db.query(models.Subtask).filter(models.Subtask.card_id == card_id).all()


@router.patch("/{item_id}", response_model=schemas.Subtask)
def update_subtask(
    item_id: int,
    update_data: schemas.SubtaskUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Actualizar una subtask."""
    item = db.query(models.Subtask).filter(models.Subtask.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    card = db.query(models.Card).filter(models.Card.id == item.card_id).first()
    board = db.query(models.Board).filter(models.Board.id == card.board_id).first()
    if not board or board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")

    try:
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(item, key, value)

        db.commit()
        db.refresh(item)
        return item
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar subtask") from exc


@router.delete("/{item_id}")
def delete_subtask(
    item_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Eliminar una subtask."""
    item = db.query(models.Subtask).filter(models.Subtask.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    card = db.query(models.Card).filter(models.Card.id == item.card_id).first()
    board = db.query(models.Board).filter(models.Board.id == card.board_id).first()
    if not board or board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")

    try:
        db.delete(item)
        db.commit()
        return {"message": "Subtask eliminada"}
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar subtask") from exc


