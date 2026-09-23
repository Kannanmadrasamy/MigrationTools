import logging
from dataclasses import dataclass

from .database import AzureSqlTarget, SqlServerSource
from .models import MigrationConfig

logger = logging.getLogger(__name__)


@dataclass
class TableResult:
    schema: str
    table: str
    rows_copied: int
    source_rows: int | None


class MigrationOrchestrator:
    def __init__(self, config: MigrationConfig, source: SqlServerSource, target: AzureSqlTarget):
        self.config = config
        self.source = source
        self.target = target

    def run(self) -> list[TableResult]:
        options = self.config.options
        results: list[TableResult] = []
        for schema, table in self.source.tables(options.schemas, options.tables):
            try:
                columns = self.source.columns(schema, table)
                if options.create_target_schema:
                    self.target.ensure_table(schema, table, columns)
                if options.truncate_target_tables:
                    self.target.truncate(schema, table)
                copied = 0
                for batch in self.source.rows(schema, table, columns, options.batch_size):
                    self.target.insert(schema, table, columns, batch)
                    copied += len(batch)
                self.target.commit()
                source_rows = self.source.count(schema, table) if options.verify_row_counts else None
                target_rows = self.target.count(schema, table) if options.verify_row_counts else None
                if source_rows is not None and source_rows != target_rows:
                    raise RuntimeError(f"row count mismatch for {schema}.{table}: source={source_rows}, target={target_rows}")
                results.append(TableResult(schema, table, copied, source_rows))
                logger.info("Migrated %s.%s (%d rows)", schema, table, copied)
            except Exception:
                self.target.rollback()
                logger.exception("Migration failed for %s.%s", schema, table)
                if not options.continue_on_error:
                    raise
        return results
