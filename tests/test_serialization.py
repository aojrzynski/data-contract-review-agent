from datetime import date, datetime

import numpy as np
import pandas as pd

from data_contract_review_agent.contract_models import ValidationFinding
from data_contract_review_agent.serialization import make_json_safe, validation_finding_to_json_safe_dict


def test_make_json_safe_handles_scalars_and_null_like_values():
    assert make_json_safe(np.int64(5)) == 5
    assert make_json_safe(np.float64(1.5)) == 1.5
    assert make_json_safe(pd.Timestamp("2025-01-02T03:04:05")) == "2025-01-02T03:04:05"
    assert make_json_safe(date(2025, 1, 2)) == "2025-01-02"
    assert make_json_safe(datetime(2025, 1, 2, 3, 4, 5)) == "2025-01-02T03:04:05"
    assert make_json_safe(np.nan) is None
    assert make_json_safe(pd.NA) is None
    assert make_json_safe(pd.NaT) is None


def test_make_json_safe_handles_nested_structures():
    payload = {
        "a": [np.int64(1), {"b": pd.Timestamp("2025-01-01"), "c": {"x", "y"}}],
        "d": (pd.NA, np.float64(2.5)),
    }
    safe = make_json_safe(payload)
    assert safe["a"][0] == 1
    assert safe["a"][1]["b"] == "2025-01-01T00:00:00"
    assert sorted(safe["a"][1]["c"]) == ["x", "y"]
    assert safe["d"][0] is None


def test_validation_finding_to_json_safe_dict_converts_evidence():
    finding = ValidationFinding(
        finding_id="id",
        rule_type="type_mismatch",
        column="created_at",
        evidence={"observed_at": pd.Timestamp("2025-02-03"), "count": np.int64(2), "bad": np.nan},
    )
    safe = validation_finding_to_json_safe_dict(finding)
    assert safe["evidence"]["observed_at"] == "2025-02-03T00:00:00"
    assert safe["evidence"]["count"] == 2
    assert safe["evidence"]["bad"] is None
