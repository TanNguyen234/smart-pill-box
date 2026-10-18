from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    options = {"connect_args": {"check_same_thread": False}} if database_url.startswith("sqlite:") else {}
    engine = create_engine(database_url, future=True, **options)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _enforce_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
