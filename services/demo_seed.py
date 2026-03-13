# services/demo_seed.py
"""Script para poblar la base de datos con datos demo médicos."""

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Board, List, Card, Worklog, Label, LabelTemplate, Subtask
from app.security import pwd_context
from datetime import date, datetime

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def seed_demo_data():
    db: Session = SessionLocal()
    try:
        # Crear usuario demo
        demo_user = User(
            email="demo@neocare.com",
            hashed_password=hash_password("demo123"),
            is_active=True
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)

        # Crear tablero
        board = Board(
            title="NeoCare Health Dashboard",
            owner_id=demo_user.id
        )
        db.add(board)
        db.commit()
        db.refresh(board)

        # Crear listas
        lists_data = [
            {"title": "Pendientes", "position": 0},
            {"title": "En Progreso", "position": 1},
            {"title": "Completadas", "position": 2}
        ]
        lists = []
        for list_data in lists_data:
            list_obj = List(
                title=list_data["title"],
                position=list_data["position"],
                board_id=board.id
            )
            db.add(list_obj)
            db.commit()
            db.refresh(list_obj)
            lists.append(list_obj)

        # Crear plantillas de etiquetas si no existen
        label_templates = [
            {"name": "Urgente", "color": "red"},
            {"name": "Consulta", "color": "blue"},
            {"name": "Tratamiento", "color": "green"},
            {"name": "Seguimiento", "color": "yellow"}
        ]
        for template in label_templates:
            existing = db.query(LabelTemplate).filter_by(name=template["name"]).first()
            if not existing:
                db.add(LabelTemplate(**template))
        db.commit()

        # Crear tarjetas con temas médicos
        cards_data = [
            {
                "title": "Revisar historial clínico de paciente Juan Pérez",
                "description": "Paciente con hipertensión, revisar medicamentos y citas previas.",
                "order": 0,
                "list_id": lists[0].id,
                "labels": ["Consulta", "Seguimiento"],
                "subtasks": ["Revisar presión arterial", "Actualizar medicamentos", "Programar cita de control"]
            },
            {
                "title": "Administrar vacuna contra gripe",
                "description": "Vacuna estacional para personal médico y pacientes de riesgo.",
                "order": 1,
                "list_id": lists[1].id,
                "labels": ["Tratamiento"],
                "subtasks": ["Verificar stock de vacunas", "Programar sesiones de vacunación", "Registrar dosis administradas"]
            },
            {
                "title": "Actualizar protocolos de emergencia",
                "description": "Revisar y actualizar procedimientos para manejo de emergencias cardíacas.",
                "order": 2,
                "list_id": lists[1].id,
                "labels": ["Urgente"],
                "subtasks": ["Revisar guías actuales", "Entrenar al personal", "Actualizar equipos"]
            },
            {
                "title": "Cita de seguimiento con paciente María López",
                "description": "Seguimiento post-operatorio después de cirugía de rodilla.",
                "order": 0,
                "list_id": lists[2].id,
                "labels": ["Consulta", "Seguimiento"],
                "subtasks": ["Evaluar recuperación", "Ajustar fisioterapia", "Programar próxima cita"]
            }
        ]

        for card_data in cards_data:
            card = Card(
                title=card_data["title"],
                description=card_data["description"],
                order=card_data["order"],
                list_id=card_data["list_id"],
                board_id=board.id,
                user_id=demo_user.id
            )
            db.add(card)
            db.commit()
            db.refresh(card)

            # Agregar etiquetas
            for label_name in card_data["labels"]:
                template = db.query(LabelTemplate).filter_by(name=label_name).first()
                if template:
                    label = Label(
                        name=template.name,
                        color=template.color,
                        card_id=card.id
                    )
                    db.add(label)

            # Agregar subtareas
            for subtask_title in card_data["subtasks"]:
                subtask = Subtask(
                    title=subtask_title,
                    completed=False,
                    card_id=card.id
                )
                db.add(subtask)

            db.commit()

        # Agregar worklogs de ejemplo
        worklogs_data = [
            {"card_title": "Revisar historial clínico de paciente Juan Pérez", "date": date.today(), "hours": 2.5, "note": "Revisión inicial completada"},
            {"card_title": "Administrar vacuna contra gripe", "date": date.today(), "hours": 1.0, "note": "Sesión de vacunación matutina"},
            {"card_title": "Cita de seguimiento con paciente María López", "date": date(2024, 1, 10), "hours": 1.5, "note": "Evaluación post-operatoria"}
        ]

        for wl_data in worklogs_data:
            card = db.query(Card).filter_by(title=wl_data["card_title"]).first()
            if card:
                worklog = Worklog(
                    card_id=card.id,
                    user_id=demo_user.id,
                    date=wl_data["date"],
                    hours=wl_data["hours"],
                    note=wl_data["note"]
                )
                db.add(worklog)

        db.commit()
        print("Datos demo poblados exitosamente.")
        print("Usuario demo: demo@neocare.com")
        print("Contraseña: demo123")

    except Exception as e:
        db.rollback()
        print(f"Error al poblar datos demo: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()