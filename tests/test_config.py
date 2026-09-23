import json

from migration_tool.config import load_config


def test_load_config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "source": {"region": "us-east-1", "host": "rds", "database": "db", "secret_id": "secret"},
        "target": {"server": "sql.database.windows.net", "database": "db", "tenant_id": "tenant"},
    }))
    config = load_config(path)
    assert config.source.port == 1433
    assert config.target.authentication == "managed_identity"
    assert config.options.batch_size == 5000


def test_invalid_batch_size(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "source": {"region": "r", "host": "h", "database": "d", "secret_id": "s"},
        "target": {"server": "s", "database": "d", "tenant_id": "t"},
        "options": {"batch_size": 0},
    }))
    try:
        load_config(path)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid batch size should be rejected")
