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
    report,
)
from app.services.label_template_seed import seed_label_templates
from app.models import Card

# ------------------------------------------------------------
# LOGGER
# ------------------------------------------------------------
logger = get_logger(__name__)

# ------------------------------------------------------------
# CREAR TABLAS
# ------------------------------------------------------------
models.Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------
# CREAR APP
# ------------------------------------------------------------
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    debug=settings.DEBUG
)

# ------------------------------------------------------------
# STARTUP: SEED
# ------------------------------------------------------------
@app.on_event("startup")
def startup_seed():
    logger.info("🚀 Startup ejecutándose - Ambiente: %s", settings.ENVIRONMENT)
    db = SessionLocal()
    try:
        seed_label_templates(db)
        logger.info("✅ Plantillas de etiquetas cargadas")
    except Exception as error:
        logger.error("❌ Error en seeding: %s", str(error))
    finally:
        db.close()

# ------------------------------------------------------------
# SECURITY HEADERS (NO ROMPER CORS)
# ------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # No tocar CORS aquí
        for header, value in settings.SECURITY_HEADERS.items():
            # Evitar sobrescribir headers CORS
            if header.lower().startswith("access-control-"):
                continue
            response.headers[header] = value

        return response

app.add_middleware(SecurityHeadersMiddleware)
logger.info("✅ Security headers configurados")

# ------------------------------------------------------------
# CORS — CONFIGURACIÓN CORRECTA
# ------------------------------------------------------------

# Asegurar que los orígenes correctos están permitidos
origins = [
    "http://localhost:5173",
    "https://neocare-frontend-production.up.railway.app",
]

# Si settings.CORS_ORIGINS está vacío o incorrecto, usamos los buenos
if not settings.CORS_ORIGINS:
    settings.CORS_ORIGINS = origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("✅ CORS configurado correctamente con: %s", settings.CORS_ORIGINS)

# ------------------------------------------------------------
# ROUTERS
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# FIX CARDS (TEMPORAL)
# ------------------------------------------------------------
@app.post("/fix-cards")
def fix_cards(db: Session = Depends(get_db)):
    cards = db.query(Card).all()

    for c in cards:
        c.board_id = 1
        c.list_id = 1
        c.user_id = 1

    db.commit()
    return {"status": "ok", "updated": len(cards)}

# ------------------------------------------------------------
# HANDLER UNIVERSAL PARA OPTIONS (PREFLIGHT)
# ------------------------------------------------------------
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    return {}

# ------------------------------------------------------------
# ROOT
# ------------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "Bienvenidos a la API de NeoCare Health."}

