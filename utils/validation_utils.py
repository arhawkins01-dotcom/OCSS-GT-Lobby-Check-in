from __future__ import annotations
import pandas as pd

REQUIRED_EXPORT_COLS = ["Status","Testing Date/Time","SETS Number","First Name","Last Name"]

def validate_onbase_export(df: pd.DataFrame) -> list[str]:
    return [c for c in REQUIRED_EXPORT_COLS if c not in df.columns]
