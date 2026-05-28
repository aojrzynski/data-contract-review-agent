"""Dataset intake helpers for local tabular files with safety guardrails.

This layer normalizes supported file inputs into a DataFrame plus stable
metadata used by downstream deterministic stages.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_contract_review_agent.contract_models import DatasetMetadata


SUPPORTED_DATASET_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}


def load_dataset(path: str | Path, sheet: str | None = None) -> tuple[pd.DataFrame, DatasetMetadata]:
    """Load a supported local tabular dataset and intake metadata.

Fails fast for missing paths, unsupported formats, and empty inputs.
"""
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {source_path}")

    extension = source_path.suffix.lower()
    if extension not in SUPPORTED_DATASET_EXTENSIONS:
        raise ValueError(
            f"Unsupported dataset extension '{extension}'. Supported extensions: .csv, .xlsx, .xlsm"
        )

    selected_sheet: str | None = None
    # CSV uses a direct single-table reader; Excel requires workbook handling.
    if extension == ".csv":
        dataframe = pd.read_csv(source_path)
    else:
        workbook = pd.ExcelFile(source_path)
        # When no sheet is requested, default to the first workbook sheet deterministically.
        if sheet is not None:
            if sheet not in workbook.sheet_names:
                raise ValueError(
                    f"Sheet '{sheet}' was not found in '{source_path.name}'. "
                    f"Available sheets: {', '.join(workbook.sheet_names)}"
                )
            selected_sheet = sheet
        else:
            selected_sheet = workbook.sheet_names[0]

        dataframe = pd.read_excel(source_path, sheet_name=selected_sheet)

    # Empty datasets are rejected early so validators never operate on degenerate inputs.
    if dataframe.shape[0] == 0:
        raise ValueError(f"Dataset '{source_path}' is empty (zero rows).")
    if dataframe.shape[1] == 0:
        raise ValueError(f"Dataset '{source_path}' is empty (zero columns).")

    metadata = DatasetMetadata(
        source_path=source_path,
        file_name=source_path.name,
        file_extension=extension,
        sheet_name=selected_sheet,
        row_count=dataframe.shape[0],
        column_count=dataframe.shape[1],
        columns=[str(column) for column in dataframe.columns.tolist()],
    )
    return dataframe, metadata
