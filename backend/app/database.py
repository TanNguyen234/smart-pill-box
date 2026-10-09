from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    options = {"connect_args": {"check_same_thread": False}} if database_url.startswith("sqlite:") else {}
    return create_engine(database_url, future=True, **options)


def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
