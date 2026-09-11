import streamlit as st
from models.Model import InvQouteUI
from models.User_Model import *

abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(page_title="Absaluminum".upper(), page_icon=abs_icon)

def gen_qoutation():
    st.title("Generate new qoutation".upper())
    qout_ui = InvQouteUI(invQouteUrl="https://script.google.com/macros/s/AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCVKsLwqrAJWkjOUVhZd7k9qA/exec?option=supabaseDB&invNumb=")
    st.session_state.edit_qout_inv = {}

    if st.session_state.get("edit_qoutation"):
        st.session_state.material_df = pd.DataFrame(columns=["Description", "Unit price", "Quantity", "Total amount"])
        st.session_state.update_qoutation = False
        st.session_state.edit_qoutation = False
    qout_ui.gen_ui(gen_message="**Generate Qoutation**")
    
def gen_invoice():
    st.title("Generate new invoice".upper())
    inv_ui = InvQouteUI()
    inv_ui.gen_ui(gen_message="**Generate Invoice**")

user = User()
if user.get_user():
    qoutation = 'Qoutation'
    with st.sidebar:
        st.header("Qoutation Navigation")
        qoutation = st.selectbox(
            "**Select an option below**",
            ["Qoutation", "Invoice"]
        )

    if qoutation.casefold() == "Qoutation".casefold():
        gen_qoutation() 
    elif qoutation.casefold() == "Invoice".casefold():
        gen_invoice()
