import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# ---- CONFIG ----
STAFF = ["Thomas", "Sophia", "Babita", "Suvarna"]
WORKSHEET = "attendance"  # tab name inside your Google Sheet

st.set_page_config(page_title="Simple Staff Attendance", layout="centered")
st.title("Simple Staff Attendance")

# Pick a date
selected_date = st.date_input("Date", value=date.today())
st.write(f"Recording attendance for {selected_date.strftime('%d %b %Y')}")

# Create connection (reads spreadsheet + service account from Streamlit Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)  # uses [connections.gsheets] secrets [web:141]

# Always fetch latest sheet (avoid cached reads)
df = conn.read(worksheet=WORKSHEET, ttl=0)

# If empty/new sheet, initialize expected columns
if df is None or df.empty:
    df = pd.DataFrame(columns=["date", "staff", "present"])
else:
    # Normalize columns (in case Google Sheet types are weird)
    df = df.copy()
    if "date" not in df.columns or "staff" not in df.columns or "present" not in df.columns:
        st.error("Your Google Sheet must have columns: date, staff, present (row 1 headers).")
        st.stop()

# Attendance checkboxes
st.subheader("Mark attendance")
attendance_states = {}
cols = st.columns(2)
for i, staff in enumerate(STAFF):
    with cols[i % 2]:
        attendance_states[staff] = st.checkbox(staff, value=True, key=f"{staff}_{selected_date.isoformat()}")

# Save
if st.button("Save attendance"):
    # Convert 'date' in existing data to a real date for filtering
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df = df[df["date"] != selected_date]

    new_rows = pd.DataFrame(
        [{"date": selected_date.isoformat(), "staff": s, "present": int(p)}
         for s, p in attendance_states.items()]
    )

    df_out = pd.concat([df, new_rows], ignore_index=True)

    # Write entire worksheet back (simple + reliable for small data)
    conn.update(worksheet=WORKSHEET, data=df_out)  # update pattern shown in examples [web:151][web:145]
    st.success("Saved to Google Sheets.")

# Monthly summary
st.subheader("Monthly summary")

# Re-read after save so UI shows updated totals
df2 = conn.read(worksheet=WORKSHEET, ttl=0)

if df2 is None or df2.empty:
    st.info("No attendance data yet. Save at least one day to see summary.")
else:
    df2 = df2.copy()
    df2["date"] = pd.to_datetime(df2["date"], errors="coerce")

    if df2["date"].isna().all():
        st.info("Your sheet has no valid dates yet.")
    else:
        month_options = sorted(df2["date"].dropna().dt.to_period("M").unique().astype(str))
        month = st.selectbox("Select month", options=month_options)

        if month:
            y, m = map(int, month.split("-"))
            month_mask = (df2["date"].dt.year == y) & (df2["date"].dt.month == m)
            month_df = df2[month_mask]

            if month_df.empty:
                st.info("No attendance recorded for that month yet.")
            else:
                summary = (
                    month_df[month_df["present"].astype(int) == 1]
                    .groupby("staff")["present"]
                    .count()
                    .reset_index()
                    .rename(columns={"present": "days_present"})
                )

                all_staff_df = pd.DataFrame({"staff": STAFF})
                summary = all_staff_df.merge(summary, on="staff", how="left").fillna(0)
                summary["days_present"] = summary["days_present"].astype(int)

                st.table(summary)
