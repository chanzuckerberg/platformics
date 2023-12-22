from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import MetaData, Column, Integer, String
import uuid6

import uuid
from sqlalchemy.dialects.postgresql import UUID
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.file import File
else:
    File = "File"

meta = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    },
)


class Base(DeclarativeBase):
    metadata = meta


class Entity(Base):
    __tablename__ = "entity"
    __mapper_args__ = {"polymorphic_identity": "entity", "polymorphic_on": "type"}

    id: Column[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)

    # The "type" field distinguishes between subclasses (e.g. sample,
    # sequencing_read, etc)
    type: Mapped[str] = mapped_column(String, nullable=False)

    # Attributes for each entity
    producing_run_id: Mapped[uuid.UUID] = mapped_column(Integer, nullable=True)
    owner_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    collection_id: Mapped[int] = mapped_column(Integer, nullable=False)
