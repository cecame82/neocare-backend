"""
Logger centralizado para la aplicación con diferentes niveles de log.
Proporciona configuración consistente en todos los routers y servicios.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings

# Crear directorio de logs si no existe
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configurar logger
logger = logging.getLogger("neocare")

# Limpiar handlers previos
logger.handlers.clear()

# Determinar nivel según configuración
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

log_level = LOG_LEVELS.get(settings.LOG_LEVEL.upper(), logging.INFO)
logger.setLevel(log_level)

# Formatter
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Handler para consola
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(log_level)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Handler para archivo (solo en producción)
if settings.ENVIRONMENT == "production":
    file_handler = RotatingFileHandler(
        LOG_DIR / "neocare.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# No propagar a root logger
logger.propagate = False


def get_logger(name: str = "neocare") -> logging.Logger:
    """Obtener logger configurado."""
    return logging.getLogger(name)
