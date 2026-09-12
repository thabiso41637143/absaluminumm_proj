import streamlit as st
from models.Model import init_data, inject_css
from models.Qout_Manag_Model import *
import webbrowser
from models.User_Model import *

abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(
    page_title="Manage Quotations | Absaluminum".upper(),
    page_icon=abs_icon,
    layout="wide",
)
inject_css()


def qouteTable(df):
    df = df.drop(columns=[c for c in ["qoute_doc"] if c in df.columns])
    df["payed_amount"] = df["payed_amount"].apply(lambda x: f"R {float(x):,.2f}" if str(x).replace('.', '', 1).isdigit() else x)
    df["total_amount"] = df["total_amount"].apply(lambda x: f"R {float(x):,.2f}" if str(x).replace('.', '', 1).isdigit() else x)
    df["oust_amount"]  = df["oust_amount"].apply(lambda x: f"R {float(x):,.2f}"  if str(x).replace('.', '', 1).isdigit() else x)
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "inv_numb":     st.column_config.TextColumn("Inv Number"),
            "inv_to":       st.column_config.TextColumn("Inv To"),
            "payed_amount": st.column_config.TextColumn("Paid (R)"),
            "total_amount": st.column_config.TextColumn("Total (R)"),
            "oust_amount":  st.column_config.TextColumn("Outstanding (R)"),
            "status":       st.column_config.TextColumn("Status"),
            "qoute_pdf":    st.column_config.LinkColumn("Quotation", display_text="View Quotation"),
        },
    )


def quotation_list():
    hdr_col, refresh_col = st.columns([5, 1])
    with hdr_col:
        st.title("📋 Quotations")
    with refresh_col:
        st.write("")
        if st.button("🔄 Refresh", use_container_width=True, key="qout_list_refresh"):
            init_data()
            st.session_state.loaded = True
            st.rerun()

    if st.session_state.qouteSummary:
        # Summary stats in list view
        all_q      = st.session_state.qouteSummary
        waiting    = sum(1 for q in all_q if str(q.get('status', '')).lower() == 'waiting')
        inprogress = sum(1 for q in all_q if str(q.get('status', '')).lower() == 'inprogress')
        invoiced   = sum(1 for q in all_q if str(q.get('status', '')).lower() == 'invoiced')
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("⏳ Waiting", waiting)
        with c2: st.metric("🚧 In Progress", inprogress)
        with c3: st.metric("✅ Invoiced", invoiced)
        st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0 1rem 0;'>", unsafe_allow_html=True)

        df = pd.DataFrame(st.session_state.qouteSummary)
        qouteTable(df=df)
    else:
        st.info("No quotations found.")


# ============================================================
user = User()
if user.get_user():
    if "loaded" not in st.session_state:
        init_data()
        st.session_state.loaded = True

    if not st.session_state.get("edit_qoute", False):
        quotation_list()
        if st.button("⚙️ Manage Quotations"):
            st.session_state.edit_qoute = True
            st.session_state.qout_page = 0
            st.rerun()
    else:
        edit_qout = Qoute_Manager()
        edit_qout.set_qout_UI()
