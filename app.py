import streamlit as st
import pandas as pd
from datetime import date, datetime
import os

# ---- CONFIG ----
STAFF = ["Thomas", "Sophia", "Babita", "Suvarna"]
DATA_FILE = "attendance.csv"

# ---- LOAD / INIT DATA ----
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE, parse_dates=["date"])
    else:
        return pd.DataFrame(columns=["date", "staff", "present"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

df = load_data()

st.title("Simple Staff Attendance")

# ---- SELECT DATE ----
today = date.today()
selected_date = st.date_input("Date", value=today)

st.write(f"Recording attendance for **{selected_date.strftime('%d %b %Y')}**")

# ---- MARK ATTENDANCE ----
st.subheader("Mark attendance")

attendance_states = {}
cols = st.columns(2)
for i, staff in enumerate(STAFF):
    col = cols[i % 2]
    with col:
        present = st.checkbox(staff, value=True, key=f"{staff}_{selected_date}")
        attendance_states[staff] = present

if st.button("Save attendance"):
    # Remove existing rows for that date for those staff (so you can overwrite)
    mask_same_day = df["date"].dt.date == selected_date
    df = df[~mask_same_day]

    rows = []
    for staff, present in attendance_states.items():
        rows.append(
            {"date": datetime.combine(selected_date, datetime.min.time()),
             "staff": staff,
             "present": int(present)}
        )

    df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    save_data(df)
    st.success("Attendance saved.")

# ---- MONTHLY SUMMARY ----
st.subheader("Monthly summary")

if not df.empty:
    month = st.selectbox(
        "Select month",
        options=sorted(df["date"].dt.to_period("M").unique().astype(str)),
    )

    if month:
        year_int, month_int = map(int, month.split("-"))
        month_mask = (df["date"].dt.year == year_int) & (df["date"].dt.month == month_int)
        month_df = df[month_mask]

        if not month_df.empty:
            summary = (
                month_df[month_df["present"] == 1]
                .groupby("staff")["present"]
                .sum()
                .reset_index()
                .rename(columns={"present": "days_present"})
            )

            # Make sure all staff show up even if 0 days
            all_staff_df = pd.DataFrame({"staff": STAFF})
            summary = all_staff_df.merge(summary, on="staff", how="left").fillna(0)
            summary["days_present"] = summary["days_present"].astype(int)

            st.table(summary)
        else:
            st.info("No attendance recorded for that month yet.")
else:
    st.info("No attendance data yet. Save at least one day to see summary.")
