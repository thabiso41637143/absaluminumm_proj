import streamlit as st
from models.Model import init_data, inject_css
from models.User_Model import *
from models.Inv_Man_Model import *

abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(
    page_title="Manage Invoices | Absaluminum".upper(),
    page_icon=abs_icon,
    layout="wide",
)
inject_css()

user = User()
if user.get_user():
    if "loaded" not in st.session_state:
        init_data()
        st.session_state.loaded = True

    new_invoice = InvManager()

    if not st.session_state.get("edit_inv", False):
        new_invoice.list_inv()
        if st.button("⚙️ Manage Invoices"):
            st.session_state.edit_inv = True
            st.session_state.inv_page = 0
            st.rerun()
    else:
        new_invoice.set_inv_UI()
