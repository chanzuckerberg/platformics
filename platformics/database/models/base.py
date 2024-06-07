import datetime
import uuid
from typing import TYPE_CHECKING

import uuid6
from sqlalchemy import Column, DateTime, Index, Integer, MetaData, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

if TYPE_CHECKING:
    from platformics.database.models.file import File
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
    producing_run_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=True)
    owner_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    collection_id: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)


Index("entity_query_fields", Entity.collection_id, Entity.producing_run_id)
