from pathlib import Path

import pandas as pd
import pytest

from data_contract_review_agent.intake import load_dataset


def test_load_dataset_csv_returns_dataframe_and_metadata() -> None:
    dataframe, metadata = load_dataset("sample_data/customers/customers_valid.csv")

    assert dataframe.shape == (5, 6)
    assert metadata.file_name == "customers_valid.csv"
    assert metadata.file_extension == ".csv"
    assert metadata.sheet_name is None
    assert metadata.row_count == 5
    assert metadata.column_count == 6


def test_load_dataset_xlsx_with_explicit_sheet(tmp_path: Path) -> None:
    path = tmp_path / "customers.xlsx"
    df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, sheet_name="SheetA", index=False)
        df.to_excel(writer, sheet_name="SheetB", index=False)

    loaded, metadata = load_dataset(path, sheet="SheetB")

    assert loaded.shape == (2, 2)
    assert metadata.sheet_name == "SheetB"


def test_load_dataset_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_dataset("sample_data/customers/does_not_exist.csv")


def test_load_dataset_raises_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "data.txt"
    path.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported dataset extension"):
        load_dataset(path)


def test_load_dataset_raises_for_empty_dataset(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    pd.DataFrame(columns=["a", "b"]).to_csv(path, index=False)

    with pytest.raises(ValueError, match="zero rows"):
        load_dataset(path)
