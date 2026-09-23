import argparse
import logging

from .config import load_config
from .database import AzureSqlTarget, SqlServerSource
from .orchestrator import MigrationOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate AWS SQL Server tables to Azure SQL")
    parser.add_argument("config", help="Path to migration JSON configuration")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config)
    results = MigrationOrchestrator(config, SqlServerSource(config.source), AzureSqlTarget(config.target)).run()
    logging.info("Migration complete: %d tables", len(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
