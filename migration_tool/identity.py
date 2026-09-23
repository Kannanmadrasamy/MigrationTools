import json
import struct
from typing import Any

import boto3
from azure.identity import ClientSecretCredential, DefaultAzureCredential


def load_aws_sql_credentials(region: str, secret_id: str) -> tuple[str, str]:
    secret = boto3.client("secretsmanager", region_name=region).get_secret_value(SecretId=secret_id)
    payload: dict[str, Any] = json.loads(secret["SecretString"])
    try:
        return str(payload["username"]), str(payload["password"])
    except KeyError as error:
        raise ValueError("AWS secret must contain username and password") from error


def azure_sql_access_token(tenant_id: str, client_id: str | None, authentication: str) -> bytes:
    if authentication == "service_principal":
        if not client_id:
            raise ValueError("target.client_id is required for service_principal authentication")
        credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id)
    else:
        credential = DefaultAzureCredential()
    token = credential.get_token("https://database.windows.net/.default").token
    return b"".join(struct.pack("<I", len(chunk)) + chunk for chunk in [token.encode("utf-16-le")])
