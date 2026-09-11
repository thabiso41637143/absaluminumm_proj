import streamlit as st
from models.User_Model import *

#page = st.sidebar.selectbox("Select a page", ["Home", "Qoute and Invoice", "Staff Members", "View Invoice and Qoute"])
abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(page_title="Absaluminum".upper(), page_icon=abs_icon)

st.image("Images/Heading_Letter_head.png")

st.title("Absaluminum (PTY) LTD".upper())
st.markdown("Welcome to the official quotation and invoice generator for **Absaluminum Projects**.")


user_role = "Admin"
if user_role:
    st.divider()

    st.header("Invoice Summary")

    st.divider()

    st.header("Staff Summary")
    
    # staff_summ = staffSummary()
    # st.write(staff_summ.get_staff_summary())
    # days, amount = st.columns(2, border=True)
    # with days:
    #     st.subheader("Days Summary")
    #     staff_summ.get_staff_days_chat()
    # with amount:
    #     st.subheader("Amount Summary")

    st.divider()

    st.header("Quotation Summary")