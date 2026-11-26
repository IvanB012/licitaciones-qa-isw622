"""Engine y sesión de SQLAlchemy (SQLite con claves foráneas activas)."""
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Base declarativa de todos los modelos (app/models.py)."""


def _enable_sqlite_fk(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_engine(database_url: str) -> Engine:
    """Crea el engine. En SQLite activa PRAGMA foreign_keys=ON en cada conexión."""
    kwargs: dict = {}
    is_sqlite = database_url.startswith("sqlite")
    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
        if database_url in ("sqlite://", "sqlite:///:memory:") or ":memory:" in database_url:
            kwargs["poolclass"] = StaticPool  # una sola conexión para que la BD en memoria persista
    engine = create_engine(database_url, **kwargs)
    if is_sqlite:
        event.listen(engine, "connect", _enable_sqlite_fk)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_tables(engine: Engine) -> None:
    """Crea todas las tablas si no existen (idempotente)."""
    from app import models  # noqa: F401  (registra los modelos en Base.metadata)

    Base.metadata.create_all(engine)


def drop_tables(engine: Engine) -> None:
    """Elimina todas las tablas (usado por el reset del seed)."""
    from app import models  # noqa: F401

    Base.metadata.drop_all(engine)
