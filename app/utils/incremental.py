"""Manage incremental processing state for reuse across pipeline runs."""

from __future__ import annotations

import hashlib
import json
import math
import numbers
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

STATE_SCHEMA_VERSION = 1
DEFAULT_KEY_COLUMN = "student_id"


class IncrementalStateError(Exception):
    """Raised when persisted incremental state is unreadable or has an invalid schema."""


def fingerprint_record(record: Mapping[str, Any] | pd.Series) -> str:
    """Return a deterministic SHA-256 hex fingerprint for one record.

    Values are canonicalized before hashing: field names are sorted, missing
    values (None, NaN, pd.NA, pd.NaT) become nulls, integral floats are
    normalized to integers, and non-JSON scalars fall back to a stable textual
    form. The input record is never modified.

    Raises TypeError when the record is neither a Mapping nor a Series.
    """
    if not isinstance(record, (Mapping, pd.Series)):
        raise TypeError("record must be a pandas Series or a Mapping")
    items = sorted(
        ((str(field), value) for field, value in record.items()),
        key=lambda item: item[0],
    )
    payload = [[field, _canonical_value(value)] for field, value in items]
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_state(state_path: str | Path) -> dict:
    """Load the persisted incremental state from a JSON file.

    Returns a dict of the form {"version": 1, "records": {<key>: <fingerprint>}}.
    A missing file is treated as the first run and yields an empty state, not
    an error. Raises IncrementalStateError for invalid JSON or an invalid
    schema; other I/O errors propagate.
    """
    path = Path(state_path)
    try:
        with path.open(encoding="utf-8") as state_file:
            raw_state = json.load(state_file)
    except FileNotFoundError:
        return {"version": STATE_SCHEMA_VERSION, "records": {}}
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise IncrementalStateError(
            f"Invalid JSON in incremental state file {path}: {exc}"
        ) from exc
    return _validate_state(raw_state, path)


def save_state(state: Mapping, state_path: str | Path) -> None:
    """Validate and persist the incremental state as readable JSON.

    The parent directory is created when missing and record keys are written
    in sorted order so identical state always produces identical file content.
    Raises IncrementalStateError when the state does not match the expected
    schema; nothing is written in that case.
    """
    validated = _validate_state(dict(state))
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(validated, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def build_state(data: pd.DataFrame, key_column: str = DEFAULT_KEY_COLUMN) -> dict:
    """Build a fresh state mapping each record key to its fingerprint.

    Raises ValueError when key_column is missing from the DataFrame or its
    values are unusable as a stable key (missing or duplicated values would
    make the state ambiguous).
    """
    _require_usable_keys(data, key_column, unique=True)
    records: dict[str, str] = {}
    for position in range(len(data)):
        row = data.iloc[position]
        records[str(row[key_column])] = fingerprint_record(row)
    return {"version": STATE_SCHEMA_VERSION, "records": records}


def identify_changes(
    data: pd.DataFrame,
    previous_state: Mapping,
    key_column: str = DEFAULT_KEY_COLUMN,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split records into (new_or_changed, unchanged) against previous state.

    previous_state is the mapping returned by load_state or build_state; an
    empty mapping means the first run, so every record is reported as new.
    Row order inside each returned DataFrame follows the input order.

    Raises ValueError when key_column is missing or contains missing values,
    and IncrementalStateError when previous_state has an invalid structure.
    """
    _require_usable_keys(data, key_column, unique=False)
    records = _records_from_state(previous_state)
    new_positions: list[int] = []
    unchanged_positions: list[int] = []
    for position in range(len(data)):
        row = data.iloc[position]
        key = str(row[key_column])
        if records.get(key) == fingerprint_record(row):
            unchanged_positions.append(position)
        else:
            new_positions.append(position)
    return data.iloc[new_positions], data.iloc[unchanged_positions]


def _require_usable_keys(
    data: pd.DataFrame,
    key_column: str,
    *,
    unique: bool,
) -> None:
    if key_column not in data.columns:
        raise ValueError(f"key column {key_column!r} is not in the DataFrame columns")
    keys = data[key_column]
    if bool(keys.isna().any()):
        raise ValueError(
            f"{key_column} contains missing values; they cannot be used as incremental state keys"
        )
    if unique and bool(keys.duplicated().any()):
        duplicated = sorted({str(key) for key in keys[keys.duplicated(keep=False)]})
        raise ValueError(
            f"{key_column} contains duplicate values {duplicated}; "
            "they would silently overwrite incremental state"
        )


def _records_from_state(previous_state: Mapping) -> Mapping:
    if not isinstance(previous_state, Mapping):
        raise TypeError(
            "previous_state must be a Mapping as returned by load_state or build_state"
        )
    if not previous_state:
        return {}
    if "records" not in previous_state:
        raise IncrementalStateError(
            "previous_state is missing the 'records' section; "
            "pass the state returned by load_state or build_state"
        )
    records = previous_state["records"]
    if not isinstance(records, Mapping):
        raise IncrementalStateError(
            "previous_state['records'] must be a mapping of record keys to fingerprints"
        )
    return records


def _validate_state(state: Any, path: Path | None = None) -> dict:
    label = f"incremental state file {path}" if path is not None else "incremental state"
    if not isinstance(state, dict):
        raise IncrementalStateError(f"{label} must be a JSON object")
    version = state.get("version")
    if isinstance(version, bool) or version != STATE_SCHEMA_VERSION:
        raise IncrementalStateError(
            f"{label} has unsupported schema version {version!r}; "
            f"expected {STATE_SCHEMA_VERSION}"
        )
    records = state.get("records")
    if not isinstance(records, dict):
        raise IncrementalStateError(f"{label} is missing a valid 'records' object")
    for key, fingerprint in records.items():
        if not isinstance(fingerprint, str) or not fingerprint:
            raise IncrementalStateError(
                f"{label} has a non-string fingerprint for record key {key!r}"
            )
    return {"version": version, "records": dict(records)}


def _is_missing(value: Any) -> bool:
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _canonical_value(value: Any) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        number = float(value)
        if math.isfinite(number):
            return int(number) if number.is_integer() else number
        return repr(value)
    if isinstance(value, Mapping):
        return {str(field): _canonical_value(item) for field, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return repr(value)
