import streamlit as st
import requests
import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
import threading
from urllib.parse import urlencode
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

def _get_supabase():
    """
    Return a Supabase client that is scoped to the current Streamlit session.
    Creating it once per session (instead of once at module import) prevents
    the JWT-expired error on long-running deployments like Streamlit Cloud,
    where the module-level client would go stale without the process restarting.
    """
    if "supabase_client" not in st.session_state:
        st.session_state.supabase_client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY"),
        )
    return st.session_state.supabase_client

# Module-level proxy — all existing code that does `supabase.table(...)` keeps
# working without any changes elsewhere in the codebase.
class _SupabaseProxy:
    """Thin proxy that forwards every attribute access to the per-session client."""
    def __getattr__(self, name):
        return getattr(_get_supabase(), name)

supabase = _SupabaseProxy()

# ---------------------------------------------------------------------------
# Shared CSS – call inject_css() once per page instead of duplicating the
# block in every module that imports Model.
# ---------------------------------------------------------------------------
_CSS = """
<style>
/* ---------- PAGE BACKGROUND ---------- */
.stApp {
    background-color: #e4ebed;
    font-family: "Segoe UI", sans-serif;
}
/* ---------- BASE TEXT (stronger contrast for readability) ---------- */
.stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stMarkdown {
    color: #1f2937;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}
/* ---------- HEADERS ---------- */
h1, h2, h3 {
    color: #111827;
    font-weight: 600;
}
/* ---------- CARDS ---------- */
.card {
    background-color: #ffffff;
    padding: 1.2rem;
    border-radius: 12px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.06);
    margin-bottom: 1rem;
}
/* ---------- BUTTONS ---------- */
.stButton > button {
    border-radius: 8px;
    padding: 0.5rem 1.2rem;
    font-weight: 500;
}
.stButton > button[kind="primary"] {
    background-color: #59afcf;
    color: white;
    border: none;
}
.stButton > button[kind="secondary"] {
    background-color: #b3e1f2;
    color: #1f2937;
}
/* ---------- DATAFRAME ---------- */
[data-testid="stDataFrame"] {
    background-color: white;
    border-radius: 12px;
    padding: 0.5rem;
}
/* ---------- RADIO / SELECT ---------- */
.stRadio > label, .stSelectbox > label {
    font-weight: 500;
    color: #374151;
}

/* ==========================================================================
   MOBILE / SMALL-SCREEN OVERRIDES
   Streamlit shrinks type and cramps padding on narrow viewports. These rules
   only apply at <= 640px so the desktop layout is unchanged.
   ========================================================================== */
@media (max-width: 640px) {
    /* Give the app breathing room and a readable base size */
    html, body, .stApp {
        font-size: 17px;      /* base bumped up from browser default ~14-16px */
    }
    /* Tighten the default top/side padding so content isn't squeezed */
    .block-container {
        padding-top: 1rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }
    /* Body copy — larger and higher contrast */
    .stApp p, .stApp li, .stApp label, .stMarkdown, .stApp span {
        font-size: 1.02rem !important;
        line-height: 1.5 !important;
        color: #1f2937 !important;
    }
    /* Headings scaled for small screens (still clearly hierarchical) */
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.15rem !important; }
    /* Inputs: bigger text + 16px minimum stops iOS Safari auto-zooming on focus */
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stSelectbox div[data-baseweb="select"] {
        font-size: 16px !important;
    }
    /* Buttons: full-height tap targets and readable label */
    .stButton > button {
        font-size: 1rem !important;
        padding: 0.65rem 1rem !important;
    }
    /* Metrics (KPI numbers on the dashboard) — keep them legible, not huge */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
    }
    /* Dataframes/tables: allow horizontal scroll instead of crushing columns */
    [data-testid="stDataFrame"] {
        font-size: 0.9rem !important;
        overflow-x: auto !important;
    }
}
</style>
"""

def inject_css():
    """Inject shared app CSS. Safe to call multiple times – Streamlit deduplicates."""
    st.markdown(_CSS, unsafe_allow_html=True)

def gen_inv_numb():
    st.session_state.inv_numbs  = supabase.table("invGenerator")\
    .select("gen_id").eq("status","unused").execute().data
    if not st.session_state.inv_numbs:
        st.session_state.inv_numbs = supabase.table("invGenerator").insert({"status": "unused",}).execute().data

    st.session_state.gen_inv_numb = st.session_state.inv_numbs[0]['gen_id']

def get_totals():
    st.session_state.invoice_totals = supabase.table("Totals").select("*").execute().data

def get_invoice_details():
    st.session_state.invoice_details = supabase.table("InvoiceDetails").select("*").execute().data

def get_items():
    st.session_state.items_details = supabase.table("Items").select("*").execute().data

def get_invoice_summary():
    st.session_state.invoice_summary = supabase.table("InvoiceSummary").select("*").execute().data

def get_customer_category():
    st.session_state.customer_category = supabase.table("CustomerCategory").select("category, starting_number").execute().data

def init_data():
    gen_inv_numb()
    qoutSummary()
    get_invoice_details()
    get_totals()
    get_items()
    get_invoice_summary()
    get_customer_category()
    # Build O(1) lookup indexes so callers don't have to linear-scan the lists.
    st.session_state._qout_summary_idx   = {q['inv_numb']: q for q in st.session_state.qouteSummary}
    st.session_state._inv_details_idx    = {d['inv_numb']: d for d in st.session_state.invoice_details}
    st.session_state._inv_totals_idx     = {t['inv_numb']: t for t in st.session_state.invoice_totals}
    st.session_state._items_idx          = {}
    for item in st.session_state.items_details:
        st.session_state._items_idx.setdefault(item['inv_numb'], []).append(item)

def qoutSummary():
    st.session_state.qouteSummary = supabase.table("QouteSummary")\
    .select("inv_numb, inv_to, payed_amount, total_amount, oust_amount, status, qoute_doc, qoute_pdf").execute().data

def init_users():
    st.session_state.int_users = supabase.table("users")\
    .select("user_id, full_names, type, home_location, work_location, email, group_id, contact_numbers, comments")\
    .in_('group_id', [219, 207]).execute().data

def init_staff_rate():
    st.session_state.init_staffrate = supabase.table('StaffRates').select('*').execute().data

def init_att_reg():
    st.session_state.init_att_register = supabase.table('StaffAttendance').select('*').execute().data

def init_loans():
    st.session_state.init_loans = supabase.table('StaffLoans').select('*').execute().data

def init_payments():
    st.session_state.init_payments = supabase.table('StaffPayment').select('*').execute().data

#Invoice Qoutation class
class InvQouteUI:
    def __init__(self, invQouteUrl = None, tax_rate = 0.15, deposite_rate = 0.7):
        self.TAX_RATE = tax_rate
        self.DEPOSITE_RATE = deposite_rate
        self.invQouteUrl = invQouteUrl
        if "loaded" not in st.session_state:
            init_data()
            st.session_state.loaded = True
        if 'material_df' not in st.session_state:
            st.session_state.material_df = pd.DataFrame(columns=["Description", "Unit price", "Quantity", "Total amount"])
            st.session_state.edit_material_df = pd.DataFrame(columns=["Description", "Unit price", "Quantity"])

    def cust_details(self):
        st.write("**Customer Details**")
        self.inv_to = st.text_input("Invoiced To", key="Invto", value=st.session_state.edit_qout_inv.get("Invto"))
        self.cust_tax = st.text_input("Client VAT", key="cust_tax", value=st.session_state.edit_qout_inv.get("cust_tax"))
        self.cust_email = st.text_input("Client Email", key="email", value=st.session_state.edit_qout_inv.get("email"))
        self.cust_cont = st.text_input("Contact Numbers", key="contnumb", value=st.session_state.edit_qout_inv.get("contnumb"))
        self.cust_addr = st.text_area("Client Address", key="adr", value=st.session_state.edit_qout_inv.get("adr"), height="content")

    def totals(self):
        st.write("**TOTALS**")
        st.session_state["sub_tot"] = float(st.session_state.material_df["Total amount"].sum())
        self.sub_total = st.number_input("Sub Total",format="%0.2f", key="sub_tot", min_value=0.00, disabled=True)

        st.session_state["less_disc"] = float(st.session_state.material_df["Total amount"].sum() - st.session_state.get("discount_input_value", 0.00))
        self.tot_less_disc = st.number_input("Total Less Discount",format="%0.2f", min_value=0.00, disabled=True, key="less_disc")

        st.session_state["tax_amount"] = float(st.session_state.get("tax_input", 0.00))
        self.tot_inc_tax = st.number_input("Total Amount Inc Tax",format="%0.2f", min_value=0.00, disabled=True, key="tax_amount")

        st.session_state["tot_bal"] = float(self.tot_less_disc + self.tot_inc_tax + st.session_state.get("inst_cost_input", 0.00))
        self.tot_balance = st.number_input("Total Balance",format="%0.2f", min_value=0.00,disabled=True, key="tot_bal")

    def additional_totals(self):
        self.tax_input, self.discount_input, self.deposite_input, self.inst_cost_input = [0.00, 0.00, 0.00, 0.00]

        st.write("**ADDITIONAL TOTALS**")

        self.discount = st.checkbox("Add Discount", value=False, key="add_disc")
        if self.discount:
            st.session_state['discount_input_value'] = st.number_input("**Discount**",format="%0.2f", min_value=self.discount_input, max_value=float(st.session_state.material_df["Total amount"].sum()), key="discount_input")
        else:
            st.session_state['discount_input_value'] = 0.00

        self.inst_cost = st.checkbox("Add Installation Cost", value=True, key="add_inst")
        if self.inst_cost:
            st.session_state['inst_cost_input'] = float((st.session_state.material_df["Total amount"].sum()) * 0.1)
            self.inst_cost_input = st.number_input("**Installation Cost**",format="%0.2f", min_value=self.inst_cost_input, key="inst_cost_input")
        else:
            st.session_state['inst_cost_input'] = 0.00
        
        self.tax = st.checkbox("Add Tax Rate", value=False, key="add_tax", disabled=True)
        if self.tax:
            st.session_state['tax_input'] = float(((st.session_state.material_df["Total amount"].sum()) + self.inst_cost_input) * self.TAX_RATE)
            self.tax_input = st.number_input("**Tax Rate**",format="%0.2f", min_value=self.tax_input, disabled=True, key="tax_input")
        else:
            st.session_state['tax_input'] = 0.00
        
        self.deposite = st.checkbox("Add Deposit", value=True, key="add_dep")
        if st.session_state.get('add_dep'):
            self.total_am = float(((st.session_state.material_df["Total amount"].sum()) + st.session_state.get("inst_cost_input", 0.0) + st.session_state.get("tax_input", 0.0)) - st.session_state.get('discount_input_value',0.00))
            st.session_state['dep_input'] = (self.total_am * self.DEPOSITE_RATE)
            self.deposite_input = st.number_input("**Deposit**",format="%0.2f", min_value=self.deposite_input,max_value=self.total_am, key="dep_input")
        else:
            st.session_state['dep_input'] = 0.00

    def add_items_validator(self, item_descr, item_unit_price):
        self.valid = []
        if item_descr == None or item_descr.strip(" ") == "":
            self.valid.append(f"Please add the description of the item first on the **Descriptions** section.")

        if not item_unit_price > 0:
            self.valid.append(f"Please set the price of the product on **Unit Price** section")

        if st.session_state.get("custtype", None) == None:
            self.valid.append(f"Please make sure that you **select customer** first")
        
        if len(self.valid) > 0:
            self.validate_dilog(self.valid)
        return self.valid

    def add_items(self, item_descr, item_unit_price, item_qty, item_total_price):

        self.add_valid = self.add_items_validator(item_descr, item_unit_price)
        if len(self.add_valid) == 0:
            st.session_state.material_df.loc[len(st.session_state.material_df)] = [item_descr, item_unit_price, item_qty, item_total_price]
            st.session_state["current_status"] = "Reset"
            
    def capture_items(self):
        # ── Ensure both DataFrames always exist before anything reads them ──
        if "material_df" not in st.session_state:
            st.session_state.material_df = pd.DataFrame(
                columns=["Description", "Unit price", "Quantity", "Total amount"]
            )
        if "edit_material_df" not in st.session_state:
            st.session_state.edit_material_df = pd.DataFrame(
                columns=["Description", "Unit price", "Quantity"]
            )

        # ── Reset staging editor after a successful "Add to Items" ──────────
        if st.session_state.get("current_status", "") == "Reset":
            st.session_state.edit_material_df = pd.DataFrame(
                columns=["Description", "Unit price", "Quantity"]
            )
            st.session_state["current_status"] = ""
            if "materials_editor" in st.session_state:
                del st.session_state["materials_editor"]

        # ════════════════════════════════════════════════════════════════════
        # SECTION 1 — MATERIALS (staging / input area)
        # ════════════════════════════════════════════════════════════════════
        st.markdown(
            "<p style='font-size:1rem; font-weight:700; color:#1f2937; "
            "margin-bottom:0.2rem;'>📦 MATERIALS</p>"
            "<p style='font-size:0.82rem; color:#6b7280; margin-top:0;'>"
            "Add your rows below, then click <b>Add to Items</b> to confirm them.</p>",
            unsafe_allow_html=True,
        )

        st.data_editor(
            st.session_state.edit_material_df,
            num_rows="dynamic",
            width="stretch",
            key="materials_editor",
            column_config={
                "Description": st.column_config.TextColumn("Description", width="large"),
                "Unit price":  st.column_config.NumberColumn("Unit Price (R)", min_value=0, format="R %.2f"),
                "Quantity":    st.column_config.NumberColumn("Qty", min_value=1),
            },
        )

        add_col, _ = st.columns([1, 3])
        with add_col:
            add_clicked = st.button("➕ Add to Items", type="primary", use_container_width=True)

        if add_clicked:
            editor_state = st.session_state.get("materials_editor", {})
            base_df = st.session_state.edit_material_df.copy()

            # Apply added rows
            added_rows = editor_state.get("added_rows", [])
            if added_rows:
                base_df = pd.concat(
                    [base_df, pd.DataFrame(added_rows, columns=base_df.columns)],
                    ignore_index=True,
                )

            # Apply in-place edits
            for row_idx, changes in editor_state.get("edited_rows", {}).items():
                for col, val in changes.items():
                    base_df.at[int(row_idx), col] = val

            # Apply deletions
            deleted = editor_state.get("deleted_rows", [])
            base_df = base_df.drop(index=deleted).reset_index(drop=True)

            # Coerce + calculate Total amount
            base_df["Unit price"] = pd.to_numeric(base_df["Unit price"], errors="coerce").fillna(0.0)
            base_df["Quantity"]   = pd.to_numeric(base_df["Quantity"],   errors="coerce").fillna(1).astype(int)
            base_df["Total amount"] = base_df["Unit price"] * base_df["Quantity"]

            valid_rows = base_df[
                (base_df["Description"].notna()) &
                (base_df["Description"].str.strip() != "") &
                (base_df["Unit price"] > 0)
            ]

            if st.session_state.get("custtype") is None:
                st.warning("⚠️ Please select a customer type before adding items.")
            elif valid_rows.empty:
                st.warning("⚠️ Fill in at least one row with a Description and a Unit price greater than R 0.")
            else:
                st.session_state.material_df = pd.concat(
                    [st.session_state.material_df, valid_rows],
                    ignore_index=True,
                )
                st.session_state["current_status"] = "Reset"
                st.rerun()

        st.markdown("<hr style='border:1px solid #d1d5db; margin: 1rem 0;'>", unsafe_allow_html=True)

        # ════════════════════════════════════════════════════════════════════
        # SECTION 2 — LIST OF ITEMS (confirmed list)
        # ════════════════════════════════════════════════════════════════════
        item_count = len(st.session_state.material_df)
        st.markdown(
            f"<p style='font-size:1rem; font-weight:700; color:#1f2937; margin-bottom:0.2rem;'>"
            f"🧾 LIST OF ITEMS "
            f"<span style='font-weight:400; font-size:0.85rem; color:#6b7280;'>"
            f"({item_count} item{'s' if item_count != 1 else ''})</span></p>",
            unsafe_allow_html=True,
        )

        if item_count == 0:
            st.info("No items added yet. Use the MATERIALS table above to add items.")
        elif st.session_state.get("edit items"):
            # ── Editable mode ───────────────────────────────────────────────
            confirmed_edited = st.data_editor(
                st.session_state.material_df,
                num_rows="dynamic",
                width="stretch",
                key="edit_materials_editor",
                column_config={
                    "Description":  st.column_config.TextColumn("Description", width="large"),
                    "Unit price":   st.column_config.NumberColumn("Unit Price (R)", min_value=0, format="R %.2f"),
                    "Quantity":     st.column_config.NumberColumn("Qty", min_value=1),
                    "Total amount": st.column_config.NumberColumn("Total (R)", disabled=True, format="R %.2f"),
                },
            )
            confirmed_edited["Unit price"]   = pd.to_numeric(confirmed_edited["Unit price"],   errors="coerce").fillna(0.0)
            confirmed_edited["Quantity"]     = pd.to_numeric(confirmed_edited["Quantity"],     errors="coerce").fillna(1).astype(int)
            confirmed_edited["Total amount"] = confirmed_edited["Unit price"] * confirmed_edited["Quantity"]

            save_col, cancel_col, _ = st.columns([1, 1, 3])
            with save_col:
                if st.button("💾 Save Changes", type="primary", use_container_width=True):
                    st.session_state.material_df = confirmed_edited.copy()
                    st.session_state["edit items"] = False
                    st.rerun()
            with cancel_col:
                if st.button("✖ Cancel", use_container_width=True):
                    st.session_state["edit items"] = False
                    st.rerun()
        else:
            # ── Read-only display ────────────────────────────────────────────
            display_df = st.session_state.material_df.copy(deep=True)
            display_df["Unit price"]   = display_df["Unit price"].apply(lambda x: f"R {float(x):.2f}" if pd.notna(x) else x)
            display_df["Total amount"] = display_df["Total amount"].apply(lambda x: f"R {float(x):.2f}" if pd.notna(x) else x)
            st.dataframe(
                display_df,
                width="stretch",
                hide_index=True,
                column_config={
                    "Description":  st.column_config.TextColumn("Description"),
                    "Unit price":   st.column_config.TextColumn("Unit Price"),
                    "Quantity":     st.column_config.NumberColumn("Qty"),
                    "Total amount": st.column_config.TextColumn("Total"),
                },
            )

            edit_col, _ = st.columns([1, 4])
            with edit_col:
                if st.button("✏️ Edit Items", use_container_width=True):
                    st.session_state["edit items"] = True
                    st.rerun()

        st.markdown("<hr style='border:1px solid #d1d5db; margin: 1rem 0;'>", unsafe_allow_html=True)

        # ════════════════════════════════════════════════════════════════════
        # SECTION 3 — TOTALS
        # ════════════════════════════════════════════════════════════════════
        self.sub_total = st.session_state.material_df["Total amount"].sum()

        left, right = st.columns(2, border=True)
        with left:
            self.additional_totals()
        with right:
            self.totals()



    def summary(self):
        st.divider()
        st.title("Invoice/Quotation Summary")

        summary = st.container(border=True)
        with summary:
            col1, col2 = st.columns(2, border=False)
            with col1:
                st.write("**Invoice Number:** " + st.session_state.get("Invnumb"))
                st.write("**Customer Type:** " + st.session_state.get("custtype"))
                st.write("**Date:** " + st.session_state.get("date").strftime('%d %b %Y'))
                st.write("**Due Date:** " + st.session_state.get("duedate").strftime('%d %b %Y'))
            
            with col2:
                st.write("**Invoice To:** " + st.session_state.get("Invto"))
                st.write("**Email Address:** " + st.session_state.get("email"))
                st.write("**Contact Numbers:** " + st.session_state.get("contnumb"))
                st.write("**Address:** " + st.session_state.get("adr"))

        st.write(st.session_state.material_df)

        sub_boder = st.container(border=True)
        with sub_boder:
            tot1, tot2 = st.columns(2, border=False)
            with tot1:
                st.write(f"**Sub total:** R {float(st.session_state.get('sub_tot')):.2f}")
                st.write(f"**Total Less Discount:** R {float(st.session_state.get('less_disc')):.2f}")

            with tot2:
                if st.session_state.get("discount_input_value") > 0:
                    st.write(f"**Discount** R {float(st.session_state.get('discount_input_value')):.2f}")
                
                if st.session_state.get("inst_cost_input") > 0:
                    st.write(f"**Installation Cost:** R {float(st.session_state.get('inst_cost_input')):.2f}")

                if st.session_state.get("tax_input") > 0:
                    st.write(f"**Tax Amount:** R {float(st.session_state.get('tax_input')):.2f}")
                
                if st.session_state.get("dep_input") > 0:
                    st.write(f"**Deposite:** R {float(st.session_state.get('dep_input')):.2f}")
            
        st.markdown(
            f"<p style='color:red; text-decoration:underline; font-weight:bold; text-align:center;'>Total Amount: R {float(st.session_state.get('tot_bal')):.2f}</p>",
            unsafe_allow_html=True )

        st.divider()
    
    def invnumb_exists(self, invoice_numb: int) -> bool:
        response = (
            supabase.table("InvoiceDetails").select("inv_numb").eq("inv_numb", invoice_numb)
            .limit(1)
            .execute()
        )

        return bool(response.data)

    def submit_inv_qout_details(self):
        st.write("Submitting details to the server")
        print("Submitting details to the server")
        items = []
        for index, row in st.session_state.material_df.iterrows():
            items.append({"inv_numb": int(st.session_state.get("Invnumb")), 
            "item_description": row["Description"], "unit_price": row["Unit price"], 
            "quantity": row["Quantity"], "total_price": row["Total amount"]})

        inv_details = {"inv_date": st.session_state.get("date").isoformat(),
        "inv_numb": int(st.session_state.get("Invnumb")), "inv_to": st.session_state.get("Invto"), 
        "inv_duedate": st.session_state.get("duedate").isoformat(), "cust_group": st.session_state.get("custtype"),
        "cust_email": st.session_state.get("email"), "cust_numb": st.session_state.get("contnumb"), 
        "cust_address": st.session_state.get("adr"), "cust_tax": int(st.session_state.get("cust_tax"))  
        if st.session_state.get("cust_tax") else 0}

        total_inv = {"inv_numb": int(st.session_state.get("Invnumb")),
        "total_balance": float(st.session_state.get('tot_bal')), 
        "total_inctax": float(st.session_state.get('tax_input')),
        "total_lessdisc": float(st.session_state.get('less_disc')), 
        "sub_total": float(st.session_state.get('sub_tot')), 
        "deposit": float(st.session_state.get('dep_input')), 
        "tax_rate": 0.15, "installation_cost": float(st.session_state.get('inst_cost_input')), 
        "discount": float(st.session_state.get('discount_input_value'))
        }

        if not self.invnumb_exists(invoice_numb=inv_details.get("inv_numb")):
            self.invQouteUrl += str(inv_details.get("inv_numb"))
            try:
                response = supabase.table("InvoiceDetails").insert(inv_details).execute()
                response = supabase.table("Items").insert(items).execute()
                response = supabase.table("Totals").insert(total_inv).execute()
                respond = supabase.table("invGenerator").update({"status": "used"})\
                .eq("gen_id", st.session_state.gen_inv_numb).execute()
                st.write(f"Change status of the following number to used: {st.session_state.gen_inv_numb}")

                with st.spinner("⏳ Generating qoutation... Please wait."):
                    results_invqout = requests.get(self.invQouteUrl)

                self.reset_ui(json.loads(results_invqout.text))
                
            except Exception as e:
                print(e)
        else:
            st.write("Qoutation already exist.")
            
    def print_qoute_results(self):
        st.success("✅ Qoutation completed")
        st.session_state.qoute_results["payed_amount"] = st.session_state.qoute_results["payed_amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
        st.session_state.qoute_results["total_amount"] = st.session_state.qoute_results["total_amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
        st.session_state.qoute_results["oust_amount"] = st.session_state.qoute_results["oust_amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
        st.dataframe(
            st.session_state.qoute_results,
            hide_index=True,
            column_config={
                'inv_numb': st.column_config.TextColumn('Invoice No'),
                'inv_to': st.column_config.TextColumn('Invoiced To'),
                'qout_name': st.column_config.TextColumn('Qoute Name'),
                'total_amount': st.column_config.TextColumn('Total Amount (R)'),
                'payed_amount': st.column_config.TextColumn('Amount Payed (R)'),
                'oust_amount': st.column_config.TextColumn('Oustanding Amount (R)'),
                'status': st.column_config.TextColumn('Status'),
                'qoute_pdf': st.column_config.LinkColumn(
                    'PDF File', display_text='View PDF File'
                ),
                'qoute_doc': st.column_config.LinkColumn(
                    'Document File', display_text='View Doc File'
                ),
            }
        )
        st.session_state.results_status = False

    def clear_gui(self):
        st.session_state.material_df.drop(st.session_state.material_df.index, inplace=True)

    def reset_ui(self, results=pd.DataFrame()):
        st.session_state.qoute_results = pd.DataFrame([results])
        init_data() 
        self.clear_gui()       
        st.session_state.results_status = True
        st.session_state.loaded = True
        st.session_state.finalise_details = False
        st.rerun()
        
    def gen_ui(self, gen_message=""):
        left, right = st.columns(2, border=True)
        with left:
            customer = self.cust_details()

        with right:
            invoice = self.inv_details()
        
        mat = st.columns(1, border=True)
        with mat[0]:
            self.capture_items()
        
        if st.session_state.get("current_status", "") == "Reset":
            st.rerun()
        
        left_button, middle_button, right_button = st.columns([1, 1, 1], border=False)
        with left_button:
            if st.button(gen_message):
                self.finalise_inv_qout()
                st.session_state.finalise_details = True
        with right_button:
            if st.button("Cancel Qoutation"):
                st.session_state.update_qoutation = False
                st.session_state.edit_qoutation = False
                st.rerun()
        
        if st.session_state.get('finalise_details', False):
            if st.button("**Finalise Details**"):
                self.submit_inv_qout_details()
        
        if st.session_state.get('results_status', False):
            if 'qoute_results' in st.session_state:
                self.print_qoute_results()
        
            if st.button('**Close**'):
                st.rerun()

    def inv_details(self, cust_type = ""):
        cust_type = {}
        for record in st.session_state.customer_category:
            cust_type[record['category']] = record["starting_number"]       

        st.write("**Invoice Details**")
        if st.session_state.edit_qout_inv:
            st.session_state["custtype"] = st.session_state.edit_qout_inv.get("custtype")
            self.cust_selection = st.selectbox("Select Customer", cust_type.keys(),index=None, 
                                               key="custtype", disabled=True)
            # st.session_state["Invnumb"] = st.session_state.edit_qout_inv.get("Invnumb")
            self.inv_no = st.text_input("Inv Number",disabled=True, key="Invnumb", 
                                        value=st.session_state.edit_qout_inv.get("Invnumb"))
        else:
            self.cust_selection = st.selectbox("Select Customer", cust_type.keys(),index=None, 
                                               placeholder="Select customer", key="custtype", disabled=False)
            if self.cust_selection:
                st.session_state['Invnumb'] = f"{cust_type[self.cust_selection]}{date.today().year}{st.session_state.gen_inv_numb}"

            self.inv_no = st.text_input("Inv Number",disabled=True, key="Invnumb")

        if st.session_state.edit_qout_inv:
            self.inv_date = st.date_input("Inv Date", format="DD-MM-YYYY", key="date",
                                      value=st.session_state.edit_qout_inv.get("date"))
            # self.in_due_date = st.date_input("Inv Due Date", format="DD-MM-YYYY", 
            #                                  value=st.session_state.edit_qout_inv.get("duedate"), 
            #                                  key="duedate")
            future_date  = st.session_state.get('date') + timedelta(days=30)
            self.in_due_date = st.date_input("Inv Due Date", format="DD-MM-YYYY", value=future_date, key="duedate")
        else:
            self.inv_date = st.date_input("Inv Date", datetime.today(), format="DD-MM-YYYY", key="date")
            st.session_state["duedate"]  = st.session_state.get('date') + timedelta(days=30)
            # st.write(st.session_state["duedate"])
            self.in_due_date = st.date_input("Inv Due Date", format="DD-MM-YYYY", key="duedate")
            
        return [self.inv_no, self.inv_date.strftime("%d %b %Y"), self.in_due_date.strftime("%d %b %Y")]
        
    def warning_validator(self):
        self.warnings = []

        if st.session_state.get("email", "").strip(" ") == "":
            self.warnings.append(f"Email not filled!")

        if st.session_state.get("contnumb", "").strip(" ") == "":
            self.warnings.append(f"You didn't capture the client contact numbers!")

        if st.session_state.get("adr", "").strip(" ") == "":
            self.warnings.append(f"Client address was not added!")
        
        for w in self.warnings:
            st.warning(w)

    def finalise_inv_qout(self):
        self.input_validator = []

        if not st.session_state.material_df.shape[0] > 0:
            self.input_validator.append(f"Please Please add 1 product first")

        if st.session_state.get("Invto", "").strip(" ") == "":
            self.input_validator.append(f"Please Fill in the **Invoice to**")
        
        if st.session_state.get("custtype", None) == None:
            self.input_validator.append(f"Please make sure that you **select customer**")
        
        if len(self.input_validator) > 0:
            st.write(self.input_validator)
            self.validate_dilog(self.input_validator)
        else:
            self.warning_validator()
            self.summary()         

    @st.dialog("Invoice To")
    def validate_dilog(self, message):
        for m in message:
            st.write(m)

        if st.button("OKAY"):
            st.rerun()

    def __str__(self):
        return "Details of the user interface"

#Get data class
class  LoadStaffData:
    def __init__(self):
        self.load_trips_status = False
        self.load_cust_type_status = False
    
    def load_staff_tables(self):
        # Pass the callable, not the result of calling it.
        # Also avoid overwriting the method name with a status string.
        t = threading.Thread(target=self.get_staff_tables)
        t.start()
        t.join()  # Wait for the network call to finish before returning status.
        return st.session_state.get('tables error')

    def get_staff_tables(self):
        try:
            api_conne = requests.get("https://script.google.com/macros/s/AKfycbyZeOUxL5wj-shkOiysBLaLstwqNf2xRbz5r7MJNHBvdkR2qb2M_GEhxOg09hn-FIeRXg/exec?option=dataReader&menue=passdb")
            staff_tables = json.loads(api_conne.text)
            st.session_state['tables'] = staff_tables
            st.session_state["load_table_status"] = True
            self.load_staff_tables = "Completed"
            st.session_state['tables error'] = False
        except Exception as ex:
            print(ex)
            st.error("Failed to connect to the server and load tables")
            st.session_state['tables error'] = True

    def load_staff_trips(self):
        t = threading.Thread(target=self.get_staff_trips)
        t.start()
        t.join()
        return st.session_state.get('trips error')
    
    def get_staff_trips(self):
        try:
            api_conne = requests.get("https://script.google.com/macros/s/AKfycbyZeOUxL5wj-shkOiysBLaLstwqNf2xRbz5r7MJNHBvdkR2qb2M_GEhxOg09hn-FIeRXg/exec?option=dataReader&menue=getabsstaff")
            staff_trips = json.loads(api_conne.text)
            st.session_state['trips'] = staff_trips
            st.session_state["load_trips_status"] = True
            self.load_staff_trips = "Completed"
            st.session_state['trips error'] = False
        except Exception as ex:
            print(ex)
            st.error("Failed to connect to the server and load days for the staff")
            st.session_state['trips error'] = True

    def load_staff(self):
        self.load_staff_tables()
        self.load_staff_trips()
        if st.session_state.get('tables error') or st.session_state['trips error']:
            return True
        return False

#Staff Class
class StaffData:
    def __init__(self):
        self.staff_data = LoadStaffData()
        self.staff_db = sqlite3.connect("staffDatabase.db")
        self.staff_cursor = self.staff_db.cursor()
        self.data_success = not self.set_days()

    def __del__(self):
        """Close the SQLite connection when this object is garbage-collected."""
        try:
            self.staff_db.close()
        except Exception:
            pass

    def run_query_list(self, query_list = []):
        try:
            for query in query_list:
                self.staff_cursor.execute(query)
            self.staff_db.commit()
        except Exception:
            st.error(f"An error occured while running the query list{query_list}", icon="🚨")

    def set_tables(self):
        error_status = False
        if not st.session_state.get("load_table_status"):
            error_status = self.staff_data.load_staff()
        if not error_status:
            if st.session_state.get("load_table_status"):
                self.run_query_list(st.session_state.get("tables", {}).get('create tables', [])) 

        return error_status           

    def set_days(self):
        error_status = self.set_tables()
        if not error_status:
            if not st.session_state.get("load_trips_status"):
                self.staff_data.load_staff_trips()
            
            if st.session_state.get("load_table_status"):
                self.run_query_list(st.session_state.get('trips', {}).get("deleteData",[]))
                self.run_query_list(st.session_state.get('trips', {}).get("query",[]))
        return error_status

    def get_user(self, staff_id):
        if self.data_success:
            self.staff_cursor.execute("SELECT * FROM USER WHERE UPPER(userId) = ?",(staff_id,))
            return self.staff_cursor.fetchall()
        return []

    def get_staff_summary(self, staff_id):
        if self.data_success:
            return f"""
\nSalary: R
\nRate: R 
\nTotal number of days: {self.get_user_numdays(staff_id)} 
\n"""
        return f"failed to load staff summary data."

    def get_user_numdays(self, staff_id):
        if self.data_success:
            self.staff_cursor.execute("SELECT COUNT(*) FROM TRIPS WHERE UPPER(passid) = ?",(staff_id,))
            return self.staff_cursor.fetchone()[0]
        return 0

    def get_all_user(self):
        if self.data_success:
            self.staff_cursor.execute("SELECT * FROM USER")
            return self.staff_cursor.fetchall()
        return []
    
    def get_staff_dates(self, staff_id):
        if self.data_success:
            self.staff_cursor.execute("SELECT tripDate FROM TRIPS WHERE UPPER(passid) = ?",(staff_id,))
            return pd.DataFrame(self.staff_cursor.fetchall(), columns=["Date"])
        return f"No dates found"
    
    def get_staff_profile(self, staff_id):
        if self.data_success:
            data = self.get_user(staff_id)[0]
            return f"""**Staff ID:** {data[0]}
\n**Name:** {data[2]}
\n**Contacts:** {data[3]}
\n**Residential Address:** {data[5]}
\n**Company Name:** {data[6]}
"""
        return f"Staff data not found."

    #still under construction
    def get_staff_loan(self, staff_id): 
        return f"No loan is found"
    
    def get_all_staff_names(self):
        data = [(staff[0], staff[2])for staff in self.get_all_user()]
        return data

#Staff summary
class staffSummary:
    def __init__(self):
        self.staff_summary = StaffData()
        self.staff_cursor = self.staff_summary.staff_cursor
        self.data_success = self.staff_summary.data_success

    def get_staff_summary(self):
        if self.data_success:
            self.staff_cursor.execute("SELECT COUNT(*) FROM USER")
            numb_staff = self.staff_cursor.fetchone()[0]
            self.staff_cursor.execute("SELECT COUNT(*) FROM TRIPS")
            numb_days = self.staff_cursor.fetchone()[0]

            return f"""Total number of staff: {numb_staff}
    \nTotal number of days:{numb_days}"""
        return f"Failed to load staff data from the server."

    def get_staff_days_chat(self):
        if self.data_success:
            staff_names = []
            staff_days = []
            for  staff_id, staff_name in self.staff_summary.get_all_staff_names():
                staff_names.append(staff_name)
                staff_days.append(self.staff_summary.get_user_numdays(staff_id))
            
            data = pd.DataFrame({
                "Staff Names": staff_names, "Number of Days": staff_days
            })

            data = data.set_index("Staff Names")

            st.bar_chart(data)
            
#Suparbase staff details start here.
class AbsStaff:
    def __init__(self, abs_user):
        self.abs_user = abs_user
        self.att_reg = StaffAttendence(staff=self.abs_user)
        self.contract = Contract(staff=self.abs_user)
        self.loans = Loans(staff=self.abs_user)
        self.payments = StaffPayment(staff=self.abs_user)

    def get_profile(self):
        return f"""**Staff ID:** {self.abs_user.get('user_id')}
    \n**Name:** {self.abs_user.get('full_names')}
    \n**Contacts:** {self.abs_user.get('contact_numbers') if self.abs_user.get('contact_numbers') else ''}
    \n**Residential Address:** {self.abs_user.get('home_location')}
    \n**Company Name:** {self.abs_user.get('work_location')}
    """

    def get_summary(self):
        """
        Markdown summary: total days attended and salary, broken down by each
        rate/contract the staff member has used, plus a grand total.
        """
        rows, total_days, total_salary = self.contract.salary_breakdown()

        if not rows:
            base = (
                f"\n**Total days attended:** {int(self.att_reg.get_tot_days())}"
                f"\n\n**Salary:** R 0.00  \n*No active contract/rate set up yet.*\n"
            )
            outstanding = self.loans.get_total_outstanding()
            if outstanding > 0:
                base += f"\n⚠️ **Outstanding loan: −R {outstanding:,.2f}**\n"
            return base

        lines = ["| Rate / Job | Basis | Days | Hours | Salary |",
                 "|---|---|---:|---:|---:|"]
        for r in rows:
            label = r['rate_type'] or "—"
            if r.get('description') and r['rate_type'] in ('Per Job', 'Contract'):
                label = f"{r['rate_type']}: {r['description']}"
            rtype = str(r['rate_type'] or '').lower()
            if rtype == 'daily':
                basis = f"R {float(r['amount'] or 0):.2f}/day"
            elif rtype == 'hourly':
                basis = f"R {float(r['amount'] or 0):.2f}/hr"
            else:
                basis = f"R {float(r['amount'] or 0):.2f} fixed"
            lines.append(
                f"| {label} | {basis} | {r['days']} | {r['hours']:.0f} | R {r['salary']:.2f} |"
            )
        table = "\n".join(lines)

        # Outstanding loans reduce the payable salary.
        outstanding = self.loans.get_total_outstanding()
        net_salary  = total_salary - outstanding

        # total_days here counts only UNPAID days (paid days are historic and
        # excluded from the salary calc above).
        if total_days == 0 and total_salary == 0:
            base = (
                "\n✅ **No unpaid days pending.** All worked days have been paid.\n\n"
                "*Click 📅 Days to view the full history.*\n"
            )
            if outstanding > 0:
                base += f"\n⚠️ **Outstanding loan: −R {outstanding:,.2f}**\n"
            return base

        summary = (
            f"\n**Unpaid days pending payment:** {total_days}  \n"
            f"*Paid days are historic — click 📅 Days to view them.*\n\n"
            f"{table}\n\n"
            f"**Gross salary due: R {total_salary:,.2f}**\n"
        )
        if outstanding > 0:
            summary += (
                f"\n⚠️ **Outstanding loan: −R {outstanding:,.2f}**\n\n"
                f"**Net payable: R {net_salary:,.2f}**\n"
            )
        return summary

    def get_pay_figures(self):
        """Convenience: (gross_salary, outstanding_loan) for the pay form."""
        _, _, gross = self.contract.salary_breakdown()
        outstanding = self.loans.get_total_outstanding()
        return gross, outstanding

    def get_staff_dates(self):
        return f"No dates found"
    
    def get_staff_loan(self): 
        return f"No loan is found"
    
    def get_contract_summary(self):
        return f"Contract"
    
    def print_staff_dates(self):
        self.att_reg.print_att()
        
class Users:
    def __init__(self):
        if not 'int_users' in st.session_state:
            init_users()
        
        if not 'init_staffrate' in st.session_state:
            init_staff_rate()

        if not 'init_att_register' in st.session_state:
            init_att_reg()

        if not 'init_loans' in st.session_state:
            init_loans()

        if not 'init_payments' in st.session_state:
            init_payments()
    
    def print_details(self):
        st.write(st.session_state.int_users)
    
    def get_user(self, user_id):
        for u in self.get_all_users():
            if user_id == u.get('user_id'):
                return u
        
        return None
    
    def get_all_users(self):
        return st.session_state.int_users
    
    def get_abs_staff(self):
        abs_staff = []
        for u in self.get_all_users():
            if u.get('group_id') == 219:
                abs_staff.append(u)
        
        return abs_staff
    
    def get_user_profile(self, user_id):
        user_prof = self.get_user(user_id=user_id)
        if user_prof:
            return f"""**Staff ID:** {user_prof.get('user_id')}
\n**Name:** {user_prof.get('full_names')}
\n**Contacts:** {user_prof.get('contact_numbers') if user_prof.get('contact_numbers') else ''}
\n**Residential Address:** {user_prof.get('home_location')}
\n**Company Name:** {user_prof.get('work_location')}
"""
        return f"Staff data not found."

class Contract:
    def __init__(self, staff):
        self.staff = staff
        self.cont_data = {'staff_id': self.staff.get('user_id'), 'status': 'Active'}
    
    def set_gui(self):
        staff_id = self.staff.get('user_id')
        st.write(f"Create New Rate for: {self.staff.get('full_names')}")
        rate_type = st.selectbox(
            "Rate Type",
            options=['Daily', 'Hourly', 'Monthly', 'Weekly', 'Per Job', 'Contract'],
            key=f'contract_type_{staff_id}', index=None, placeholder='Select Rate Type'
        )

        # ── Per Job / Contract need an identifier so multiple concurrent
        #    jobs/contracts for the same staff member can be told apart. ──
        description = None
        if rate_type == 'Per Job':
            description = st.text_input(
                "Job Name / Reference",
                key=f'contract_desc_{staff_id}',
                placeholder="e.g. Kitchen windows – 12 Main St",
            )
            st.caption("Identifies this specific job when capturing attendance.")
        elif rate_type == 'Contract':
            description = st.text_input(
                "Contract Link / Reference",
                key=f'contract_desc_{staff_id}',
                placeholder="e.g. https://... or CONTRACT-2026-014",
            )
            st.caption("The staff contract link or reference number.")

        amount = st.number_input(
            label="Rate Amount (R)", min_value=0.00, format="%0.2f",
            key=f'rate_amount_{staff_id}',
        )
        status = st.selectbox(
            "Status", options=['Active', 'Completed', 'Paused', 'Suspended', 'Closed'],
            key=f'contract_status_{staff_id}', index=0,
        )

        self.cont_data['rate_type']   = rate_type
        self.cont_data['amount']      = amount
        self.cont_data['status']      = status
        self.cont_data['description'] = (description or "").strip() or None

        col1, col2 = st.columns(2, border=False)
        with col2:
            if st.button("Save Contract", key=f"save_contract_{staff_id}"):
                self.create_contract()
        with col1:
            if st.button("Cancel", key=f"cancel_contract_{staff_id}"):
                st.session_state.contract_updates = None
                st.rerun()

    def create_contract(self):
        ok, msg = self.validate_cont()
        if ok:
            supabase.table("StaffRates").insert(self.cont_data).execute()
            init_staff_rate()  # refresh cache so the new rate shows immediately
            st.session_state.contract_updates = None
            st.success("✅ Successfully created a contract.")
        else:
            st.error(f"❌ {msg}")

    def validate_cont(self):
        rt = self.cont_data.get('rate_type')
        if not rt:
            return False, "Please select a rate type."
        if not self.cont_data.get('amount') or self.cont_data['amount'] <= 0:
            return False, "Rate amount must be greater than R 0.00."
        if rt in ('Per Job', 'Contract') and not self.cont_data.get('description'):
            label = "job name" if rt == 'Per Job' else "contract link"
            return False, f"Please provide a {label} for this {rt} rate."
        return True, ""
    
    def get_user_rate(self):
        s_rate = []
        for r in st.session_state.init_staffrate:
            if r.get('staff_id') == self.staff.get('user_id'):
                s_rate.append(r)
        return s_rate

    def _attendance_for_rate(self, rate_id, unpaid_only=True):
        """Attendance rows this staff member logged against a specific rate.

        For salary we only count UNPAID days: once a payment has been made the
        worked days are marked 'Paid' and stop contributing to the summary /
        next salary (they remain visible under the Days button as history).
        """
        rows = [
            a for a in st.session_state.get('init_att_register', [])
            if a.get('staff_id') == self.staff.get('user_id')
            and a.get('rate_id') == rate_id
        ]
        if unpaid_only:
            rows = [a for a in rows if str(a.get('status', '')).strip().lower() != 'paid']
        return rows

    def calc_rate_earnings(self, rate):
        """
        Return (days, hours, salary) earned under a single rate row, following
        the rules for each rate type:
          Daily    -> amount * number of days worked
          Hourly   -> amount * total hours captured
          Monthly  -> fixed amount (paid once attendance exists)
          Per Job  -> fixed amount for that job
          Contract -> fixed amount for that contract
        """
        att   = self._attendance_for_rate(rate.get('rate_id'))
        days  = len(att)
        hours = sum(float(a.get('hours_worked', 0) or 0) for a in att)
        try:
            amount = float(rate.get('amount', 0) or 0)
        except (TypeError, ValueError):
            amount = 0.0

        rtype = str(rate.get('rate_type', '')).strip().lower()
        if rtype == 'daily':
            salary = amount * days
        elif rtype == 'hourly':
            salary = amount * hours
        elif rtype in ('monthly', 'weekly', 'per job', 'contract'):
            # Fixed rates: considered earned once there is at least one
            # attendance record logged against them.
            salary = amount if days > 0 else 0.0
        else:
            salary = 0.0

        return days, hours, salary

    def get_active_rates(self):
        """Only Active rates count toward staff salary. Non-active rates are
        kept for history but are never used to pay a staff member."""
        return [r for r in self.get_user_rate()
                if str(r.get('status', '')).strip().lower() == 'active']

    def salary_breakdown(self):
        """
        Per-rate dicts + grand totals for this staff member.
        Salary is computed ONLY from Active rates; inactive contracts are
        excluded from pay (they remain visible in the agreements history).
        """
        rows, total_days, total_salary = [], 0, 0.0
        for r in self.get_active_rates():
            days, hours, salary = self.calc_rate_earnings(r)
            rows.append({
                'rate_type':   r.get('rate_type'),
                'description': r.get('description'),
                'amount':      r.get('amount'),
                'status':      r.get('status'),
                'days':        days,
                'hours':       hours,
                'salary':      salary,
            })
            total_days   += days
            total_salary += salary
        return rows, total_days, total_salary

    def print_rate(self):
        if self.get_user_rate():
            st.subheader("Agreement Details".upper())
            rate_df = pd.DataFrame(self.get_user_rate())
            drop_cols = [c for c in ['rate_id', 'staff_id'] if c in rate_df.columns]
            rate_df = rate_df.drop(columns=drop_cols)
            if 'description' not in rate_df.columns:
                rate_df['description'] = None
            rate_df["amount"] = rate_df["amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
            # Order columns for readability
            ordered = [c for c in ['rate_type', 'description', 'amount', 'status'] if c in rate_df.columns]
            rate_df = rate_df[ordered]
            st.dataframe(
                rate_df,
                hide_index=True,
                column_config={
                    'rate_type':   st.column_config.TextColumn('Rate Type'),
                    'description': st.column_config.TextColumn('Job / Contract'),
                    'amount':      st.column_config.TextColumn('Rate Amount'),
                    'status':      st.column_config.TextColumn('Status'),
                },
                width='content'
            )
        else:
            st.write('There is no contract')

    STATUS_OPTIONS = ['Active', 'Completed', 'Paused', 'Suspended', 'Closed']

    def update_rate_status(self, rate_id, new_status):
        """Persist a status change for a single rate row, then refresh cache."""
        supabase.table("StaffRates").update({"status": new_status}).eq("rate_id", rate_id).execute()
        init_staff_rate()

    def review_agreements_gui(self):
        """
        Reviewable agreements panel: shows every rate (active + historic) and
        lets the user change each one's status. Only 'Active' rates are used to
        pay the staff member; others are kept for historic reference only.
        """
        rates = self.get_user_rate()
        if not rates:
            st.info("This staff member has no agreements yet. Use 'Add Contract' to create one.")
            return

        staff_id = self.staff.get('user_id')

        for r in rates:
            rate_id = r.get('rate_id')
            rtype   = r.get('rate_type') or '—'
            desc    = r.get('description')
            amount  = r.get('amount')
            current = r.get('status') or 'Active'
            is_active = str(current).strip().lower() == 'active'

            with st.container(border=True):
                # Header line: rate type + job/contract identifier
                title = rtype
                if desc and rtype in ('Per Job', 'Contract'):
                    title = f"{rtype} — {desc}"
                badge_color = "#16a34a" if is_active else "#9ca3af"
                st.markdown(
                    f"**{title}**  "
                    f"<span style='background:{badge_color}; color:white; padding:1px 8px; "
                    f"border-radius:10px; font-size:0.72rem;'>{current}</span>",
                    unsafe_allow_html=True,
                )
                try:
                    st.caption(f"Rate: R {float(amount or 0):.2f}")
                except (TypeError, ValueError):
                    st.caption(f"Rate: {amount}")

                # If it's a Contract with a URL, make it clickable
                if rtype == 'Contract' and desc and str(desc).lower().startswith(('http://', 'https://')):
                    st.markdown(f"🔗 [Open contract link]({desc})")

                # Status editor
                edit_col, save_col = st.columns([2, 1])
                with edit_col:
                    options = self.STATUS_OPTIONS
                    idx = options.index(current) if current in options else 0
                    chosen = st.selectbox(
                        "Status", options=options, index=idx,
                        key=f"agr_status_{staff_id}_{rate_id}",
                        label_visibility="collapsed",
                    )
                with save_col:
                    if st.button("💾 Update", key=f"agr_save_{staff_id}_{rate_id}", use_container_width=True):
                        if chosen != current:
                            try:
                                self.update_rate_status(rate_id, chosen)
                                st.success(f"Status changed to {chosen}.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not update status: {e}")
                        else:
                            st.info("Status unchanged.")

                if not is_active:
                    st.caption("ℹ️ Not Active — kept for history, not used for salary.")

class StaffAttendence:
    def __init__(self, staff):
        self.staff = staff
        self.st_rate = self.get_rate()
        self.rate_data = {'staff_id': self.staff.get('user_id'), }
    
    def set_gui(self):
        st.write(f"**Attendentce Register for {self.staff.get('full_names')}**")
        staff_id = self.staff.get('user_id')

        if not self.st_rate:
            st.warning(
                f"⚠️ No contract/rate found for **{self.staff.get('full_names')}**. "
                "Please add a contract on the Staff Summary tab before capturing attendance."
            )
            # Mark as invalid so capture_att() knows to skip this staff member
            self.rate_data['_no_rate'] = True
            return

        # Build a display label → rate record mapping so the selected label
        # resolves to the correct rate_id. For Per Job / Contract we include the
        # description so a staff member with several concurrent jobs/contracts
        # can pick exactly the right one.
        def _rate_label(r):
            base = f"{r.get('rate_type')} - R {r.get('amount')}"
            desc = r.get('description')
            if desc and r.get('rate_type') in ('Per Job', 'Contract'):
                return f"{r.get('rate_type')} ({desc}) - R {r.get('amount')}"
            return base

        # Only offer Active rates for capturing new attendance.
        active_rates = [r for r in self.st_rate if str(r.get('status', '')).lower() == 'active'] or self.st_rate
        rate_labels = [_rate_label(r) for r in active_rates]
        rate_map    = {_rate_label(r): r for r in active_rates}

        rate_choice = st.radio(label='Select Rate / Job', options=rate_labels, key=f"rate_choice_{staff_id}")

        d_col, h_col, s_col = st.columns(3, border=False)
        with d_col:
            st.date_input("Captured Date", datetime.today(), format="DD-MM-YYYY", key=f"capt_date_{staff_id}")
        with h_col:
            st.number_input("Total Hours", min_value=1, key=f"tot_hours_{staff_id}", value=int(8), max_value=24)
        with s_col:
            st.selectbox(label='Status', options=['Paid', 'Unpaid'], index=1, key=f'status_choice_{staff_id}')

        selected_rate = rate_map.get(rate_choice, active_rates[0])
        self.rate_data['att_date']     = st.session_state.get(f"capt_date_{staff_id}").isoformat()
        self.rate_data['status']       = st.session_state.get(f'status_choice_{staff_id}')
        self.rate_data['hours_worked'] = st.session_state.get(f"tot_hours_{staff_id}")
        self.rate_data['rate_id']      = selected_rate.get('rate_id')
        self.rate_data.pop('_no_rate', None)  # clear any previous no-rate flag

    def get_rate(self):
        s_rate = []
        for r in st.session_state.init_staffrate:
            if r.get('staff_id') == self.staff.get('user_id'):
                s_rate.append(r)
        return s_rate
    
    def capture_att(self):
        if self.rate_data.get('_no_rate'):
            raise ValueError(f"No contract rate found for {self.staff.get('full_names')} — skipped.")
        payload = {k: v for k, v in self.rate_data.items() if k != '_no_rate'}
        print(payload)
        supabase.table('StaffAttendance').insert(payload).execute()

    def get_unpaid_days(self):
        """Attendance rows for this staff member not yet marked as Paid."""
        return [a for a in self.get_days()
                if str(a.get('status', '')).strip().lower() != 'paid']

    def mark_all_paid(self):
        """Mark every currently-unpaid attendance row for this staff member as
        Paid. Called after a payment so those days become historic and stop
        counting toward the summary / next salary. Returns the count updated."""
        unpaid = self.get_unpaid_days()
        if not unpaid:
            return 0
        supabase.table('StaffAttendance').update({'status': 'Paid'})\
            .eq('staff_id', self.staff.get('user_id'))\
            .neq('status', 'Paid')\
            .execute()
        init_att_reg()
        return len(unpaid)

    def get_days(self):
        att_list = []
        for att in st.session_state.init_att_register:
            if att.get('staff_id') == self.staff.get('user_id'):
                att_list.append(att)
        
        return att_list

    def print_att(self):
        att_list = self.get_days()
        if att_list:
            # Map rate_id -> readable label so each day shows which job/contract.
            rate_lookup = {}
            for r in st.session_state.get('init_staffrate', []):
                if r.get('staff_id') == self.staff.get('user_id'):
                    lbl = r.get('rate_type') or '—'
                    if r.get('description') and r.get('rate_type') in ('Per Job', 'Contract'):
                        lbl = f"{r.get('rate_type')}: {r.get('description')}"
                    rate_lookup[r.get('rate_id')] = lbl

            att_df = pd.DataFrame(att_list)
            att_df['rate_used'] = att_df['rate_id'].map(rate_lookup).fillna('—')
            drop_cols = [c for c in ['att_id', 'created_at', 'staff_id', 'rate_id'] if c in att_df.columns]
            att_df = att_df.drop(columns=drop_cols)
            ordered = [c for c in ['att_date', 'rate_used', 'hours_worked', 'status'] if c in att_df.columns]
            att_df = att_df[ordered]
            st.subheader('Days worked'.upper())
            st.dataframe(
                att_df,
                hide_index=True,
                column_config={
                    'att_date':     st.column_config.TextColumn('Date Attended'),
                    'rate_used':    st.column_config.TextColumn('Rate / Job'),
                    'hours_worked': st.column_config.NumberColumn('Total Hours'),
                    'status':       st.column_config.TextColumn('Status'),
                },
                width='content'
            )
        else:
            st.write('There is no days worked.')

    def get_tot_days(self):
        return len(self.get_days())





# ─────────────────────────────────────────────────────────────────────────────
# Staff loans / advances
# ─────────────────────────────────────────────────────────────────────────────
class Loans:
    """Manage advances/loans given to a staff member.

    Status is derived from amounts:
      paid == 0            -> unsettled
      0 < paid < loan      -> partially settled
      paid >= loan         -> settled
    """

    STATUS_UNSETTLED = "unsettled"
    STATUS_PARTIAL   = "partially settled"
    STATUS_SETTLED   = "settled"

    def __init__(self, staff):
        self.staff = staff

    # ── Reads ────────────────────────────────────────────────────────────
    def get_loans(self):
        """All loan rows for this staff member (most recent first)."""
        loans = [
            l for l in st.session_state.get('init_loans', [])
            if l.get('staff_id') == self.staff.get('user_id')
        ]
        return sorted(loans, key=lambda l: str(l.get('loan_date', '')), reverse=True)

    def get_total_outstanding(self):
        """Sum of outstanding amounts across all not-fully-settled loans."""
        total = 0.0
        for l in self.get_loans():
            try:
                total += float(l.get('out_amount', 0) or 0)
            except (TypeError, ValueError):
                pass
        return total

    def has_unsettled(self):
        return self.get_total_outstanding() > 0

    # ── Helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _derive_status(loan_amount, paid_amount):
        loan = float(loan_amount or 0)
        paid = float(paid_amount or 0)
        if paid <= 0:
            return Loans.STATUS_UNSETTLED
        if paid >= loan:
            return Loans.STATUS_SETTLED
        return Loans.STATUS_PARTIAL

    # ── Writes ───────────────────────────────────────────────────────────
    def create_loan(self, loan_date, loan_amount, comments=None):
        loan_amount = float(loan_amount or 0)
        payload = {
            "staff_id":    self.staff.get('user_id'),
            "loan_date":   loan_date.isoformat() if hasattr(loan_date, 'isoformat') else loan_date,
            "loan_amount": loan_amount,
            "paid_amount": 0,
            "out_amount":  loan_amount,
            "status":      self._derive_status(loan_amount, 0),
            "comments":    (comments or "").strip() or None,
        }
        supabase.table("StaffLoans").insert(payload).execute()
        init_loans()

    def record_payment(self, loan_id, payment):
        """Add a repayment to an existing loan and recompute status/outstanding."""
        loan = next((l for l in self.get_loans() if l.get('loan_id') == loan_id), None)
        if not loan:
            raise ValueError("Loan not found.")
        loan_amount = float(loan.get('loan_amount', 0) or 0)
        new_paid    = float(loan.get('paid_amount', 0) or 0) + float(payment or 0)
        new_paid    = min(new_paid, loan_amount)          # never overpay
        out_amount  = max(loan_amount - new_paid, 0.0)
        supabase.table("StaffLoans").update({
            "paid_amount": new_paid,
            "out_amount":  out_amount,
            "status":      self._derive_status(loan_amount, new_paid),
        }).eq("loan_id", loan_id).execute()
        init_loans()

    def edit_loan_amount(self, loan_id, new_loan_amount):
        """Change the borrowed amount; keep paid as-is and recompute the rest."""
        loan = next((l for l in self.get_loans() if l.get('loan_id') == loan_id), None)
        if not loan:
            raise ValueError("Loan not found.")
        new_loan_amount = float(new_loan_amount or 0)
        paid       = min(float(loan.get('paid_amount', 0) or 0), new_loan_amount)
        out_amount = max(new_loan_amount - paid, 0.0)
        supabase.table("StaffLoans").update({
            "loan_amount": new_loan_amount,
            "paid_amount": paid,
            "out_amount":  out_amount,
            "status":      self._derive_status(new_loan_amount, paid),
        }).eq("loan_id", loan_id).execute()
        init_loans()

    def delete_loan(self, loan_id):
        supabase.table("StaffLoans").delete().eq("loan_id", loan_id).execute()
        init_loans()


# ─────────────────────────────────────────────────────────────────────────────
# Staff payments / payslips
# ─────────────────────────────────────────────────────────────────────────────
class StaffPayment:
    """Record and review payments made to a staff member.

    A payment stores the full money breakdown so a payslip can be
    reconstructed later:
        net_amount = gross_amount - loan_deduction - other_deduction
    Recording a payment also pushes the loan_deduction through
    Loans.record_payment() so the loan balance stays in sync.
    """

    def __init__(self, staff):
        self.staff = staff
        self.loans = Loans(staff=staff)

    # ── Reads ────────────────────────────────────────────────────────────
    def get_payments(self):
        """All payment rows for this staff member (most recent first)."""
        pays = [
            p for p in st.session_state.get('init_payments', [])
            if p.get('staff_id') == self.staff.get('user_id')
        ]
        return sorted(pays, key=lambda p: str(p.get('pay_date', '')), reverse=True)

    def get_total_paid(self):
        total = 0.0
        for p in self.get_payments():
            try:
                total += float(p.get('net_amount', 0) or 0)
            except (TypeError, ValueError):
                pass
        return total

    # ── Writes ───────────────────────────────────────────────────────────
    def create_payment(self, pay_date, gross_amount, loan_deduction=0.0,
                        other_deduction=0.0, method="Cash", status="Paid",
                        period_start=None, period_end=None, notes=None):
        """Insert a payment and settle the loan portion.

        Returns the inserted payment row (dict) so the caller can, e.g., pass
        it to a payslip generator.
        """
        gross = float(gross_amount or 0)
        loan  = max(float(loan_deduction or 0), 0.0)
        other = max(float(other_deduction or 0), 0.0)

        # Never let loan repayment exceed what is actually owed.
        outstanding = self.loans.get_total_outstanding()
        loan = min(loan, outstanding)

        net = gross - loan - other

        def _iso(d):
            return d.isoformat() if hasattr(d, 'isoformat') else (d or None)

        payload = {
            "staff_id":        self.staff.get('user_id'),
            "pay_date":        _iso(pay_date),
            "period_start":    _iso(period_start),
            "period_end":      _iso(period_end),
            "gross_amount":    gross,
            "loan_deduction":  loan,
            "other_deduction": other,
            "net_amount":      net,
            "method":          method,
            "status":          status,
            "pay_doc":         "",
            "pay_pdf":         "",
            "notes":           (notes or "").strip() or None,
        }

        result = supabase.table("StaffPayment").insert(payload).execute()

        # Apply the loan repayment portion across outstanding loans (oldest first).
        if loan > 0:
            self._apply_loan_repayment(loan)

        # Mark all currently-unpaid worked days as Paid so they become historic
        # and no longer count toward the summary / next salary.
        try:
            StaffAttendence(staff=self.staff).mark_all_paid()
        except Exception as e:
            print(f"[create_payment] mark_all_paid failed: {e}")

        init_payments()
        return (result.data or [payload])[0]

    def _apply_loan_repayment(self, amount):
        """Distribute a repayment across the staff member's outstanding loans,
        oldest first, using the existing Loans.record_payment logic."""
        remaining = float(amount or 0)
        # Oldest first so the longest-standing debt is cleared first.
        loans_oldest = sorted(
            [l for l in self.loans.get_loans() if float(l.get('out_amount', 0) or 0) > 0],
            key=lambda l: str(l.get('loan_date', '')),
        )
        for loan in loans_oldest:
            if remaining <= 0:
                break
            owed = float(loan.get('out_amount', 0) or 0)
            pay  = min(owed, remaining)
            self.loans.record_payment(loan.get('loan_id'), pay)
            remaining -= pay
