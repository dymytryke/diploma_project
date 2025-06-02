# app/models/base.py
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    metadata = MetaData()

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"
