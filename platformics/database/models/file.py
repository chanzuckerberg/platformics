import datetime
import uuid
import uuid6
from platformics.settings import APISettings
from platformics.database.models.base import Base, Entity
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Enum, event
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, Mapper, relationship
from sqlalchemy.engine import Connection
from support.enums import FileStatus, FileAccessProtocol, FileUploadClient
from mypy_boto3_s3.client import S3Client


class File(Base):
    __tablename__ = "file"
    _settings = None
    _s3_client = None

    @staticmethod
    def get_settings() -> APISettings:
        if not File._settings:
            raise Exception("Settings not defined in this environment")
        return File._settings

    @staticmethod
    def set_settings(settings: APISettings) -> None:
        File._settings = settings

    @staticmethod
    def get_s3_client() -> S3Client:
        if not File._s3_client:
            raise Exception("S3 client not defined in this environment")
        return File._s3_client

    @staticmethod
    def set_s3_client(s3_client: S3Client) -> None:
        File._s3_client = s3_client

    id: Column[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)

    # TODO - the relationship between Entities and Files is currently being
    # configured in both directions: entities have {fieldname}_file_id fields,
    # *and* files have {entity_id, field_name} fields to map back to
    # entities. We'll probably deprecate one side of this relationship in
    # the future, but I'm not sure yet which one is going to prove to be
    # more useful.
    entity_id = mapped_column(ForeignKey("entity.id"))
    entity_field_name: Mapped[str] = mapped_column(String, nullable=False)
    entity: Mapped[Entity] = relationship(Entity, foreign_keys=entity_id)

    # TODO: Changes here need to be reflected in api/files.py
    status: Mapped[FileStatus] = mapped_column(Enum(FileStatus, native_enum=False), nullable=False)
    protocol: Mapped[FileAccessProtocol] = mapped_column(Enum(FileAccessProtocol, native_enum=False), nullable=False)
    namespace: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    file_format: Mapped[str] = mapped_column(String, nullable=False)
    compression_type: Mapped[str] = mapped_column(String, nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=True)
    upload_client: Mapped[FileUploadClient] = mapped_column(Enum(FileUploadClient, native_enum=False), nullable=True)
    upload_error: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)


@event.listens_for(File, "before_delete")
def before_delete(mapper: Mapper, connection: Connection, target: File) -> None:
    """
    Before deleting a File object, check whether we need to delete it from S3, and
    make sure to scrub the foreign keys in the Entity it's associated with.
    """
    table_files = target.__table__
    table_entity = target.entity.__table__
    settings = File.get_settings()
    s3_client = File.get_s3_client()

    # If this file is managed by NextGen, see if it needs to be deleted from S3
    if target.path.startswith(f"{settings.OUTPUT_S3_PREFIX}/") and target.protocol == FileAccessProtocol.s3:
        # Is this the last File object pointing to this path?
        files_pointing_to_same_path = connection.execute(
            table_files.select()
            .where(table_files.c.id != target.id)
            .where(table_files.c.protocol == target.protocol)
            .where(table_files.c.namespace == target.namespace)
            .where(table_files.c.path == target.path)
        )

        # If so, delete it from S3
        if len(list(files_pointing_to_same_path)) == 0:
            response = s3_client.delete_object(Bucket=target.namespace, Key=target.path)
            if response["ResponseMetadata"]["HTTPStatusCode"] != 204:
                raise Exception("Failed to delete file from S3")

    # Finally, scrub the foreign keys in the related Entity
    values = {f"{target.entity_field_name}_id": None}
    # Modifying the target.entity directly does not save changes, we need to use `connection`
    connection.execute(
        table_entity.update().where(table_entity.c.entity_id == target.entity_id).values(**values)  # type: ignore
    )
