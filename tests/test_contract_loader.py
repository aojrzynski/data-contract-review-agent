import json
from pathlib import Path

import pytest

from data_contract_review_agent.contract_loader import load_contract


def test_loads_valid_yaml_contract() -> None:
    contract = load_contract("config/examples/customer_contract.yaml")

    assert contract.contract.name == "customer_master_contract"
    assert contract.contract.version == "1.0.0"
    assert "customer_id" in contract.columns


def test_loads_valid_json_contract(tmp_path: Path) -> None:
    payload = {
        "contract": {"name": "json_contract"},
        "columns": {"id": {"type": "string", "required": True}},
    }
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    contract = load_contract(path)

    assert contract.contract.name == "json_contract"


def test_missing_contract_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_contract("config/examples/missing.yaml")


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    path = tmp_path / "contract.txt"
    path.write_text("contract: {}", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported contract extension"):
        load_contract(path)


def test_missing_contract_name_raises(tmp_path: Path) -> None:
    path = tmp_path / "contract.yaml"
    path.write_text("contract: {}\ncolumns:\n  id: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="contract.name"):
        load_contract(path)


def test_missing_columns_raises(tmp_path: Path) -> None:
    path = tmp_path / "contract.yaml"
    path.write_text("contract:\n  name: sample\n", encoding="utf-8")

    with pytest.raises(ValueError, match="columns"):
        load_contract(path)


def test_unsupported_logical_type_raises(tmp_path: Path) -> None:
    path = tmp_path / "contract.yaml"
    path.write_text("contract:\n  name: sample\ncolumns:\n  id:\n    type: uuid\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported logical type"):
        load_contract(path)


def test_invalid_severity_raises(tmp_path: Path) -> None:
    path = tmp_path / "contract.yaml"
    path.write_text(
        "contract:\n  name: sample\ncolumns:\n  id:\n    type: string\n    severity: critical\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid severity"):
        load_contract(path)


def test_row_count_min_greater_than_max_raises(tmp_path: Path) -> None:
    path = tmp_path / "contract.yaml"
    path.write_text(
        "contract:\n  name: sample\ncolumns:\n  id:\n    type: string\nrow_count:\n  min: 10\n  max: 5\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must not be greater"):
        load_contract(path)


def test_invalid_freshness_rule_raises(tmp_path: Path) -> None:
    path = tmp_path / "contract.yaml"
    path.write_text(
        "contract:\n  name: sample\ncolumns:\n  updated_at:\n    type: datetime\n    freshness:\n      max_age_days: 0\n      reference: max_value\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="positive integer max_age_days"):
        load_contract(path)
