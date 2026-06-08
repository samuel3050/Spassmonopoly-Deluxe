import os
from contextlib import contextmanager

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()
db = SQLAlchemy()


def create_database_url():
    """Build SQLAlchemy database URL from environment variables."""
    # SQLite keeps the local game setup self-contained; MySQL remains optional.
    db_engine = os.getenv("DB_ENGINE", "sqlite").lower()
    if db_engine == "sqlite":
        db_file = os.getenv("DB_FILE", "spassmonopoly.db")
        return f"sqlite:///{db_file}"
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "spassmonopoly")

    if db_password:
        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    return f"mysql+pymysql://{db_user}@{db_host}:{db_port}/{db_name}"


def init_db(app):
    """Initialize SQLAlchemy with Flask app."""
    app.config["SQLALCHEMY_DATABASE_URI"] = create_database_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "echo": False,
    }
    db.init_app(app)
    return db


def get_db_session():
    """Get a new database session."""
    return db.session


@contextmanager
def get_session():
    """Context manager for database sessions."""
    session = db.session
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables(app):
    """Create all database tables."""
    with app.app_context():
        db.create_all()
