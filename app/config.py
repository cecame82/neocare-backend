"""
Módulo de configuración centralizado para NeoCare Health API.
Maneja todas las variables de entorno y configuraciones según el ambiente.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# ------------------------------------------------------------
# Cargar .env SOLO en local (no en producción)
# ------------------------------------------------------------
if os.path.exists(".env"):
    load_dotenv()


class Settings:
    """Configuración centralizada de la aplicación."""
    
    # --- ENTORNO ---
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # --- BASE DE DATOS ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    if not DATABASE_URL:
        raise ValueError("❌ DATABASE_URL no configurada en variables de entorno")
    
    # --- SEGURIDAD JWT ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    if not SECRET_KEY:
        raise ValueError("❌ SECRET_KEY no configurada en variables de entorno")
    
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_IN: int = int(os.getenv("JWT_EXPIRES_IN", "60"))  # minutos
    
    # --- CORS ---
    CORS_ORIGINS: list[str] = [
        # PUERTO REAL DE TU FRONTEND (VITE)
        "http://localhost:5174",
        "http://127.0.0.1:5174",

        # Puertos típicos de Vite
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:5180",
        "http://127.0.0.1:5180",
        "http://localhost:5178",
        "http://127.0.0.1:5178",

        # Puertos típicos de React CRA
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # Agregar orígenes personalizados desde .env (separados por comas)
    CUSTOM_ORIGINS: Optional[str] = os.getenv("CORS_ORIGINS", None)
    if CUSTOM_ORIGINS:
        CORS_ORIGINS.extend([origin.strip() for origin in CUSTOM_ORIGINS.split(",")])
    
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_HEADERS: list[str] = ["Content-Type", "Authorization"]
    
    # --- SECURITY HEADERS ---
    SECURITY_HEADERS: dict = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": (
            "max-age=31536000; includeSubDomains" 
            if ENVIRONMENT == "production" 
            else ""
        ),
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' https://fastapi.tiangolo.com; "
            "connect-src 'self'"
        ),
    }
    SECURITY_HEADERS = {k: v for k, v in SECURITY_HEADERS.items() if v}
    
    # --- API ---
    API_TITLE: str = "NeoCare Health API"
    API_DESCRIPTION: str = "API de gestión interna para NeoCare Health"
    API_VERSION: str = "1.0.0"
    
    # --- LOGS ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO" if not DEBUG else "DEBUG")
    
    # --- RATE LIMITING ---
    AUTH_RATE_LIMIT_ATTEMPTS: int = int(os.getenv("AUTH_RATE_LIMIT_ATTEMPTS", "5"))
    AUTH_RATE_LIMIT_MINUTES: int = int(os.getenv("AUTH_RATE_LIMIT_MINUTES", "15"))
    
    # --- SETTINGS ADICIONALES ---
    MAX_PASSWORD_LENGTH: int = 72  # Límite de bcrypt
    
    def __repr__(self) -> str:
        return f"<Settings env={self.ENVIRONMENT} db={self.DATABASE_URL.split('/')[-1]}>"


# Instancia global de configuración
settings = Settings()
<<<<<<< HEAD


=======
>>>>>>> abb45ec6c71b49776bcb1386ae95eab333cf6f1c
