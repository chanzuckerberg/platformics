"""
Test concatenating small files, both plain text and gzipped
"""
import pytest
import requests
from mypy_boto3_s3.client import S3Client
from platformics.database.connect import SyncDB
from platformics.codegen.conftest import SessionStorage, GQLTestClient
from platformics.codegen.tests.output.test_infra.factories.sequencing_read import SequencingReadFactory


@pytest.mark.parametrize(
    "file_name_1,file_name_2", [("test1.fasta", "test2.fasta"), ("test1.fasta.gz", "test2.fasta.gz")]
)
@pytest.mark.asyncio
async def test_concatenation(
    file_name_1: str,
    file_name_2: str,
    sync_db: SyncDB,
    gql_client: GQLTestClient,
    moto_client: S3Client,
) -> None:
    """
    Upload 2 files and concatenate them
    """
    user_id = 12345
    project_id = 111
    member_projects = [project_id]
    fasta_file_1 = f"test_infra/fixtures/{file_name_1}"
    fasta_file_2 = f"test_infra/fixtures/{file_name_2}"

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
            file: {{ name: "{file_name_1}", fileFormat: "fasta" }}
          ) {{
            file {{ id }}
            credentials {{ namespace path }}
          }}

          r2: uploadFile(
            entityId: "{entity_id}",
            entityFieldName: "r2_file",
            file: {{ name: "{file_name_2}", fileFormat: "fasta" }}
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
    moto_client.put_object(Bucket=credentials_1["namespace"], Key=credentials_1["path"], Body=open(fasta_file_1, "rb"))
    moto_client.put_object(Bucket=credentials_2["namespace"], Key=credentials_2["path"], Body=open(fasta_file_2, "rb"))

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

    # Concatenate files
    query = f"""
      mutation Concatenate {{
        concatenateFiles(ids: ["{file_id_1}", "{file_id_2}"]) {{
          url
        }}
      }}
    """
    output = await gql_client.query(query, member_projects=member_projects)
    contents_observed = requests.get(output["data"]["concatenateFiles"]["url"]).content

    # Validate concatenated files
    contents_expected = b""
    with open(fasta_file_1, "rb") as f:
        contents_expected += f.read()
    with open(fasta_file_2, "rb") as f:
        contents_expected += f.read()
    assert contents_expected == contents_observed
