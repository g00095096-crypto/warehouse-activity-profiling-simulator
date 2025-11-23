from pathlib import Path
import pandas as pd

# Folder where streamlit_app.py and the CSV/XLSX files live
BASE_DIR = Path(__file__).resolve().parent.parent


def _safe_read_csv(filename):
    """
    Helper to read a CSV from the project root.
    Returns a dataframe if the file exists, otherwise None.
    """
    path = BASE_DIR / filename
    if path.exists():
        return pd.read_csv(path)
    else:
        return None


def _safe_read_excel(filename):
    """
    Helper to read an Excel file from the project root.
    Returns a dataframe if the file exists, otherwise None.
    """
    path = BASE_DIR / filename
    if path.exists():
        return pd.read_excel(path)
    else:
        return None


def load_main_datasets():
    """
    Loads all main datasets used in the project.

    Files expected in the SAME folder as streamlit_app.py:
      - SKU_Demand_Profile.csv
      - SKU_Clusters.csv
      - SKU_Associations.csv
      - Warehouse Challenge Dataset.xlsx

    Returns a dictionary with:
      - "demand"        -> demand profile data
      - "clusters"      -> clustering results
      - "associations"  -> association rules
      - "warehouse_raw" -> original challenge dataset
    Any missing file will have value None.
    """

    data = {}

    data["demand"] = _safe_read_csv("SKU_Demand_Profile.csv")
    data["clusters"] = _safe_read_csv("SKU_Clusters.csv")
    data["associations"] = _safe_read_csv("SKU_Associations.csv")
    data["warehouse_raw"] = _safe_read_excel("Warehouse Challenge Dataset.xlsx")

    return data

