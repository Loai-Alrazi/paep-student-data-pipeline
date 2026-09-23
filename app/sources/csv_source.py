from pathlib import Path

import pandas as pd

from app.utils.config_loader import load_config
from app.utils.logger import setup_logger

"""CSV source placeholder."""
# =========================
# Load data
# =========================

def load_data(file_path: str | Path) -> pd.DataFrame:
    """Load the raw CSV file."""

    logger = setup_logger(load_config()["logging"]["path"], name=__name__)
    logger.info("Starting CSV data loading from %s.", file_path)

    file_path = Path(file_path)

    if not file_path.exists():
        logger.error("CSV input file does not exist: %s", file_path)
        raise FileNotFoundError(
            f"Input file does not exist: {file_path}"
        )

    df = pd.read_csv(file_path)

    if df.empty:
        logger.error("CSV input dataset is empty: %s", file_path)
        raise ValueError("Input dataset is empty")

    logger.info("Loaded %d records from CSV.", len(df))

    return df
