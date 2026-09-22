from pathlib import Path

import pandas as pd
import pytest

from app.sources.csv_source import load_data


def test_load_data_returns_dataframe(tmp_path: Path) -> None:
    csv_path = tmp_path / "students.csv"
    csv_path.write_text("student_id,name\n1,Alice\n2,Bob\n", encoding="utf-8")

    result = load_data(csv_path)

    expected = pd.DataFrame(
        {
            "student_id": [1, 2],
            "name": ["Alice", "Bob"],
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_load_data_raises_when_file_does_not_exist(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="Input file does not exist"):
        load_data(missing_path)


def test_load_data_raises_when_dataset_is_empty(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("student_id,name\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Input dataset is empty"):
        load_data(csv_path)
