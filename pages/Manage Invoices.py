from models.Model import InvQouteUI
import streamlit as st
from models.User_Model import *
from models.Inv_Man_Model import *


abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(page_title="Absaluminum".upper(), page_icon=abs_icon)

def edit_invoice():
    new_invoice.set_inv_UI()  
    
user = User()

if user.get_user():
    if "loaded" not in st.session_state:
        init_data()
        st.session_state.loaded = True

    new_invoice = InvManager()

    if not st.session_state.get("edit_inv", False):
        new_invoice.list_inv()

        if st.button("**More Options...**"):
            st.session_state.edit_inv = True
            st.session_state.inv_page = 0
            st.rerun()

    else:
        edit_invoice()

