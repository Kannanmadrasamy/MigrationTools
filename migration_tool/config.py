import json
from pathlib import Path

from .models import MigrationConfig


def load_config(path: str | Path) -> MigrationConfig:
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as config_file:
        return MigrationConfig.model_validate(json.load(config_file))
