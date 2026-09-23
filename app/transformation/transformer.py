"""Transform cleaned source records without applying rejection rules."""

from __future__ import annotations

import pandas as pd


NUMERIC_COLUMNS = ("student_id", "age", "gpa", "attendance", "credit_hours", "score")


def _valid_median(series: pd.Series, lower: float, upper: float) -> float | None:
	valid_values = series[series.between(lower, upper)]
	if valid_values.empty:
		return None
	return float(valid_values.median())


def transform_data(data: pd.DataFrame) -> pd.DataFrame:
	"""Apply recoverable transformations and add derived performance fields.

	Out-of-range numeric values remain unchanged for the validation layer.
	"""
	transformed = data.copy()

	for column in NUMERIC_COLUMNS:
		if column in transformed:
			transformed[column] = pd.to_numeric(transformed[column], errors="coerce")

	if "major" in transformed:
		transformed["major"] = transformed["major"].fillna("Unknown")

	if "gpa" in transformed:
		gpa_median = _valid_median(transformed["gpa"], 0, 4)
		if gpa_median is not None:
			missing_gpa = transformed["gpa"].isna()
			transformed.loc[missing_gpa, "gpa"] = gpa_median

	if "attendance" in transformed:
		attendance_median = _valid_median(transformed["attendance"], 0, 100)
		if attendance_median is not None:
			missing_attendance = transformed["attendance"].isna()
			transformed.loc[missing_attendance, "attendance"] = attendance_median

	if "gpa" in transformed:
		performance = pd.Series(pd.NA, index=transformed.index, dtype="string")
		valid_gpa = transformed["gpa"].between(0, 4)
		performance.loc[valid_gpa & (transformed["gpa"] >= 3.5)] = "Excellent"
		performance.loc[valid_gpa & (transformed["gpa"] >= 3.0) & (transformed["gpa"] < 3.5)] = "Very Good"
		performance.loc[valid_gpa & (transformed["gpa"] >= 2.5) & (transformed["gpa"] < 3.0)] = "Good"
		performance.loc[valid_gpa & (transformed["gpa"] >= 2.0) & (transformed["gpa"] < 2.5)] = "Acceptable"
		performance.loc[valid_gpa & (transformed["gpa"] < 2.0)] = "At Risk"
		transformed["performance_level"] = performance

	if "attendance" in transformed:
		attendance_status = pd.Series(pd.NA, index=transformed.index, dtype="string")
		valid_attendance = transformed["attendance"].between(0, 100)
		attendance_status.loc[valid_attendance & (transformed["attendance"] >= 75)] = "Good"
		attendance_status.loc[valid_attendance & (transformed["attendance"] < 75)] = "Low"
		transformed["attendance_status"] = attendance_status

	return transformed


def transform(data: pd.DataFrame) -> pd.DataFrame:
	"""Compatibility alias for callers using the shorter transformation name."""
	return transform_data(data)
