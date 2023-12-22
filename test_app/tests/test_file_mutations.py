"""
Test file mutations for upload, linking an existing S3 file, and marking a file as completed
"""

import os
import pytest
import sqlalchemy as sa
from mypy_boto3_s3.client import S3Client
from platformics.database.connect import SyncDB
from database.models import File, FileStatus
from platformics.codegen.conftest import SessionStorage, FileFactory, GQLTestClient
from platformics.codegen.tests.output.test_infra.factories.sequencing_read import SequencingReadFactory
from platformics.codegen.tests.output.database.models import SequencingRead


@pytest.mark.asyncio
async def test_file_validation(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
    moto_client: S3Client,
) -> None:
    """
    Test that we can mark a file upload as complete
    """
    user1_id = 12345
    project1_id = 123

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SequencingReadFactory.create(owner_user_id=user1_id, collection_id=project1_id)
        FileFactory.update_file_ids()
        session.commit()
        files = session.execute(sa.select(File)).scalars().all()
        file = list(filter(lambda file: file.entity_field_name == "r1_file", files))[0]

    valid_fastq_file = "test_infra/fixtures/test1.fastq"
    file_size = os.stat(valid_fastq_file).st_size
    moto_client.put_object(Bucket=file.namespace, Key=file.path, Body=open(valid_fastq_file, "rb"))

    # Mark upload complete
    query = f"""
      mutation MyMutation {{
        markUploadComplete(fileId: "{file.id}") {{
          id
          namespace
          size
          status
        }}
      }}
    """
    res = await gql_client.query(query, member_projects=[project1_id])
    fileinfo = res["data"]["markUploadComplete"]
    assert fileinfo["status"] == "SUCCESS"
    assert fileinfo["size"] == file_size

    # Make sure the file was updated in the database
    with sync_db.session() as session:
        files = session.execute(sa.select(File)).scalars().all()
        file = list(filter(lambda file: file.entity_field_name == "r1_file", files))[0]
        assert file.status == FileStatus.SUCCESS
        assert file.size == file_size


@pytest.mark.asyncio
async def test_invalid_fastq(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
    moto_client: S3Client,
) -> None:
    """
    Test that invalid fastq's don't work
    """
    user1_id = 12345
    project1_id = 123

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SequencingReadFactory.create(owner_user_id=user1_id, collection_id=project1_id)
        FileFactory.update_file_ids()
        session.commit()
        files = session.execute(sa.select(File)).scalars().all()
        file = list(filter(lambda file: file.entity_field_name == "r1_file", files))[0]

    moto_client.put_object(Bucket=file.namespace, Key=file.path, Body="this is not a fastq file")

    # Mark upload complete
    query = f"""
      mutation MyMutation {{
        markUploadComplete(fileId: "{file.id}") {{
          id
          namespace
          size
          status
        }}
      }}
    """
    res = await gql_client.query(query, member_projects=[project1_id])
    fileinfo = res["data"]["markUploadComplete"]
    assert fileinfo["status"] == "FAILED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "member_projects,project_id,entity_field",
    [
        ([456], 123, "r1_file"),  # Can't create file for entity you don't have access to
        ([123], 123, "does_not_exist"),  # Can't create file for entity that isn't connected to a valid file type
        ([123], 123, "r1_file"),  # Can create file for entity you have access to
    ],
)
async def test_upload_file(
    member_projects: list[int],
    project_id: int,
    entity_field: str,
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test generating STS tokens for file uploads
    """
    user_id = 12345

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SequencingReadFactory.create(owner_user_id=user_id, collection_id=project_id)
        FileFactory.update_file_ids()
        session.commit()

        sequencing_read = session.execute(sa.select(SequencingRead)).scalars().one()
        entity_id = sequencing_read.entity_id

    # Try creating a file
    mutation = f"""
        mutation MyQuery {{
          uploadFile(
            entityId: "{entity_id}",
            entityFieldName: "{entity_field}",
            file: {{
                name: "test.fastq",
                fileFormat: "fastq"
            }}
        ) {{
            credentials {{
                namespace
                path
                accessKeyId
                secretAccessKey
                expiration
            }}
          }}
        }}
    """
    output = await gql_client.query(mutation, member_projects=member_projects)

    # If don't have access to this entity, or trying to link an entity with a made up file type, should get an error
    if project_id not in member_projects or entity_field == "does_not_exist":
        assert output["data"] is None
        assert output["errors"] is not None
        return

    # Moto produces a hard-coded tokens
    assert output["data"]["uploadFile"]["credentials"]["accessKeyId"].endswith("EXAMPLE")
    assert output["data"]["uploadFile"]["credentials"]["secretAccessKey"].endswith("EXAMPLEKEY")


@pytest.mark.asyncio
async def test_create_file(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
    moto_client: S3Client,
) -> None:
    """
    Test adding an existing file to the entities service
    """
    with sync_db.session() as session:
        # Create sequencing read and file
        SessionStorage.set_session(session)
        SequencingReadFactory.create(owner_user_id=12345, collection_id=123)
        FileFactory.update_file_ids()
        session.commit()

        sequencing_read = session.execute(sa.select(SequencingRead)).scalars().one()
        entity_id = sequencing_read.entity_id

    # Upload a fastq file to a mock bucket so we can create a file object from it
    file_namespace = "local-bucket"
    file_path = "test1.fastq"
    file_path_local = "test_infra/fixtures/test1.fastq"
    file_size = os.stat(file_path_local).st_size
    with open(file_path_local, "rb") as fp:
        moto_client.put_object(Bucket=file_namespace, Key=file_path, Body=fp)

    # Try creating a file from existing file on S3
    mutation = f"""
        mutation MyQuery {{
            createFile(
                entityId: "{entity_id}",
                entityFieldName: "r1_file",
                file: {{
                    name: "{file_path}",
                    fileFormat: "fastq",
                    protocol: "s3",
                    namespace: "{file_namespace}",
                    path: "{file_path}"
                }}
            ) {{
                path
                size
            }}
        }}
    """
    output = await gql_client.query(mutation, member_projects=[123])
    assert output["data"]["createFile"]["size"] == file_size
