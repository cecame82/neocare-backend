# app/routers/labels.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app import database, models, schemas, security

router = APIRouter(
    tags=["Labels"],
)

# -----------------------------
# POST /cards/{id}/labels
# -----------------------------
@router.post("/cards/{card_id}/labels", response_model=schemas.Label)
def create_label(
    card_id: int,
    label: schemas.LabelCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    # Buscar tarjeta
    card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    # Validar permisos (dueño del tablero)
    board = db.query(models.Board).filter(models.Board.id == card.board_id).first()
    if board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permisos")

    # Validar que la tarjeta no tenga ya esa etiqueta
    existing_label = (
        db.query(models.Label)
        .filter(models.Label.card_id == card_id, models.Label.name == label.name)
        .first()
    )
    if existing_label:
        raise HTTPException(
            status_code=400,
            detail="La tarjeta ya tiene esta etiqueta"
        )
    
    # Crear etiqueta
    try:
        db_label = models.Label(
            name=label.name,
            color=label.color,
            card_id=card_id
        )
        db.add(db_label)
        db.commit()
        db.refresh(db_label)
        return db_label
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear etiqueta")


# -----------------------------
# GET /cards/{id}/labels
# -----------------------------
@router.get("/cards/{card_id}/labels", response_model=list[schemas.Label])
def get_labels_for_card(
    card_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    board = db.query(models.Board).filter(models.Board.id == card.board_id).first()
    if board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permisos")

    return db.query(models.Label).filter(models.Label.card_id == card_id).all()


# -----------------------------
# DELETE /labels/{id}
# -----------------------------
@router.delete("/labels/{label_id}")
def delete_label(
    label_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    label = db.query(models.Label).filter(models.Label.id == label_id).first()
    if not label:
        raise HTTPException(status_code=404, detail="Etiqueta no encontrada")

    card = db.query(models.Card).filter(models.Card.id == label.card_id).first()
    board = db.query(models.Board).filter(models.Board.id == card.board_id).first()

    if board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sin permisos")

    db.delete(label)
    db.commit()

    from fastapi import Response
    return Response(status_code=204)
