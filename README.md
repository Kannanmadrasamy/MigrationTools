# AWS to Azure SQL Migration Tool

A Python CLI that orchestrates migration of tables from an AWS-hosted SQL Server, such as Amazon RDS for SQL Server, to Azure SQL Database.

## What it provides

- JSON-driven migration settings.
- AWS SDK credential resolution and AWS Secrets Manager lookup for source SQL credentials.
- Microsoft Entra ID access-token authentication for Azure SQL using managed identity or service principal.
- Batched table copy, optional target creation/truncation, per-table transactions, and row-count verification.
- Structured logging and a `continue_on_error` option for controlled batch runs.

## Quick start

1. Install Microsoft ODBC Driver 18 for SQL Server.
2. Create a virtual environment and install the package:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

3. Copy `config.example.json` to a protected location and set real endpoints. Do not put passwords or client secrets in the JSON file.
4. Authenticate AWS with the normal boto3 provider chain, for example an IAM role, profile, or environment credentials.
5. Authenticate Azure with `DefaultAzureCredential` for managed identity. For a service principal, set `authentication` to `service_principal`, provide `client_id`, and let `AZURE_CLIENT_SECRET` be resolved by the Azure identity library.
6. Run:

```powershell
aws-azure-sql-migrate .\config.json --log-level INFO
```

See [docs/DESIGN.md](docs/DESIGN.md) for architecture and [docs/SUPPORT.md](docs/SUPPORT.md) for operational guidance.

## Important scope

The initial implementation creates missing target columns as `NVARCHAR(MAX)` because it is intended as an orchestration baseline, not a full SQL Server schema conversion engine. Review and pre-create production target schemas when native types, keys, indexes, computed columns, identity behavior, or constraints matter.
