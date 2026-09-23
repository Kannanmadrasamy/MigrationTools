# Detailed Design and Technical Specification

## Purpose

This tool performs a controlled, repeatable bulk copy from an AWS-hosted Microsoft SQL Server to Azure SQL Database. It is designed for migrations where the source database remains available during a bounded copy window and where secrets must be resolved through identity-aware services rather than stored in configuration.

## Architecture

```text
JSON config
    |
    v
CLI -> Pydantic validation -> MigrationOrchestrator
                                      |
                 +--------------------+--------------------+
                 |                                         |
       SqlServerSource                              AzureSqlTarget
                 |                                         |
 AWS Secrets Manager + pyodbc              Entra ID token + pyodbc
```

### Components

- `config.py`: loads and validates JSON using Pydantic.
- `models.py`: defines source, target, and run options.
- `identity.py`: uses boto3's default credential chain and AWS Secrets Manager; obtains Azure SQL tokens through `DefaultAzureCredential` or `ClientSecretCredential`.
- `database.py`: owns ODBC connections and database operations.
- `orchestrator.py`: enumerates tables, prepares target tables, copies batches, commits each table, and verifies counts.
- `cli.py`: provides the executable command and logging setup.

## Authentication and authorization

### AWS

The process requires an AWS principal with `secretsmanager:GetSecretValue` for the configured secret and network access to the source SQL Server. Boto3 resolves credentials in the standard order, including environment variables, shared profiles, ECS/EC2 roles, and workload identity mechanisms supported by the runtime.

The Secrets Manager value must be JSON with `username` and `password` fields. The secret should be encrypted with a customer-managed KMS key where organizational policy requires it.

### Azure

Managed identity is the preferred mode. Grant the identity a contained database user and least-privilege permissions such as `CREATE TABLE` only when target creation is enabled, plus `INSERT`, `SELECT`, and `ALTER` as required by the selected migration scope.

Service principal mode is supported for hosted runners. The client secret must be supplied through Azure Identity's supported environment variables or secret store, never in the migration JSON.

## Data flow

1. Load and validate JSON.
2. Open the AWS source connection using credentials fetched from Secrets Manager.
3. Acquire an Azure SQL access token and open the target connection.
4. List base tables filtered by configured schemas and table names.
5. Read source columns in ordinal order.
6. Optionally create a missing target table and schema.
7. Optionally truncate the target table.
8. Read rows with `fetchmany(batch_size)` and insert using `fast_executemany`.
9. Commit one table at a time.
10. Compare source and target `COUNT_BIG(*)` values when verification is enabled.

## Reliability model

A table is the transaction boundary. A failed table is rolled back. By default the process stops on the first failure; `continue_on_error` changes this to best-effort processing and logs each failed table. Reruns should use pre-created schemas and an explicit truncation or reconciliation strategy to avoid duplicate rows.

## Security controls

- TLS is enabled by default and certificate trust is not bypassed by default.
- No passwords or access tokens are written to logs.
- Configuration files should be protected by filesystem ACLs.
- Use private connectivity, firewall allowlists, and DNS resolution appropriate to the AWS and Azure network design.
- Restrict the source secret and Azure database role to the migration job identity.

## Current limitations and production hardening

- Missing target tables use `NVARCHAR(MAX)` columns. Native type mapping, primary keys, foreign keys, indexes, identity columns, LOB streaming, and CDC are outside this baseline.
- There is no resume checkpoint beyond committed tables; add a durable run manifest for very large migrations.
- Row-count validation does not prove content equivalence. Add checksums or sampled comparisons for regulated workloads.
- Source and target endpoints must be reachable from the host running the CLI.
- The tool is a bulk copy utility, not a continuous replication service. Use AWS DMS or another CDC-capable service for near-zero-downtime cutover.

## Extension points

The next safe extensions are a schema/type inspection phase, a durable manifest, retry policies for transient SQL errors, and a preflight command that checks identity permissions, ODBC versions, connectivity, and estimated data volume before copying.
