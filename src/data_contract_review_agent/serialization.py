"""Helpers for converting validation data into JSON-safe Python values."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from math import isnan

import numpy as np
import pandas as pd

from data_contract_review_agent.contract_models import ValidationFinding


def make_json_safe(value: object) -> object:
    """Recursively convert profile/finding objects into JSON-safe primitives."""
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return None if isnan(value) else value

    if value is pd.NA or value is pd.NaT or (isinstance(value, pd.Timestamp) and pd.isna(value)):
        return None

    if isinstance(value, np.generic):
        scalar = value.item()
        return make_json_safe(scalar)

    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]

    if pd.isna(value):
        return None

    return str(value)


def validation_finding_to_json_safe_dict(finding: ValidationFinding) -> dict[str, object]:
    """Convert a validation finding dataclass to a JSON-safe dictionary."""
    payload = asdict(finding)
    return make_json_safe(payload)  # type: ignore[return-value]
