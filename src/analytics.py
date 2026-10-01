"""
Analytics and Statistics module for SU-DRISHTI.
Provides structured aggregations and trend analysis over the SQLite events database.
"""

from typing import Dict, Any, List
import pandas as pd
from src.database import get_connection


def get_summary_metrics() -> Dict[str, Any]:
    """Return high-level safety KPI metrics."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM events", conn)
    finally:
        conn.close()

    if df.empty:
        return {
            "total_incidents": 0,
            "critical_count": 0,
            "person_count": 0,
            "unique_sources": 0,
            "avg_confidence": 0.0,
        }

    return {
        "total_incidents": int(len(df)),
        "critical_count": int(len(df[df["severity"] == "CRITICAL"])),
        "person_count": int(len(df[df["object_name"] == "person"])),
        "unique_sources": int(df["source"].nunique()),
        "avg_confidence": float(df["confidence"].mean()),
    }


def get_incidents_by_type() -> pd.Series:
    """Return counts of incidents grouped by object/event type."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT object_name FROM events", conn)
    finally:
        conn.close()
    return df["object_name"].value_counts() if not df.empty else pd.Series()


def get_incidents_by_severity() -> pd.Series:
    """Return counts of incidents grouped by severity level."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT severity FROM events", conn)
    finally:
        conn.close()
    return df["severity"].value_counts() if not df.empty else pd.Series()


if __name__ == "__main__":
    metrics = get_summary_metrics()
    print("SU-DRISHTI Safety Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
