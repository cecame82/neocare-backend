# app/routers/labelTemplates.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import database, models, schemas, security

router = APIRouter(
    prefix="/label-templates",
    tags=["LabelTemplates"]
)

# Obtener todas las plantillas
@router.get("/", response_model=list[schemas.LabelTemplate])
def get_label_templates(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    return db.query(models.LabelTemplate).all()

# Crear plantilla nueva
@router.post("/", response_model=schemas.LabelTemplate)
def create_label_template(
    label: schemas.LabelTemplateBase,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    db_label = models.LabelTemplate(name=label.name, color=label.color)
    db.add(db_label)
    db.commit()
    db.refresh(db_label)
    return db_label
