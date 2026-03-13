#label_template_seed.py

from sqlalchemy.orm import Session
from app import models

# Plantillas por defecto que quieras tener
DEFAULT_LABEL_TEMPLATES = [
    {"name": "Urgente", "color": "#FF4D4D"},
    {"name": "Dependencia externa", "color": "orange"},
    {"name": "IA", "color": "#66B2FF"},
    {"name": "QA pendiente", "color": "#006600"}, 
]

def seed_label_templates(db: Session):
    """
    Sincroniza la tabla LabelTemplate con DEFAULT_LABEL_TEMPLATES:
    - Si existe la plantilla, actualiza el color.
    - Si no existe, la crea.
    - Elimina duplicados o plantillas que ya no están en DEFAULT_LABEL_TEMPLATES.
    """
    # Traer todas las plantillas existentes
    existing_templates = {lt.name: lt for lt in db.query(models.LabelTemplate).all()}

    # Crear o actualizar según DEFAULT_LABEL_TEMPLATES
    for template in DEFAULT_LABEL_TEMPLATES:
        name = template["name"]
        color = template["color"]

        if name in existing_templates:
            lt = existing_templates[name]
            if lt.color != color:
                lt.color = color  # Reescribimos color
                db.add(lt)
        else:
            db.add(models.LabelTemplate(name=name, color=color))

    # 3️⃣ Opcional: eliminar plantillas que ya no estén en DEFAULT_LABEL_TEMPLATES
    default_names = {t["name"] for t in DEFAULT_LABEL_TEMPLATES}
    for name, lt in existing_templates.items():
        if name not in default_names:
            db.delete(lt)

    db.commit()
    print("Label templates sincronizadas correctamente")
