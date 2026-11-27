"""Adherence dashboard for the app owner. Run: streamlit run analytics.py

Reads the app database directly (DATABASE_URL), so keep it off the public internet.
"""

from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from app.db import SessionLocal, utcnow
from app.models import DoseEvent, Elder, Medicine


def load_doses(db: Session, days: int) -> pd.DataFrame:
    now = utcnow()
    rows = (
        db.query(
            Elder.name, Elder.timezone, Medicine.name, DoseEvent.scheduled_at, DoseEvent.status
        )
        .join(Elder, Elder.id == DoseEvent.elder_id)
        .join(Medicine, Medicine.id == DoseEvent.medicine_id)
        .filter(DoseEvent.scheduled_at >= now - timedelta(days=days))
        .filter(DoseEvent.scheduled_at <= now)
        .all()
    )
    # The day the dose was due, in the elder's own timezone.
    rows = [
        (elder, medicine, at.replace(tzinfo=UTC).astimezone(ZoneInfo(tz)).date(), status)
        for elder, tz, medicine, at, status in rows
    ]
    return pd.DataFrame(rows, columns=["elder", "medicine", "day", "status"])


def adherence(doses: pd.DataFrame) -> pd.DataFrame:
    """Taken / missed per elder and medicine. Only finished doses count."""
    done = doses[doses["status"].isin(["taken", "missed"])]
    table = (
        done.groupby(["elder", "medicine"])["status"]
        .value_counts()
        .unstack(fill_value=0)
        .reindex(columns=["taken", "missed"], fill_value=0)
        .reset_index()
    )
    table["adherence %"] = (100 * table["taken"] / (table["taken"] + table["missed"])).round()
    return table


def daily(doses: pd.DataFrame) -> pd.DataFrame:
    """Taken and missed counts per day, for a chart."""
    done = doses[doses["status"].isin(["taken", "missed"])]
    return (
        done.groupby("day")["status"]
        .value_counts()
        .unstack(fill_value=0)
        .reindex(columns=["taken", "missed"], fill_value=0)
    )


def low_stock(db: Session) -> pd.DataFrame:
    rows = (
        db.query(Elder.name, Medicine.name, Medicine.stock_count, Medicine.refill_threshold)
        .join(Elder, Elder.id == Medicine.elder_id)
        .filter(Medicine.stock_count <= Medicine.refill_threshold)
        .all()
    )
    return pd.DataFrame(rows, columns=["elder", "medicine", "stock", "refill at"])


def main() -> None:
    st.set_page_config(page_title="Medicine adherence", page_icon="💊")
    st.title("Medicine adherence")
    days = st.sidebar.selectbox(
        "Period", [7, 30, 90], index=1, format_func=lambda d: f"Last {d} days"
    )

    with SessionLocal() as db:
        doses = load_doses(db, days)
        low = low_stock(db)

    if doses.empty:
        st.info("No doses in this period yet.")
        return

    elders = sorted(doses["elder"].unique())
    chosen = st.sidebar.multiselect("Elders", elders, default=elders)
    doses = doses[doses["elder"].isin(chosen)]

    table = adherence(doses)
    taken, missed = table["taken"].sum(), table["missed"].sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("Adherence", f"{100 * taken / max(taken + missed, 1):.0f}%")
    col2.metric("Taken", int(taken))
    col3.metric("Missed", int(missed))

    st.subheader("Per day")
    st.bar_chart(daily(doses), color=["#2e7d32", "#c62828"])

    st.subheader("Per medicine")
    st.dataframe(table, hide_index=True)

    st.subheader("Needs refill")
    if low.empty:
        st.write("All medicines have enough stock.")
    else:
        st.dataframe(low[low["elder"].isin(chosen)], hide_index=True)


if __name__ == "__main__":
    main()
