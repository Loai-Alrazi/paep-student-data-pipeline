"""Reusable cleaning functions for extracted student data."""

import pandas as pd

from app.utils.config_loader import load_config
from app.utils.logger import setup_logger


TITLE_CASE_COLUMNS = {
	"student_name",
	"major",
	"city",
	"status",
	"course_name",
}


def _normalize_text(value: object, title_case: bool) -> object:
	if pd.isna(value) or not isinstance(value, str):
		return value

	normalized = " ".join(value.split())
	return normalized.title() if title_case else normalized


def clean_data(data: pd.DataFrame) -> pd.DataFrame:
	"""Clean textual values and remove exact duplicate records."""
	logger = setup_logger(load_config()["logging"]["path"], name=__name__)
	logger.info("Starting student data cleaning for %d records.", len(data))

	duplicate_count = int(data.duplicated().sum())
	cleaned = data.drop_duplicates().reset_index(drop=True).copy()
	if duplicate_count:
		logger.info("Removed %d exact duplicate records.", duplicate_count)

	for column in cleaned.columns:
		if not pd.api.types.is_string_dtype(cleaned[column].dtype):
			continue

		cleaned[column] = cleaned[column].map(
			lambda value: _normalize_text(value, column in TITLE_CASE_COLUMNS)
		)

	logger.info("Completed student data cleaning with %d records.", len(cleaned))
	return cleaned
