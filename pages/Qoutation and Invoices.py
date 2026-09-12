import streamlit as st
from models.Model import InvQouteUI, init_data, inject_css
from models.User_Model import *

abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(
    page_title="New Quotation / Invoice | Absaluminum".upper(),
    page_icon=abs_icon,
    layout="wide",
)
inject_css()

# Google Apps Script base URL shared by both modes
_GAS_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCV"
    "KsLwqrAJWkjOUVhZd7k9qA/exec?option=supabaseDB&invNumb="
)
_GAS_INV_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCV"
    "KsLwqrAJWkjOUVhZd7k9qA/exec?option=supabaseDB&menue=createInvoice&invNumb="
)


def _clear_form():
    """Reset all form state so switching modes starts with a clean slate."""
    for key in (
        "material_df", "edit_material_df", "materials_editor",
        "edit_items", "current_status", "edit_qout_inv",
        "Invto", "cust_tax", "email", "contnumb", "adr",
        "custtype", "Invnumb", "date", "duedate",
        "sub_tot", "less_disc", "tax_amount", "tot_bal",
        "discount_input_value", "inst_cost_input", "tax_input", "dep_input",
        "finalise_details", "results_status", "qoute_results",
    ):
        st.session_state.pop(key, None)


def gen_qoutation():
    st.title("📝 Generate New Quotation")
    st.session_state.edit_qout_inv = st.session_state.get("edit_qout_inv") or {}

    if st.session_state.get("edit_qoutation"):
        st.session_state.material_df = pd.DataFrame(
            columns=["Description", "Unit price", "Quantity", "Total amount"]
        )
        st.session_state.update_qoutation = False
        st.session_state.edit_qoutation = False

    qout_ui = InvQouteUI(invQouteUrl=_GAS_URL)
    qout_ui.gen_ui(gen_message="**Generate Quotation**")


def gen_invoice():
    st.title("🧾 Generate New Invoice")
    st.session_state.edit_qout_inv = st.session_state.get("edit_qout_inv") or {}

    inv_ui = InvQouteUI(invQouteUrl=_GAS_INV_URL)
    inv_ui.gen_ui(gen_message="**Generate Invoice**")


user = User()
if user.get_user():
    with st.sidebar:
        st.header("Create Document")
        mode = st.selectbox(
            "**Select document type**",
            ["Quotation", "Invoice"],
            key="create_mode",
        )

    # Detect mode switch and clear form to prevent bleed-over between modes
    prev_mode = st.session_state.get("_prev_create_mode")
    if prev_mode is not None and prev_mode != mode:
        _clear_form()
    st.session_state["_prev_create_mode"] = mode

    if mode == "Quotation":
        gen_qoutation()
    elif mode == "Invoice":
        gen_invoice()
