from pathlib import Path

import pandas as pd

from data_contract_review_agent.contract_models import DatasetMetadata
from data_contract_review_agent.intake import load_dataset
from data_contract_review_agent.profiling import build_dataset_profile, infer_observed_logical_type


def _metadata_for(df: pd.DataFrame) -> DatasetMetadata:
    return DatasetMetadata(
        source_path=Path("/tmp/test.csv"),
        file_name="test.csv",
        file_extension=".csv",
        sheet_name=None,
        row_count=df.shape[0],
        column_count=df.shape[1],
        columns=[str(c) for c in df.columns],
    )


def test_profile_row_and_column_counts_from_sample_csv() -> None:
    dataframe, metadata = load_dataset("sample_data/customers/customers_valid.csv")

    profile = build_dataset_profile(dataframe, metadata)

    assert profile.row_count == 5
    assert profile.column_count == 6
    assert len(profile.columns) == 6


def test_profile_null_counts_percentages_and_empty_column() -> None:
    df = pd.DataFrame({"value": [1, None, 3, None], "all_null": [None, None, None, None]})
    profile = build_dataset_profile(df, _metadata_for(df))

    value = profile.columns["value"]
    assert value.null_count == 2
    assert value.non_null_count == 2
    assert value.null_percentage == 50.0

    all_null = profile.columns["all_null"]
    assert all_null.observed_logical_type == "empty"


def test_infers_integer_number_boolean_and_date_or_datetime_types() -> None:
    df = pd.DataFrame(
        {
            "integer_col": [1, 2, 3],
            "number_col": [1.0, 2.5, 3.75],
            "bool_col": [True, False, True],
            "date_col": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "datetime_col": ["2024-01-01T10:00:00", "2024-01-02T11:00:00", "2024-01-03T12:00:00"],
        }
    )
    profile = build_dataset_profile(df, _metadata_for(df))

    assert profile.columns["integer_col"].observed_logical_type == "integer"
    assert profile.columns["number_col"].observed_logical_type == "number"
    assert profile.columns["bool_col"].observed_logical_type == "boolean"
    assert profile.columns["date_col"].observed_logical_type == "date"
    assert profile.columns["datetime_col"].observed_logical_type == "datetime"


def test_treats_mixed_object_data_conservatively_as_string() -> None:
    df = pd.DataFrame({"mixed": ["123", "abc", "2024-01-01"]})

    observed = infer_observed_logical_type(df["mixed"])

    assert observed == "string"


def test_sample_values_and_top_values_are_deterministic() -> None:
    df = pd.DataFrame({"category": ["b", "a", "b", "c", "a", "b", None]})

    profile = build_dataset_profile(df, _metadata_for(df), sample_size=3, top_values_limit=2)
    column = profile.columns["category"]

    assert column.sample_values == ["b", "a", "b"]
    assert [(item.value, item.count) for item in column.top_values] == [("b", 3), ("a", 2)]


def test_numeric_string_and_datetime_summaries() -> None:
    df = pd.DataFrame(
        {
            "numbers": [10, 5, 20],
            "strings": ["aa", "bbbb", "ccc"],
            "datetimes": ["2024-01-01T10:00:00", "2024-01-01T09:00:00", "2024-01-02T11:00:00"],
        }
    )

    profile = build_dataset_profile(df, _metadata_for(df))

    number_col = profile.columns["numbers"]
    assert number_col.numeric_min == 5
    assert number_col.numeric_max == 20

    string_col = profile.columns["strings"]
    assert string_col.string_min_length == 2
    assert string_col.string_max_length == 4

    datetime_col = profile.columns["datetimes"]
    assert datetime_col.datetime_min == "2024-01-01T09:00:00"
    assert datetime_col.datetime_max == "2024-01-02T11:00:00"
