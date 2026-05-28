"""Deterministic dataset profiling for observed evidence extraction."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

import numpy as np
from pathlib import Path

import pandas as pd
from pandas.api import types as pd_types

from data_contract_review_agent.contract_models import DatasetMetadata


@dataclass(slots=True)
class TopValue:
    """Deterministic top-frequency value summary used in column profiling."""
    value: str | int | float | bool
    count: int


@dataclass(slots=True)
class ColumnProfile:
    """Observed profile snapshot for one dataset column."""
    name: str
    pandas_dtype: str
    observed_logical_type: str
    null_count: int
    null_percentage: float
    non_null_count: int
    distinct_count: int
    sample_values: list[str | int | float | bool] = field(default_factory=list)
    top_values: list[TopValue] = field(default_factory=list)
    numeric_min: int | float | None = None
    numeric_max: int | float | None = None
    datetime_min: str | None = None
    datetime_max: str | None = None
    string_min_length: int | None = None
    string_max_length: int | None = None


@dataclass(slots=True)
class DatasetProfile:
    """Deterministic profile artifact used by downstream validators."""
    source_path: Path
    file_name: str
    sheet_name: str | None
    row_count: int
    column_count: int
    columns: dict[str, ColumnProfile]


def _to_safe_scalar(value: object) -> str | int | float | bool:
    """Normalize scalar values so profile artifacts serialize deterministically."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _parse_bool(value: object) -> bool | None:
    """Conservative boolean parser used before claiming boolean observed types."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"true", "false"}:
            return cleaned == "true"
    return None


def _parse_int(value: object) -> int | None:
    """Strict integer parser for full-column consistency checks."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.startswith(("+", "-")):
            sign, body = cleaned[0], cleaned[1:]
            if body.isdigit():
                return int(f"{sign}{body}")
        elif cleaned.isdigit():
            return int(cleaned)
    return None


def _parse_number(value: object) -> float | None:
    """Parse numeric candidates conservatively before claiming number types."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        try:
            parsed = float(cleaned)
        except ValueError:
            return None
        return parsed
    return None


def _parse_datetime(value: object) -> pd.Timestamp | None:
    """Parse datetime candidates conservatively for stable inferred typing."""
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value)
    if isinstance(value, str):
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return pd.Timestamp(parsed)
    return None


def infer_observed_logical_type(series: pd.Series) -> str:
    """Infer logical type conservatively to avoid over-claiming schema certainty."""
    non_null = series.dropna()
    if non_null.empty:
        return "empty"

    if pd_types.is_bool_dtype(series.dtype):
        return "boolean"
    if pd_types.is_integer_dtype(series.dtype):
        return "integer"
    if pd_types.is_float_dtype(series.dtype) or pd_types.is_numeric_dtype(series.dtype):
        return "number"
    if pd_types.is_datetime64_any_dtype(series.dtype):
        return "datetime"

    values = non_null.tolist()

    parsed_bools = [_parse_bool(value) for value in values]
    if all(value is not None for value in parsed_bools):
        return "boolean"

    parsed_ints = [_parse_int(value) for value in values]
    if all(value is not None for value in parsed_ints):
        return "integer"

    parsed_numbers = [_parse_number(value) for value in values]
    if all(value is not None for value in parsed_numbers):
        return "number"

    parsed_datetimes = [_parse_datetime(value) for value in values]
    if all(value is not None for value in parsed_datetimes):
        has_time_component = any(
            parsed is not None and parsed.time() != datetime.min.time() for parsed in parsed_datetimes
        )
        return "datetime" if has_time_component else "date"

    return "string"


def build_dataset_profile(
    dataframe: pd.DataFrame,
    metadata: DatasetMetadata,
    sample_size: int = 5,
    top_values_limit: int = 5,
) -> DatasetProfile:
    """Build observed evidence summaries without making contract judgments."""
    columns: dict[str, ColumnProfile] = {}

    for column_name in dataframe.columns:
        series = dataframe[column_name]
        non_null = series.dropna()
        total_count = len(series)
        null_count = int(series.isna().sum())
        non_null_count = int(len(non_null))
        null_percentage = round((null_count / total_count) * 100, 2) if total_count else 0.0
        distinct_count = int(non_null.nunique(dropna=True))
        observed_type = infer_observed_logical_type(series)

        sample_values = [_to_safe_scalar(value) for value in non_null.head(sample_size).tolist()]

        top_counts = Counter(_to_safe_scalar(value) for value in non_null.tolist())
        top_values = [
            TopValue(value=value, count=count)
            for value, count in sorted(top_counts.items(), key=lambda item: (-item[1], str(item[0])))[:top_values_limit]
        ]

        numeric_min: int | float | None = None
        numeric_max: int | float | None = None
        datetime_min: str | None = None
        datetime_max: str | None = None
        string_min_length: int | None = None
        string_max_length: int | None = None

        if not non_null.empty and observed_type in {"integer", "number"}:
            numeric_series = pd.to_numeric(non_null, errors="coerce").dropna()
            if not numeric_series.empty:
                numeric_min = _to_safe_scalar(numeric_series.min())  # type: ignore[assignment]
                numeric_max = _to_safe_scalar(numeric_series.max())  # type: ignore[assignment]

        if not non_null.empty and observed_type in {"date", "datetime"}:
            datetime_series = pd.to_datetime(non_null, errors="coerce").dropna()
            if not datetime_series.empty:
                datetime_min = pd.Timestamp(datetime_series.min()).isoformat()
                datetime_max = pd.Timestamp(datetime_series.max()).isoformat()

        if not non_null.empty and observed_type in {"string", "mixed"}:
            lengths = non_null.astype(str).map(len)
            if not lengths.empty:
                string_min_length = int(lengths.min())
                string_max_length = int(lengths.max())

        columns[str(column_name)] = ColumnProfile(
            name=str(column_name),
            pandas_dtype=str(series.dtype),
            observed_logical_type=observed_type,
            null_count=null_count,
            null_percentage=null_percentage,
            non_null_count=non_null_count,
            distinct_count=distinct_count,
            sample_values=sample_values,
            top_values=top_values,
            numeric_min=numeric_min,
            numeric_max=numeric_max,
            datetime_min=datetime_min,
            datetime_max=datetime_max,
            string_min_length=string_min_length,
            string_max_length=string_max_length,
        )

    return DatasetProfile(
        source_path=metadata.source_path,
        file_name=metadata.file_name,
        sheet_name=metadata.sheet_name,
        row_count=metadata.row_count,
        column_count=metadata.column_count,
        columns=columns,
    )
