from pathlib import Path

import pandas as pd

"""CSV source placeholder."""
# =========================
# Load data
# =========================

def load_data(file_path: Path) -> pd.DataFrame:
    """Load the raw CSV file."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {file_path}"
        )

    df = pd.read_csv(file_path)

    if df.empty:
        raise ValueError("Input dataset is empty")


    return df
