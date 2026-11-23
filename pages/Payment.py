import streamlit as st
from models.Model import init_data, inject_css
from models.User_Model import *
from models.Payment_Model import *

abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(
    page_title="Payment | Absaluminum".upper(),
    page_icon=abs_icon,
    layout="wide",
)
inject_css()

user = User()
if user.get_user():
    if "loaded" not in st.session_state:
        init_data()
        st.session_state.loaded = True

    # ── Header ────────────────────────────────────────────────────────
    hdr_col, refresh_col = st.columns([5, 1])
    with hdr_col:
        st.title("💰 Payment")
        st.markdown(
            "<p style='color:#6b7280; margin-top:4px;'>"
            "Track outstanding quotations and invoices, and capture payments.</p>",
            unsafe_allow_html=True,
        )
    with refresh_col:
        st.write("")
        if st.button("🔄 Refresh", use_container_width=True, key="payment_refresh"):
            init_data()
            st.session_state.loaded = True
            st.rerun()

    st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0 1.2rem 0;'>",
                unsafe_allow_html=True)

    manager = PaymentManager()

    summary_tab, pay_quote_tab, pay_inv_tab = st.tabs(
        ["📊 Payment Summary", "💳 Pay Quotation", "🧾 Pay Invoice"]
    )

    with summary_tab:
        manager.payment_summary()
    with pay_quote_tab:
        manager.pay_quotation()
    with pay_inv_tab:
        manager.pay_invoice()
