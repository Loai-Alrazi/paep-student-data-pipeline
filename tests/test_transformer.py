from pathlib import Path

import pandas as pd
import pytest

from app.transformation import transformer
from app.transformation.transformer import transform_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def canonical_api_data() -> pd.DataFrame:
    return pd.read_json(PROJECT_ROOT / "mock_api" / "students_academic.json")


def test_transform_fills_missing_major_and_numeric_values_from_valid_medians():
    data = pd.DataFrame(
        {
            "student_id": [1001, 1002, 1003, 1011],
            "major": ["math", None, "science", "art"],
            "gpa": [3.0, None, 4.5, 2.0],
            "attendance": [90, 80, 105, None],
        }
    )

    result = transform_data(data)

    assert result.loc[1, "major"] == "Unknown"
    assert result.loc[1, "gpa"] == 2.5
    assert result.loc[3, "attendance"] == 85
    assert result.loc[2, "gpa"] == 4.5
    assert result.loc[2, "attendance"] == 105
    assert pd.isna(result.loc[2, "performance_level"])
    assert pd.isna(result.loc[2, "attendance_status"])


def test_canonical_medians_exclude_invalid_values():
    result = transform_data(canonical_api_data())

    assert result.loc[result["student_id"] == 1002, "gpa"].item() == 3.0
    assert result.loc[result["student_id"] == 1011, "attendance"].item() == 85.0
    assert result["gpa"].median() == 3.0
    assert result["attendance"].median() == 85.0
    assert result.loc[result["student_id"] == 1004, "gpa"].item() == 4.5
    assert result.loc[result["student_id"] == 1003, "attendance"].item() == 105


@pytest.mark.parametrize(
    ("gpa", "expected"),
    [
        (3.5, "Excellent"),
        (3.0, "Very Good"),
        (2.5, "Good"),
        (2.0, "Acceptable"),
        (1.9, "At Risk"),
    ],
)
def test_performance_level_thresholds(gpa, expected):
    result = transform_data(pd.DataFrame({"gpa": [gpa], "attendance": [75]}))

    assert result.loc[0, "performance_level"] == expected


@pytest.mark.parametrize(
    ("attendance", "expected"), [(75, "Good"), (74.99, "Low")]
)
def test_attendance_status_threshold(attendance, expected):
    result = transform_data(pd.DataFrame({"gpa": [3.0], "attendance": [attendance]}))

    assert result.loc[0, "attendance_status"] == expected


def test_numeric_columns_are_converted_without_rejecting_invalid_values():
    data = pd.DataFrame(
        {
            "student_id": ["1001"],
            "age": ["22"],
            "gpa": ["4.5"],
            "attendance": ["105"],
            "score": ["88"],
        }
    )

    result = transform_data(data)

    for column in ("student_id", "age", "gpa", "attendance", "score"):
        assert pd.api.types.is_numeric_dtype(result[column])
    assert result.loc[0, "gpa"] == 4.5
    assert result.loc[0, "attendance"] == 105


def test_transform_logs_transformation_activity(tmp_path, monkeypatch):
    data = pd.DataFrame({"major": [None], "gpa": [None], "attendance": [None]})
    log_path = tmp_path / "pipeline.log"
    monkeypatch.setattr(
        transformer,
        "load_config",
        lambda: {"logging": {"path": str(log_path)}},
    )

    transformer.transform_data(data)

    log_content = log_path.read_text(encoding="utf-8")
    assert "Starting student data transformation for 1 records." in log_content
    assert "Completed student data transformation for 1 records." in log_content