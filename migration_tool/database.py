from collections.abc import Iterator
from typing import Any

import pyodbc

from .identity import azure_sql_access_token, load_aws_sql_credentials
from .models import AwsSource, AzureTarget


def _connection_string(server: str, port: int, database: str, encrypt: bool, trust: bool) -> str:
    return ";".join([
        "DRIVER={ODBC Driver 18 for SQL Server}",
        f"SERVER={server},{port}",
        f"DATABASE={database}",
        f"Encrypt={'yes' if encrypt else 'no'}",
        f"TrustServerCertificate={'yes' if trust else 'no'}",
    ])


class SqlServerSource:
    def __init__(self, settings: AwsSource):
        self.settings = settings
        username, password = load_aws_sql_credentials(settings.region, settings.secret_id)
        connection_string = _connection_string(settings.host, settings.port, settings.database, settings.encrypt, settings.trust_server_certificate)
        self.connection = pyodbc.connect(f"{connection_string};UID={username};PWD={password}", autocommit=False)

    def tables(self, schemas: list[str], selected: list[str]) -> list[tuple[str, str]]:
        query = "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
        params: list[str] = []
        if schemas:
            query += " AND TABLE_SCHEMA IN (" + ",".join("?" for _ in schemas) + ")"
            params.extend(schemas)
        if selected:
            query += " AND TABLE_NAME IN (" + ",".join("?" for _ in selected) + ")"
            params.extend(selected)
        query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"
        return [(row[0], row[1]) for row in self.connection.cursor().execute(query, params)]

    def columns(self, schema: str, table: str) -> list[str]:
        rows = self.connection.cursor().execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
            schema, table,
        )
        return [row[0] for row in rows]

    def rows(self, schema: str, table: str, columns: list[str], batch_size: int) -> Iterator[list[tuple[Any, ...]]]:
        names = ", ".join(f"[{column.replace(']', ']]')}]" for column in columns)
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT {names} FROM [{schema.replace(']', ']]')}].[{table.replace(']', ']]')}]" )
        while batch := cursor.fetchmany(batch_size):
            yield batch

    def count(self, schema: str, table: str) -> int:
        return int(self.connection.cursor().execute(f"SELECT COUNT_BIG(*) FROM [{schema}].[{table}]").fetchone()[0])


class AzureSqlTarget:
    def __init__(self, settings: AzureTarget):
        self.settings = settings
        server = settings.server if "," in settings.server else f"{settings.server},1433"
        connection_string = ";".join([
            "DRIVER={ODBC Driver 18 for SQL Server}", f"SERVER={server}", f"DATABASE={settings.database}",
            f"Encrypt={'yes' if settings.encrypt else 'no'}", f"TrustServerCertificate={'yes' if settings.trust_server_certificate else 'no'}",
        ])
        token = azure_sql_access_token(settings.tenant_id, settings.client_id, settings.authentication)
        self.connection = pyodbc.connect(connection_string, attrs_before={1256: token}, autocommit=False)

    def ensure_table(self, schema: str, table: str, columns: list[str]) -> None:
        cursor = self.connection.cursor()
        cursor.execute(f"IF SCHEMA_ID(?) IS NULL EXEC('CREATE SCHEMA [{schema}]')", schema)
        definitions = ", ".join(f"[{column}] NVARCHAR(MAX) NULL" for column in columns)
        cursor.execute(f"IF OBJECT_ID(?, 'U') IS NULL CREATE TABLE [{schema}].[{table}] ({definitions})", f"{schema}.{table}")

    def truncate(self, schema: str, table: str) -> None:
        self.connection.cursor().execute(f"TRUNCATE TABLE [{schema}].[{table}]")

    def insert(self, schema: str, table: str, columns: list[str], rows: list[tuple[Any, ...]]) -> None:
        names = ", ".join(f"[{column}]" for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        cursor = self.connection.cursor()
        cursor.fast_executemany = True
        cursor.executemany(f"INSERT INTO [{schema}].[{table}] ({names}) VALUES ({placeholders})", rows)

    def count(self, schema: str, table: str) -> int:
        return int(self.connection.cursor().execute(f"SELECT COUNT_BIG(*) FROM [{schema}].[{table}]").fetchone()[0])

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()
