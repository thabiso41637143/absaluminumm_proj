import streamlit as st
from models.Model import (
    init_data, inject_css,
    Users, StaffAttendence,
    supabase,
)
from models.User_Model import User
from datetime import date
import pandas as pd

abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(
    page_title="Absaluminum | Dashboard".upper(),
    page_icon=abs_icon,
    layout="wide",
)
inject_css()

# ─────────────────────────────────────────────────────────────────────────────
# Auth — show branded login page if not authenticated
# ─────────────────────────────────────────────────────────────────────────────
user = User()

if not st.session_state.get("user"):
    # ── Centred login card ────────────────────────────────────────────────
    st.image("Images/Heading_Letter_head.png")
    st.markdown(
        "<h2 style='text-align:center; color:#1f2937; margin-top:1rem;'>"
        "Welcome to Absaluminum Portal</h2>"
        "<p style='text-align:center; color:#6b7280; margin-bottom:2rem;'>"
        "Please sign in to access your dashboard.</p>",
        unsafe_allow_html=True,
    )

    _, login_col, _ = st.columns([1, 2, 1])
    with login_col:
        with st.container(border=True):
            st.markdown("#### 🔐 Sign In")
            user_name = st.text_input("Username", placeholder="Enter your username")
            password  = st.text_input("Password", type="password", placeholder="Enter your password")

            if st.button("Login", type="primary", use_container_width=True):
                try:
                    user_details = (
                        supabase.table("Profiles")
                        .select("username", "role", "email")
                        .eq("username", user_name)
                        .execute()
                    )
                    if not user_details.data:
                        st.error("Username not found.")
                    else:
                        supabase.auth.sign_in_with_password({
                            "email":    user_details.data[0].get("email"),
                            "password": password,
                        })
                        st.session_state.user = {
                            "user_role": user_details.data[0].get("role"),
                            "username":  user_details.data[0].get("username"),
                        }
                        st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    st.stop()

username = user.get_user()

# ─────────────────────────────────────────────────────────────────────────────
# Load all data once per session
# ─────────────────────────────────────────────────────────────────────────────
if "loaded" not in st.session_state:
    init_data()
    st.session_state.loaded = True

# Load staff data if not already present
abs_staff = Users()

# ─────────────────────────────────────────────────────────────────────────────
# Helper: logout button in sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("Images/Heading_Letter_head.png")
    st.markdown(f"**👤 {username}**")
    role = st.session_state.get("user", {}).get("user_role", "—")
    st.markdown(f"*Role: {role}*")
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        user.logout()

# ─────────────────────────────────────────────────────────────────────────────
# Page header
# ─────────────────────────────────────────────────────────────────────────────
st.image("Images/Heading_Letter_head.png")
st.markdown(
    "<h1 style='color:#1f2937; margin-bottom:0;'>ABSALUMINUM (PTY) LTD</h1>"
    "<p style='color:#6b7280; margin-top:4px;'>Dashboard — quotation, invoice & staff overview</p>",
    unsafe_allow_html=True,
)
st.markdown(f"<p style='color:#6b7280; font-size:0.85rem;'>📅 {date.today().strftime('%A, %d %B %Y')}</p>",
            unsafe_allow_html=True)

st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0 1.2rem 0;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Derive summary values
# ─────────────────────────────────────────────────────────────────────────────
quotes   = st.session_state.get("qouteSummary", [])
invoices = st.session_state.get("invoice_summary", [])
staff    = abs_staff.get_abs_staff()
att_reg  = st.session_state.get("init_att_register", [])

# Quotation counts
q_waiting    = sum(1 for q in quotes if str(q.get("status","")).lower() == "waiting")
q_inprogress = sum(1 for q in quotes if str(q.get("status","")).lower() == "inprogress")
q_invoiced   = sum(1 for q in quotes if str(q.get("status","")).lower() == "invoiced")

# Invoice totals
inv_total_value   = sum(float(i.get("total_amount", 0) or 0) for i in invoices)
inv_total_paid    = sum(float(i.get("paid_amount",  0) or 0) for i in invoices)
inv_outstanding   = sum(float(i.get("out_amount",   0) or 0) for i in invoices)
inv_inprogress    = sum(1 for i in invoices if str(i.get("inv_status","")).lower() == "inprogress")

# Staff / attendance
total_staff       = len(staff)
today_iso         = date.today().isoformat()
this_month        = date.today().strftime("%Y-%m")
days_this_month   = sum(
    1 for a in att_reg
    if str(a.get("att_date","")).startswith(this_month)
)

# Active jobs = quotes inprogress + invoices inprogress
active_jobs = q_inprogress + inv_inprogress

# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Top KPI bar
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 📊 Overview")
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("📋 Total Quotations", len(quotes))
with k2:
    st.metric("🧾 Total Invoices", len(invoices))
with k3:
    st.metric("🏗️ Active Jobs", active_jobs)
with k4:
    st.metric("💰 Total Outstanding", f"R {inv_outstanding:,.2f}")

st.markdown("<hr style='border:1px solid #d1d5db; margin:1rem 0;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — Invoice Summary
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 🧾 Invoice Summary")

i1, i2, i3 = st.columns(3)
with i1:
    with st.container(border=True):
        st.metric("Total Invoiced (R)", f"R {inv_total_value:,.2f}")
with i2:
    with st.container(border=True):
        st.metric("Total Collected (R)", f"R {inv_total_paid:,.2f}")
with i3:
    with st.container(border=True):
        outstanding_delta = f"-R {inv_outstanding:,.2f}" if inv_outstanding > 0 else "✅ None"
        st.metric("Outstanding (R)", f"R {inv_outstanding:,.2f}")

chart_col, table_col = st.columns([1, 1], gap="large")

with chart_col:
    st.markdown("**Paid vs Outstanding — last 10 invoices**")
    if invoices:
        chart_data = pd.DataFrame(invoices[-10:])
        chart_data = chart_data[["inv_numb", "paid_amount", "out_amount"]].copy()
        chart_data["paid_amount"] = pd.to_numeric(chart_data["paid_amount"], errors="coerce").fillna(0)
        chart_data["out_amount"]  = pd.to_numeric(chart_data["out_amount"],  errors="coerce").fillna(0)
        chart_data = chart_data.rename(columns={
            "inv_numb":    "Invoice #",
            "paid_amount": "Paid (R)",
            "out_amount":  "Outstanding (R)",
        })
        chart_data = chart_data.set_index("Invoice #")
        st.bar_chart(chart_data, color=["#16a34a", "#b91c1c"])
    else:
        st.info("No invoice data available.")

with table_col:
    st.markdown("**5 Most Recent Invoices**")
    if invoices:
        recent_inv = pd.DataFrame(invoices[-5:])
        cols_to_show = [c for c in ["inv_numb", "inv_to", "total_amount", "paid_amount", "out_amount", "inv_status"]
                        if c in recent_inv.columns]
        recent_inv = recent_inv[cols_to_show].copy()
        recent_inv["total_amount"] = pd.to_numeric(recent_inv["total_amount"], errors="coerce").apply(
            lambda x: f"R {x:,.2f}" if pd.notna(x) else "—")
        recent_inv["paid_amount"]  = pd.to_numeric(recent_inv["paid_amount"],  errors="coerce").apply(
            lambda x: f"R {x:,.2f}" if pd.notna(x) else "—")
        recent_inv["out_amount"]   = pd.to_numeric(recent_inv["out_amount"],   errors="coerce").apply(
            lambda x: f"R {x:,.2f}" if pd.notna(x) else "—")
        st.dataframe(
            recent_inv,
            hide_index=True,
            width="stretch",
            column_config={
                "inv_numb":    st.column_config.TextColumn("Inv #"),
                "inv_to":      st.column_config.TextColumn("Client"),
                "total_amount":st.column_config.TextColumn("Total"),
                "paid_amount": st.column_config.TextColumn("Paid"),
                "out_amount":  st.column_config.TextColumn("Outstanding"),
                "inv_status":  st.column_config.TextColumn("Status"),
            },
        )
    else:
        st.info("No invoices yet.")

st.markdown("<hr style='border:1px solid #d1d5db; margin:1rem 0;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — Quotation Summary
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 📋 Quotation Summary")

q1, q2, q3, q4 = st.columns(4)
with q1:
    with st.container(border=True):
        st.metric("⏳ Waiting", q_waiting)
with q2:
    with st.container(border=True):
        st.metric("🚧 In Progress", q_inprogress)
with q3:
    with st.container(border=True):
        st.metric("✅ Invoiced", q_invoiced)
with q4:
    with st.container(border=True):
        q_total_value = sum(float(q.get("total_amount", 0) or 0) for q in quotes)
        st.metric("💼 Total Value", f"R {q_total_value:,.2f}")

st.markdown("**5 Most Recent Quotations**")
if quotes:
    recent_q = pd.DataFrame(quotes[-5:])
    cols_q = [c for c in ["inv_numb", "inv_to", "total_amount", "oust_amount", "status"]
              if c in recent_q.columns]
    recent_q = recent_q[cols_q].copy()
    recent_q["total_amount"] = pd.to_numeric(recent_q["total_amount"], errors="coerce").apply(
        lambda x: f"R {x:,.2f}" if pd.notna(x) else "—")
    recent_q["oust_amount"]  = pd.to_numeric(recent_q["oust_amount"],  errors="coerce").apply(
        lambda x: f"R {x:,.2f}" if pd.notna(x) else "—")
    st.dataframe(
        recent_q,
        hide_index=True,
        width="stretch",
        column_config={
            "inv_numb":    st.column_config.TextColumn("Quote #"),
            "inv_to":      st.column_config.TextColumn("Client"),
            "total_amount":st.column_config.TextColumn("Total (R)"),
            "oust_amount": st.column_config.TextColumn("Outstanding (R)"),
            "status":      st.column_config.TextColumn("Status"),
        },
    )
else:
    st.info("No quotations yet.")

st.markdown("<hr style='border:1px solid #d1d5db; margin:1rem 0;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — Staff Summary
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 👥 Staff Summary")

s1, s2, s3 = st.columns(3)
with s1:
    with st.container(border=True):
        st.metric("👤 Total Staff", total_staff)
with s2:
    with st.container(border=True):
        st.metric("📅 Days Worked This Month", days_this_month)
with s3:
    with st.container(border=True):
        # Count unique staff who worked this month
        active_this_month = len({
            a.get("staff_id") for a in att_reg
            if str(a.get("att_date", "")).startswith(this_month)
        })
        st.metric("🏃 Active Staff This Month", active_this_month)

# Staff attendance this month as a bar chart
if att_reg:
    st.markdown("**Days worked per staff member this month**")
    month_att = [a for a in att_reg if str(a.get("att_date","")).startswith(this_month)]
    if month_att:
        att_df = pd.DataFrame(month_att)
        # Map staff_id → full_names for readable labels
        id_to_name = {u.get("user_id"): u.get("full_names", u.get("user_id"))
                      for u in abs_staff.get_all_users()}
        att_df["staff_name"] = att_df["staff_id"].map(id_to_name).fillna(att_df["staff_id"])
        days_per_staff = att_df.groupby("staff_name").size().reset_index(name="Days Worked")
        days_per_staff = days_per_staff.set_index("staff_name")
        st.bar_chart(days_per_staff, color="#2563eb")
    else:
        st.info("No attendance recorded this month yet.")

# Quick staff list
if staff:
    st.markdown("**Staff members**")
    staff_df = pd.DataFrame(staff)
    cols_s = [c for c in ["user_id", "full_names", "contact_numbers", "email"]
              if c in staff_df.columns]
    st.dataframe(
        staff_df[cols_s],
        hide_index=True,
        width="stretch",
        column_config={
            "user_id":         st.column_config.TextColumn("Staff ID"),
            "full_names":      st.column_config.TextColumn("Name"),
            "contact_numbers": st.column_config.TextColumn("Contact"),
            "email":           st.column_config.TextColumn("Email"),
        },
    )
