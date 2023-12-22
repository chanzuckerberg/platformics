"""
Test end-to-end upload process
"""

import os
import pytest
from mypy_boto3_s3.client import S3Client
from platformics.database.connect import SyncDB
from platformics.codegen.conftest import SessionStorage, GQLTestClient
from platformics.codegen.tests.output.test_infra.factories.sequencing_read import SequencingReadFactory


@pytest.mark.asyncio
async def test_upload_process(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
    moto_client: S3Client,
) -> None:
    """
    Generate AWS credentials, upload a file, and mark the upload as complete
    """
    user_id = 12345
    project_id = 111
    member_projects = [project_id]

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sequencing_read = SequencingReadFactory.create(owner_user_id=user_id, collection_id=project_id)
        entity_id = sequencing_read.entity_id
        session.commit()

    # Get AWS creds to upload an R1 fastq file
    mutation = f"""
        mutation MyQuery {{
          uploadFile(
            entityId: "{entity_id}",
            entityFieldName: "r1_file",
            file: {{
                name: "some_file.fastq",
                fileFormat: "fastq"
            }}
          ) {{
            file {{
                id
                status
            }}
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
    file_id = output["data"]["uploadFile"]["file"]["id"]
    credentials = output["data"]["uploadFile"]["credentials"]

    # Upload the file
    fastq_file = "test_infra/fixtures/test1.fastq"
    fastq_file_size = os.stat(fastq_file).st_size
    moto_client.put_object(Bucket=credentials["namespace"], Key=credentials["path"], Body=open(fastq_file, "rb"))

    # Mark upload complete
    query = f"""
      mutation MyMutation {{
        markUploadComplete(fileId: "{file_id}") {{
          id
          namespace
          size
          status
        }}
      }}
    """
    output = await gql_client.query(query, member_projects=member_projects)
    assert output["data"]["markUploadComplete"]["status"] == "SUCCESS"
    assert output["data"]["markUploadComplete"]["size"] == fastq_file_size


@pytest.mark.asyncio
async def test_upload_process_multiple_files_per_entity(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
    moto_client: S3Client,
) -> None:
    """
    Make sure that entities with multiple file links still behave correctly. Test the logic that unlinks a File from
    an entity if another file is uploaded to the same entity field.
    """
    user_id = 12345
    project_id = 111
    member_projects = [project_id]
    fastq_file = "test_infra/fixtures/test1.fastq"

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sequencing_read = SequencingReadFactory.create(owner_user_id=user_id, collection_id=project_id)
        entity_id = sequencing_read.entity_id
        session.commit()

    # Create files
    mutation = f"""
        mutation MyQuery {{
          r1: uploadFile(
            entityId: "{entity_id}",
            entityFieldName: "r1_file",
            file: {{ name: "some_file1.fastq", fileFormat: "fastq" }}
          ) {{
            file {{ id }}
            credentials {{ namespace path }}
          }}

          r2: uploadFile(
            entityId: "{entity_id}",
            entityFieldName: "r2_file",
            file: {{ name: "some_file2.fastq", fileFormat: "fastq" }}
          ) {{
            file {{ id }}
            credentials {{ namespace path }}
          }}
        }}
    """
    output = await gql_client.query(mutation, member_projects=member_projects)

    # Upload files
    credentials_1 = output["data"]["r1"]["credentials"]
    credentials_2 = output["data"]["r2"]["credentials"]
    moto_client.put_object(Bucket=credentials_1["namespace"], Key=credentials_1["path"], Body=open(fastq_file, "rb"))
    moto_client.put_object(Bucket=credentials_2["namespace"], Key=credentials_2["path"], Body=open(fastq_file, "rb"))

    # Mark upload as complete
    file_id_1 = output["data"]["r1"]["file"]["id"]
    file_id_2 = output["data"]["r2"]["file"]["id"]
    query = f"""
      mutation MyMutation {{
        r1: markUploadComplete(fileId: "{file_id_1}") {{ status }}
        r2: markUploadComplete(fileId: "{file_id_2}") {{ status }}
      }}
    """
    output = await gql_client.query(query, member_projects=member_projects)
    assert output["data"]["r1"]["status"] == "SUCCESS"
    assert output["data"]["r2"]["status"] == "SUCCESS"
