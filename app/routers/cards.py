"""
Módulo de rutas para la gestión de Tarjetas (Cards).
Maneja la creación, lectura, actualización, eliminación y movimiento (Drag & Drop).
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app import database, models, schemas, security

router = APIRouter(
    prefix="/cards",
    tags=["Cards"],
)

@router.post("/", response_model=schemas.Card)
def create_card(
    card: schemas.CardCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Crea una tarjeta y la pone al final de la lista."""
    board = db.query(models.Board).filter(models.Board.id == card.board_id).first()
    if not board:
        # Tablero inexistente -> Bad Request (según tests)
        raise HTTPException(status_code=400, detail="Tablero no encontrado")
    if board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para este tablero")

    last_card = db.query(models.Card).filter(
        models.Card.list_id == card.list_id
    ).order_by(models.Card.order.desc()).first()
    
    new_order = (last_card.order + 1) if last_card else 0

    try:
        db_card = models.Card(
            **card.model_dump(),
            order=new_order,
            user_id=current_user.id
        )
        db.add(db_card)
        db.commit()
        db.refresh(db_card)
        return db_card
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear la tarjeta")

@router.get("/", response_model=List[schemas.Card])
def read_cards(
    board_id: int,
    responsible_id: Optional[int] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Obtiene las tarjetas de un tablero, opcionalmente filtradas por responsable."""
    board = db.query(models.Board).filter(models.Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Tablero no encontrado")
    
    # Validación simple de propiedad (se podría expandir a equipos compartidos)
    if board.owner_id != current_user.id:
         raise HTTPException(status_code=403, detail="No tienes permiso")

    query = db.query(models.Card).filter(models.Card.board_id == board_id)

    # --- FILTRO POR RESPONSABLE ---
    if responsible_id is not None:
        query = query.filter(models.Card.user_id == responsible_id)
    # ------------------------------

    return query.all()

@router.patch("/{card_id}", response_model=schemas.Card)
def update_card(
    card_id: int,
    card_update: schemas.CardUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    db_card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    
    # Validar permisos (dueño del tablero)
    board = db.query(models.Board).filter(models.Board.id == db_card.board_id).first()
    if board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso")

    update_data = card_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_card, key, value)

    try:
        db.commit()
        db.refresh(db_card)
        return db_card
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar")

@router.patch("/{card_id}/move", response_model=schemas.Card)
def move_card(
    card_id: int,
    move_data: schemas.CardMove,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Mueve una tarjeta a otra lista o reordena en la misma.
    Ajusta automáticamente el orden de las demás tarjetas.
    """
    db_card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    old_list_id = db_card.list_id
    new_list_id = move_data.list_id
    old_order = db_card.order
    new_order = move_data.order

    # Validar permisos
    board = db.query(models.Board).filter(models.Board.id == db_card.board_id).first()
    if board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso")

    try:
        if old_list_id == new_list_id:
            if new_order > old_order:
                db.query(models.Card).filter(
                    models.Card.list_id == old_list_id,
                    models.Card.order > old_order,
                    models.Card.order <= new_order
                ).update({"order": models.Card.order - 1}, synchronize_session=False)
            elif new_order < old_order:
                db.query(models.Card).filter(
                    models.Card.list_id == old_list_id,
                    models.Card.order >= new_order,
                    models.Card.order < old_order
                ).update({"order": models.Card.order + 1}, synchronize_session=False)
        else:
            db.query(models.Card).filter(
                models.Card.list_id == old_list_id,
                models.Card.order > old_order
            ).update({"order": models.Card.order - 1}, synchronize_session=False)
            db.query(models.Card).filter(
                models.Card.list_id == new_list_id,
                models.Card.order >= new_order
            ).update({"order": models.Card.order + 1}, synchronize_session=False)

        db_card.list_id = new_list_id
        db_card.order = new_order
        db.commit()
        db.refresh(db_card)
        return db_card
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al mover")

@router.delete("/{card_id}")
def delete_card(
    card_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    db_card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not db_card: raise HTTPException(status_code=404)
    
    old_list_id = db_card.list_id
    old_order = db_card.order

    db.delete(db_card)
    db.query(models.Card).filter(
        models.Card.list_id == old_list_id,
        models.Card.order > old_order
    ).update({"order": models.Card.order - 1}, synchronize_session=False)
    
    db.commit()
    return {"message": "Tarjeta eliminada"}
