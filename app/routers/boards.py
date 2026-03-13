"""
Módulo de rutas para la gestión de Tableros (Boards).
Permite crear nuevos tableros y listar los existentes para el usuario autenticado.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import database, models, schemas, security
from app.services.setup_service import create_default_lists
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/boards",
    tags=["Boards"],
    dependencies=[Depends(security.get_current_user)]
)

@router.post("/", response_model=schemas.BoardGet)
def create_board(
    board_data: schemas.BoardCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Crea un nuevo tablero para el usuario actual e inicializa sus listas por defecto.
    """
    logger.info(
        "📋 Creando nuevo tablero '%s' para usuario %s",
        board_data.title,
        current_user.email
    )

    # 1. Crear el nuevo objeto Board
    db_board = models.Board(title=board_data.title, owner_id=current_user.id)
    db.add(db_board)
    db.commit()
    db.refresh(db_board)

    # 2. AUTOMATIZACIÓN: Llamar al servicio para crear las listas por defecto
    create_default_lists(db, db_board.id)

    logger.info("✅ Tablero creado con ID %s", db_board.id)
    return db_board

@router.get("/", response_model=List[schemas.BoardGet])
def read_boards(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Retorna la lista de todos los tableros que pertenecen al usuario autenticado.
    """
    boards = db.query(models.Board).filter(models.Board.owner_id == current_user.id).all()
    logger.debug("📊 Tableros encontrados para %s: %d", current_user.email, len(boards))
    return boards
