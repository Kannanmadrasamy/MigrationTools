from typing import Literal

from pydantic import BaseModel, Field


class AwsSource(BaseModel):
    region: str
    host: str
    port: int = 1433
    database: str
    secret_id: str
    encrypt: bool = True
    trust_server_certificate: bool = False


class AzureTarget(BaseModel):
    server: str
    database: str
    tenant_id: str
    client_id: str | None = None
    authentication: Literal["managed_identity", "service_principal"] = "managed_identity"
    encrypt: bool = True
    trust_server_certificate: bool = False


class MigrationOptions(BaseModel):
    schemas: list[str] = Field(default_factory=lambda: ["dbo"])
    tables: list[str] = Field(default_factory=list)
    batch_size: int = Field(default=5000, ge=1)
    create_target_schema: bool = True
    truncate_target_tables: bool = False
    continue_on_error: bool = False
    verify_row_counts: bool = True


class MigrationConfig(BaseModel):
    source: AwsSource
    target: AzureTarget
    options: MigrationOptions = Field(default_factory=MigrationOptions)
