from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from sqlalchemy.orm import Session
from . import database, models

load_dotenv()

# ============================
# CONFIGURACIÓN
# ============================

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("No se ha configurado la SECRET_KEY.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================
# HASHING
# ============================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    truncated_password = password[:72]
    return pwd_context.hash(truncated_password)

# ============================
# TOKEN
# ============================

def create_access_token(data: dict, expires_time: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_time or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        return None

# ============================
# ESQUEMAS DE SEGURIDAD
# ============================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
bearer_scheme = HTTPBearer()

# ============================
# OBTENER USUARIO ACTUAL
# ============================

def get_current_user(token: str = Depends(bearer_scheme), db: Session = Depends(database.get_db)):
    """
    Obtiene el usuario actual a partir del token Bearer.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Acepta token.credentials (HTTPBearer) o token directo (otros clientes)
    token_str = token.credentials if hasattr(token, "credentials") else token
    payload = decode_access_token(token_str)

    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception

    return user


