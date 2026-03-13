"""
Módulo de autenticación.
Maneja el registro de usuarios, inicio de sesión y generación de tokens.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import database, models, schemas, security
from app.services.setup_service import create_default_lists
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

# Simple in-memory rate limiting (en producción usar Redis)
auth_attempts = {}

router = APIRouter(prefix="/auth", tags=["Auth"])


def check_rate_limit(email: str) -> bool:
    """Verifica si el email ha excedido el límite de intentos de login."""
    now = datetime.now()

    if email not in auth_attempts:
        auth_attempts[email] = []

    # Limpiar intentos antiguos
    auth_attempts[email] = [
        attempt for attempt in auth_attempts[email]
        if now - attempt < timedelta(minutes=settings.AUTH_RATE_LIMIT_MINUTES)
    ]

    if len(auth_attempts[email]) >= settings.AUTH_RATE_LIMIT_ATTEMPTS:
        logger.warning("⚠️ Rate limit: Demasiados intentos de login para %s", email)
        return False

    auth_attempts[email].append(now)
    return True


# ---------------------------------------------------------
#  REGISTRO
# ---------------------------------------------------------
@router.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Registra un nuevo usuario y crea automáticamente su tablero principal y listas.
    """
    logger.info("📝 Intento de registro con email: %s", user.email)

    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        logger.warning("⚠️ Intento de registro duplicado para: %s", user.email)
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    hashed_pwd = security.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Crear tablero por defecto
    default_board = models.Board(title="Tablero Principal", owner_id=new_user.id)
    db.add(default_board)
    db.commit()

    # IMPORTANTE: Refrescar para obtener el ID del tablero creado
    db.refresh(default_board)

    # AUTOMATIZACIÓN: Crear listas por defecto para el nuevo tablero
    create_default_lists(db, default_board.id)

    logger.info("✅ Usuario registrado exitosamente: %s", user.email)
    return new_user


# ---------------------------------------------------------
#  LOGIN ORIGINAL (Swagger, OAuth2, form-data)
# ---------------------------------------------------------
@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """
    Verifica las credenciales y devuelve un token de acceso JWT.
    Este endpoint usa OAuth2PasswordRequestForm (form-data).
    Swagger lo usa automáticamente.
    """
    email = form_data.username
    logger.info("🔐 Intento de login para: %s", email)

    # Verificar rate limit
    if not check_rate_limit(email):
        logger.error("❌ Rate limit excedido para: %s", email)
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados intentos. Intente en {settings.AUTH_RATE_LIMIT_MINUTES} minutos"
        )

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        logger.warning("⚠️ Credenciales inválidas para: %s", email)
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    access_token = security.create_access_token(data={"sub": user.email})
    logger.info("✅ Login exitoso para: %s", email)
    return {"access_token": access_token, "token_type": "bearer"}


# ---------------------------------------------------------
#  LOGIN JSON (para el frontend)
# ---------------------------------------------------------
@router.post("/login-json", response_model=schemas.Token)
def login_json(credentials: schemas.LoginRequest, db: Session = Depends(database.get_db)):
    """
    Login usando JSON (email + password).
    Este endpoint es para el frontend.
    """
    email = credentials.email
    password = credentials.password

    logger.info("🔐 Login JSON para: %s", email)

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not security.verify_password(password, user.hashed_password):
        logger.warning("⚠️ Credenciales inválidas para: %s", email)
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    access_token = security.create_access_token(data={"sub": user.email})
    logger.info("✅ Login JSON exitoso para: %s", email)

    return {"access_token": access_token, "token_type": "bearer"}


# ---------------------------------------------------------
#  RESET TEMPORAL DE CONTRASEÑA (solo para uso interno)
# ---------------------------------------------------------
@router.post("/force-reset")
def force_reset(db: Session = Depends(database.get_db)):
    """
    Ruta temporal para restablecer la contraseña del usuario con ID = 1.
    Después de usarla, BORRARLA.
    """
    logger.info("🔧 Ejecutando reseteo de contraseña para user_id = 1")

    user = db.query(models.User).filter(models.User.id == 1).first()
    if not user:
        logger.error("❌ Usuario con ID 1 no encontrado")
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    new_password = "Cesar1234"
    user.hashed_password = security.get_password_hash(new_password)
    db.commit()

    logger.info("✅ Contraseña actualizada correctamente para user_id = 1")
    return {"status": "ok", "message": "Contraseña actualizada a Cesar1234"}



