# ==========================================================
# 🚔 SecureCheck: Police Post Log Ledger (FINAL VERSION)
# ==========================================================

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ----------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------
st.set_page_config(page_title="SecureCheck", layout="wide")
st.title("🚔 SecureCheck: Police Post Log Ledger")

# ----------------------------------------------------------
# DATABASE (SQLite – No installation needed)
# ----------------------------------------------------------
DB_FILE = "securecheck.db"

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def create_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS police_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stop_date TEXT,
                stop_time TEXT,
                country_name TEXT,
                driver_gender TEXT,
                driver_age INTEGER,
                driver_race TEXT,
                violation TEXT,
                search_conducted INTEGER,
                search_type TEXT,
                stop_outcome TEXT,
                is_arrested INTEGER,
                stop_duration TEXT,
                drugs_related_stop INTEGER,
                vehicle_number TEXT
            )
        """)
create_table()

# ----------------------------------------------------------
# CSV UPLOAD
# ----------------------------------------------------------
uploaded_file = st.file_uploader("📂 Upload traffic_stops.csv", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # ------------------------------------------------------
    # DATA CLEANING
    # ------------------------------------------------------
    df = df.dropna(axis=1, how="all")

    required_cols = [
        "stop_date","stop_time","country_name","driver_gender",
        "driver_age","driver_race","violation","search_conducted",
        "search_type","stop_outcome","is_arrested",
        "stop_duration","drugs_related_stop"
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = "Unknown"

    df["vehicle_number"] = ["TN-"+str(1000+i) for i in range(len(df))]

    # Boolean conversion
    for col in ["search_conducted","is_arrested","drugs_related_stop"]:
        df[col] = df[col].astype(str).map(
            {"True":1,"False":0,"1":1,"0":0}
        ).fillna(0)

    df["driver_age"] = pd.to_numeric(
        df["driver_age"], errors="coerce"
    ).fillna(0).astype(int)

    # Insert into DB
    with get_conn() as conn:
        conn.execute("DELETE FROM police_logs")
        df.to_sql("police_logs", conn, if_exists="append", index=False)

    st.success("✅ Data successfully loaded into SecureCheck")

# ----------------------------------------------------------
# LOAD DATA
# ----------------------------------------------------------
data = pd.read_sql("SELECT * FROM police_logs", get_conn())

if data.empty:
    st.info("📁 Upload traffic_stops.csv to activate dashboard")
    st.stop()

# ----------------------------------------------------------
# DATE & TIME PROCESSING
# ----------------------------------------------------------
data["stop_date"] = pd.to_datetime(data["stop_date"], errors="coerce")
data["hour"] = pd.to_datetime(data["stop_time"], errors="coerce").dt.hour

# ----------------------------------------------------------
# DATE FILTER
# ----------------------------------------------------------
st.sidebar.header("📅 Filter by Date")

start_date = st.sidebar.date_input(
    "Start Date", data["stop_date"].min()
)
end_date = st.sidebar.date_input(
    "End Date", data["stop_date"].max()
)

filtered = data[
    (data["stop_date"] >= pd.to_datetime(start_date)) &
    (data["stop_date"] <= pd.to_datetime(end_date))
]

# ----------------------------------------------------------
# DASHBOARD METRICS
# ----------------------------------------------------------
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Stops", len(filtered))
c2.metric("Arrests", int(filtered["is_arrested"].sum()))
c3.metric("Searches", int(filtered["search_conducted"].sum()))
c4.metric("Drug Related", int(filtered["drugs_related_stop"].sum()))

st.divider()

# ----------------------------------------------------------
# VEHICLE LOG TABLE
# ----------------------------------------------------------
st.subheader("🚗 Vehicle Stop Records")

st.dataframe(
    filtered[[
        "stop_date","stop_time","vehicle_number",
        "violation","stop_outcome","country_name"
    ]],
    use_container_width=True
)

st.divider()

# ----------------------------------------------------------
# TIME & TREND ANALYTICS
# ----------------------------------------------------------
st.subheader("🕒 Peak Traffic Stop Hours")
st.bar_chart(filtered["hour"].value_counts().sort_index())

st.subheader("📆 Monthly Stop Trend")
monthly = filtered.groupby(filtered["stop_date"].dt.month).size()
st.line_chart(monthly)

st.divider()

# ==========================================================
# 🔮 DATE-BASED PREDICTION MODULE
# ==========================================================
st.subheader("🔮 Predict High-Risk Vehicles by Date")

predict_date = st.date_input(
    "Select a date to predict risk",
    value=datetime.today()
)

historical = data[data["stop_date"] <= pd.to_datetime(predict_date)]

if historical.empty:
    st.warning("⚠️ Not enough historical data for prediction")
else:
    historical = historical.copy()

    # Risk Score Logic
    historical["risk_score"] = (
        historical["drugs_related_stop"] * 3 +
        historical["is_arrested"] * 2 +
        historical["search_conducted"] * 2 +
        (historical["driver_age"] < 25).astype(int)
    )

    prediction = historical.groupby("vehicle_number").agg({
        "risk_score":"mean",
        "violation":"last",
        "country_name":"last"
    }).reset_index()

    prediction["Predicted_Risk"] = prediction["risk_score"].apply(
        lambda x: "HIGH" if x >= 3 else
                  "MEDIUM" if x >= 1.5 else "LOW"
    )

    st.success(f"📅 Prediction results for {predict_date}")

    st.dataframe(
        prediction.sort_values(
            "risk_score", ascending=False
        ).head(10),
        use_container_width=True
    )

st.caption("SecureCheck | Law Enforcement & Public Safety Analytics")
