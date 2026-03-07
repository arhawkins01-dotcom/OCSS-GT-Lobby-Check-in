from __future__ import annotations

from datetime import datetime

import pandas as pd


def apply_queue_priority(df: pd.DataFrame, grace_minutes: int) -> pd.DataFrame:
    """Apply queue prioritization and derive queue metrics fields."""
    if df.empty:
        return df

    out = df.copy()
    now = datetime.now()

    out["scheduled_dt"] = pd.to_datetime(out["testing_datetime"], errors="coerce")
    out["checkin_dt"] = pd.to_datetime(out["checkin_time"], errors="coerce")

    out["wait_minutes"] = 0
    mask_checked = out["current_status"].isin(["CHECKED_IN", "IN_PROCESS"])
    out.loc[mask_checked, "wait_minutes"] = (
        (now - out.loc[mask_checked, "checkin_dt"]).dt.total_seconds().fillna(0) / 60
    ).astype(int).clip(lower=0)

    out["late_minutes"] = 0
    out["late_flag"] = 0
    late_mask = out["checkin_dt"].notna() & out["scheduled_dt"].notna()
    out.loc[late_mask, "late_minutes"] = (
        (out.loc[late_mask, "checkin_dt"] - out.loc[late_mask, "scheduled_dt"]).dt.total_seconds() / 60
    ).astype(int)
    out.loc[late_mask & (out["late_minutes"] > grace_minutes), "late_flag"] = 1

    out["priority_bucket"] = 9

    # 1) checked in and waiting longest
    out.loc[out["current_status"] == "CHECKED_IN", "priority_bucket"] = 1

    # 2) checked in after scheduled time
    out.loc[(out["current_status"] == "CHECKED_IN") & (out["late_minutes"] > 0), "priority_bucket"] = 2

    # 3) scheduled clients near appointment time (within +/- 30 min)
    near_mask = (
        (out["current_status"] == "SCHEDULED")
        & out["scheduled_dt"].notna()
        & (((out["scheduled_dt"] - now).dt.total_seconds().abs() / 60) <= 30)
    )
    out.loc[near_mask, "priority_bucket"] = 3

    # 4) potential no-shows (scheduled and over grace window)
    no_show_mask = (
        (out["current_status"] == "SCHEDULED")
        & out["scheduled_dt"].notna()
        & (((now - out["scheduled_dt"]).dt.total_seconds() / 60) > grace_minutes)
    )
    out.loc[no_show_mask, "priority_bucket"] = 4

    out = out.sort_values(
        by=["priority_bucket", "wait_minutes", "scheduled_dt"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    out["queue_order"] = out.index + 1
    return out


def build_queue_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total": 0,
            "checked_in": 0,
            "waiting": 0,
            "completed": 0,
            "no_show": 0,
            "avg_wait": 0,
            "late_arrivals": 0,
        }

    wait_rows = df[df["current_status"].isin(["CHECKED_IN", "IN_PROCESS"])]
    avg_wait = int(wait_rows["wait_minutes"].mean()) if not wait_rows.empty else 0

    return {
        "total": int(len(df)),
        "checked_in": int((df["current_status"] == "CHECKED_IN").sum()),
        "waiting": int(df["current_status"].isin(["CHECKED_IN", "IN_PROCESS"]).sum()),
        "completed": int((df["current_status"] == "COMPLETED").sum()),
        "no_show": int((df["current_status"] == "NO_SHOW").sum()),
        "avg_wait": avg_wait,
        "late_arrivals": int((df.get("late_flag", 0) == 1).sum()),
    }
