"""
Módulo de configuración de la Base de Datos.
Maneja la conexión con PostgreSQL, la creación automática de la DB si no existe
y la gestión de sesiones de SQLAlchemy.
"""
import os
import psycopg2
from sqlalchemy import create_engine
# Use the modern import location for SQLAlchemy 2.x
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("No se ha encontrado la variable DATABASE_URL en el archivo .env")

# --- LÓGICA DE CREACIÓN DE BASE DE DATOS AUTOMÁTICA ---
try:
    # 1. Extraer detalles de conexión de la URL
    base_url_no_db = SQLALCHEMY_DATABASE_URL.rsplit('/', 1)[0]
    db_name = SQLALCHEMY_DATABASE_URL.rsplit('/', 1)[1]

    user_pass = base_url_no_db.split('//')[1].split('@')[0]
    user = user_pass.split(':')[0]
    password = user_pass.split(':')[1]

    host_port = base_url_no_db.split('@')[1].split(':')[0:2]
    host = host_port[0]
    port = host_port[1]

    # 2. Conexión temporal a 'postgres' para crear la DB propia
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname='postgres'
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # 3. Comprobar si existe la base de datos
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
    exists = cursor.fetchone()

    # 4. Crear si no existe
    if not exists:
        print(f"PostgreSQL: Creando la base de datos: {db_name}...")
        cursor.execute(f"CREATE DATABASE {db_name}")
        print(f"PostgreSQL: Base de datos '{db_name}' creada exitosamente.")
    else:
        print(f"PostgreSQL: Base de datos '{db_name}' ya existe. Continuando...")

    cursor.close()
    conn.close()

except psycopg2.Error as e:  # CORRECCIÓN W0718: Captura específica para errores de Postgres
    print(f"Nota: Verificación automática de DB omitida o fallida: {e}")
except (IndexError, ValueError) as e: # Captura específica para errores de parseo de URL
    print(f"Nota: Error al parsear la URL de la base de datos: {e}")

# --- CONFIGURACIÓN DE SQLALCHEMY ---

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    Generador de sesiones de base de datos.
    Asegura que la conexión se cierre después de cada petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# Fin de app/database.py