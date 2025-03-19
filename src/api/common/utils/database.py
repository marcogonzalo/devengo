import os
from sqlalchemy import create_engine
from sqlmodel import Session


def _get_database_url_from_env_vars():
    DB_SCHEME = os.getenv("DB_SCHEME", "postgresql")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST = os.getenv("DB_HOST", "db")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "assessments")
    return f"{DB_SCHEME}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_database_url():
    url = os.getenv("DATABASE_URL", _get_database_url_from_env_vars())
    print("DATABASE_URL", url)
    return url


# Default to SQLite for development if no DATABASE_URL is provided
DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("ENV") != "production",
)


def get_db():
    with Session(engine) as session:
        yield session
