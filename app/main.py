"""
Módulo principal de la API de NeoCare Health.
Configura la aplicación FastAPI, CORS y las rutas de los controladores.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from sqlalchemy.orm import Session

from app.database import engine, SessionLocal, get_db
from app import models
from app.config import settings
from app.logger import get_logger
from app.routers import (
    auth,
    users,
    cards,
    lists,
    boards,
    worklogs,
    labels,
    labelTemplates,
    checklist,
)
from app.routers import report
from app.services.label_template_seed import seed_label_templates
from app.models import Card

# Obtener logger centralizado
logger = get_logger(__name__)

# Crear tablas en la base de datos si no existen
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    debug=settings.DEBUG
)


@app.on_event("startup")
def startup_seed():
    """Semilla de datos al iniciar la aplicación."""
    logger.info("🚀 Startup ejecutándose - Ambiente: %s", settings.ENVIRONMENT)
    db = SessionLocal()
    try:
        seed_label_templates(db)
        logger.info("✅ Plantillas de etiquetas cargadas")
    except Exception as error:
        logger.error("❌ Error en seeding: %s", str(error))
    finally:
        db.close()


# ============================================================
# 🛡️ Middleware de Security Headers (SIN ROMPER CORS)
# ============================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware que agrega headers de seguridad a todas las respuestas."""
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # ❗ NO tocar los headers de CORS aquí
        # FastAPI los maneja automáticamente

        # Agregar headers de seguridad personalizados
        for header, value in settings.SECURITY_HEADERS.items():
            response.headers[header] = value

        return response

app.add_middleware(SecurityHeadersMiddleware)
logger.info("✅ Security headers configurados")


# ============================================================
# 🚧 CORS — DEBE IR DESPUÉS DEL MIDDLEWARE DE SEGURIDAD
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5182",
        "http://127.0.0.1:5182",
        "https://web-production-61c2c.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("✅ CORS configurado correctamente")


# ============================================================
# 📌 Inclusión de Routers
# ============================================================
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(cards.router)
app.include_router(lists.router)
app.include_router(boards.router)
app.include_router(worklogs.router)
app.include_router(report.router)
app.include_router(labels.router)
app.include_router(labelTemplates.router)
app.include_router(checklist.router)


# ============================================================
# 🛠️ Endpoint temporal para arreglar tarjetas antiguas
# ============================================================
@app.post("/fix-cards")
def fix_cards(db: Session = Depends(get_db)):
    cards = db.query(Card).all()

    for c in cards:
        c.board_id = 1   # Tablero César
        c.list_id = 1    # Lista "Por Hacer"
        c.user_id = 1    # Tu usuario

    db.commit()
    return {"status": "ok", "updated": len(cards)}


# ============================================================
# 🧩 Handler universal para OPTIONS — soluciona preflight
# ============================================================
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    return {}


@app.get("/")
def read_root():
    return {"message": "Bienvenidos a la API de NeoCare Health."}
