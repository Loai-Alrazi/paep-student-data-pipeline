"""HTTP REST API source extraction for academic student records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import requests
from app.utils.logger import get_logger

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"
REQUIRED_FIELDS = {"student_id", "gpa", "attendance", "status"}

logger = get_logger(__name__)


class APISourceError(RuntimeError):
    """Raised when the API source cannot extract a valid transport payload."""


def load_api_config(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    with Path(config_path).open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    try:
        api_config = config["sources"]["api"]
    except KeyError as exc:
        raise APISourceError("Missing sources.api configuration.") from exc

    return dict(api_config)


class APISource:
    """Extract student records from a configured HTTP API endpoint."""

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        api_config = dict(config) if config is not None else load_api_config()

        try:
            self.url = str(api_config["url"])
            self.timeout_seconds = float(api_config["timeout_seconds"])
            logger.info(f"API source configured with URL: {self.url} and timeout: {self.timeout_seconds}s.")
        except KeyError as exc:
            logger.error("API configuration requires url and timeout_seconds.")
            raise APISourceError("API configuration requires url and timeout_seconds.") from exc
        except (TypeError, ValueError) as exc:
            logger.error("API timeout_seconds must be numeric.")
            raise APISourceError("API timeout_seconds must be numeric.") from exc

        if not self.url:
            logger.error("API URL cannot be empty.")
            raise APISourceError("API URL cannot be empty.")

    def extract(self) -> pd.DataFrame:
        try:
            response = requests.get(self.url, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.Timeout as exc:
            logger.error(f"API request timed out after {self.timeout_seconds} seconds.")
            raise APISourceError(f"API request timed out after {self.timeout_seconds} seconds.") from exc
        except requests.ConnectionError as exc:
            logger.error(f"API connection error for {self.url}.")
            raise APISourceError(f"API connection error for {self.url}.") from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            logger.error(f"API HTTP error: {status_code}.")
            raise APISourceError(f"API HTTP error: {status_code}.") from exc
        except requests.RequestException as exc:
            logger.error(f"API request failed: {exc}.")
            raise APISourceError(f"API request failed: {exc}.") from exc

        if not response.content:
            logger.error("API returned an empty response.")
            raise APISourceError("API returned an empty response.")

        try:
            payload = response.json()
            logger.info("API response received.")
        except ValueError as exc:
            logger.error("Invalid JSON returned by API.")
            raise APISourceError("Invalid JSON returned by API.") from exc

        if not payload:
            logger.error("API returned an empty response.")
            raise APISourceError("API returned an empty response.")
        if not isinstance(payload, list):
            logger.error("API payload must be a JSON array of records.")
            raise APISourceError("API payload must be a JSON array of records.")
        if not all(isinstance(record, dict) for record in payload):
            logger.error("API payload records must be JSON objects.")
            raise APISourceError("API payload records must be JSON objects.")

        frame = pd.DataFrame(payload)
        logger.info(f"Extracted {len(frame)} records from API.")
        missing_fields = REQUIRED_FIELDS.difference(frame.columns)
        logger.info(f"Required fields: {REQUIRED_FIELDS}")
        logger.info(f"Available fields: {frame.columns.tolist()}")
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            logger.error(f"API payload is missing required fields: {fields}.")
            raise APISourceError(f"API payload is missing required fields: {fields}.")

        logger.info("API extraction completed successfully.")
        return frame


def extract_api_data(config: Mapping[str, Any] | None = None) -> pd.DataFrame:
    return APISource(config).extract()
