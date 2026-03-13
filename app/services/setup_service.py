from sqlalchemy.orm import Session
from .. import models 

def create_default_lists(db: Session, board_id: int):
    """
    Crea automáticamente las listas por defecto para el board_id especificado.
    """
    # Define las listas por defecto con su posición
    lists_data = [
        {"title": "Por Hacer", "position": 1},
        {"title": "En Progreso", "position": 2},
        {"title": "Hecho", "position": 3}
    ]
    
    lists_to_create = []
    for data in lists_data:
        # Usa el modelo List
        db_list = models.List(title=data["title"], position=data["position"], board_id=board_id)
        lists_to_create.append(db_list)
        
    db.add_all(lists_to_create)
    db.commit()
    return lists_to_create