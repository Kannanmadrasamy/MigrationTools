# Operations and Support Runbook

## Prerequisites

- Python 3.11 or later.
- Microsoft ODBC Driver 18 for SQL Server on the execution host.
- Network routes and firewall rules to the AWS SQL Server and Azure SQL server.
- AWS IAM permission for `secretsmanager:GetSecretValue` on the configured secret.
- Azure Entra identity with the required database permissions.
- A source secret containing JSON keys `username` and `password`.

## Recommended run sequence

1. Validate the JSON locally with the package test suite.
2. Confirm DNS and TCP connectivity to both database endpoints.
3. Run a small table allowlist with `truncate_target_tables` set to `false`.
4. Inspect row-count verification results.
5. Expand the table allowlist or remove it for the approved migration scope.
6. Freeze application writes for the final cutover when consistency is required.
7. Take independent backups or snapshots before destructive operations.

## Common failures

### AWS `AccessDeniedException`

The runtime identity cannot read the configured Secrets Manager secret. Check the AWS account, region, secret ARN, IAM policy, KMS decrypt permission, and the active boto3 profile or workload role.

### Azure login/token failure

For managed identity, check that the process is running on an Azure resource with identity enabled and that the identity has a database user. For service principal, check `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET` without placing the secret in JSON or logs.

### ODBC driver or connection errors

Confirm that `ODBC Driver 18 for SQL Server` is installed and visible to pyodbc. Check the server firewall, private endpoint DNS, TLS requirements, database name, and whether the execution host has a route to both clouds.

### Permission denied during target creation

Either grant the target identity the documented schema/table permissions or pre-create the target schema and tables, then set `create_target_schema` to `false`.

### Row-count mismatch

Treat this as a failed table. Check source writes during migration, triggers, filters, duplicate reruns, and whether a target table was truncated before the run. Do not ignore the mismatch for a production cutover.

### Memory or timeout pressure

Lower `batch_size`, increase command/network timeouts in a future adapter implementation, and migrate large tables independently. Avoid running many copies concurrently until the target service tier has been sized and tested.

## Logging and evidence

Retain the command configuration version, start/end timestamps, table results, failed table names, source and target row counts, and identity used. Logs should exclude secrets and access tokens. Store migration evidence according to the organization's retention and data classification policy.

## Rollback

This tool does not delete source data and does not provide automatic target rollback. For a failed run, stop downstream consumers, preserve logs, drop or restore only the affected target objects according to the change plan, and rerun from a known target state. Always use backups or point-in-time restore capabilities before a destructive target operation.

## Escalation checklist

Provide the tool version, sanitized config, affected table, UTC timestamp, complete error type/message, row counts, ODBC driver version, execution host, AWS region, Azure server/database, and confirmation that no credentials were included in the evidence.
