---
id: skill-azure-cloud-native-testing-2e886e185f
purpose: azure cloud native testing
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-static-analysis-the-ruff-led-stack-0ac1d5e4c5"]
links: ["skill-azure-devops-pipeline-for-python-68aa18180b"]
---

## Azure Cloud-Native Testing

### Azurite (Local Azure Storage Emulator)

```python
# conftest.py
import pytest
import subprocess
import time
from azure.storage.blob import BlobServiceClient

AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KNKQi38OHD2g==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
)

@pytest.fixture(scope="session")
def azurite():
    """Start Azurite for the test session."""
    proc = subprocess.Popen(["azurite", "--silent"])
    time.sleep(2)  # wait for startup
    yield
    proc.terminate()

@pytest.fixture
def blob_client(azurite):
    client = BlobServiceClient.from_connection_string(AZURITE_CONNECTION_STRING)
    container = client.create_container("test-container")
    yield client
    client.delete_container("test-container")
```

Or use testcontainers:
```python
from testcontainers.azurite import AzuriteContainer

@pytest.fixture(scope="session")
def azurite_container():
    with AzuriteContainer() as azurite:
        yield azurite
```

### Cosmos DB Linux Emulator (vNext)

```python
# conftest.py
import pytest
from testcontainers.core.container import DockerContainer
from azure.cosmos import CosmosClient

COSMOS_EMULATOR_IMAGE = "mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:vnext-preview"
COSMOS_ACCOUNT_KEY = "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw=="

@pytest.fixture(scope="session")
def cosmos_container():
    container = (
        DockerContainer(COSMOS_EMULATOR_IMAGE)
        .with_exposed_ports(8081, 8080)
        .with_env("AZURE_COSMOS_EMULATOR_PARTITION_COUNT", "3")
        .with_env("AZURE_COSMOS_EMULATOR_ENABLE_DATA_PERSISTENCE", "false")
    )
    with container:
        # Wait for health endpoint
        import time; time.sleep(15)
        yield container

@pytest.fixture(scope="session")
def cosmos_client(cosmos_container):
    port = cosmos_container.get_exposed_port(8081)
    client = CosmosClient(
        url=f"https://localhost:{port}",
        credential=COSMOS_ACCOUNT_KEY,
        connection_verify=False  # emulator uses self-signed cert
    )
    yield client
```

### testcontainers-python (PostgreSQL, Redis, Kafka, etc.)

```python
# conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from myapp.db import Base

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def db_engine(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
```

---
