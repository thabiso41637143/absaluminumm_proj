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

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

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
/* ---------- HEADERS ---------- */
h1, h2, h3 {
    color: #1f2937;
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
            st.session_state.edit_material_df = st.session_state.material_df.copy()

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
        st.write("**MATERIALS**")
        if st.session_state.get("current_status", "") == "Reset":
            self.descr, self.unit_price, self.qty_value = None, 0.00, 1
            st.session_state["current_status"] = ""
        else:
            self.descr, self.unit_price, self.qty_value = st.session_state.get("descr", None), st.session_state.get("unit_price", 0.00), st.session_state.get("qty", 1)

        edited_df = st.data_editor(
            st.session_state.edit_material_df,
            num_rows="dynamic",
            use_container_width=True,
            key="materials_editor",
            column_config={
                "Unit price": st.column_config.NumberColumn(min_value=0),
                "Quantity": st.column_config.NumberColumn(min_value=1),
                "Total amount": st.column_config.NumberColumn(disabled=True),
            }
        )

        # self.item_descr = st.text_area("Descriptions", key="descr", value=self.descr)

        # up, qty, tp = st.columns(3)

        # with up:
        #     self.item_unit_price = st.number_input("Unit Price",format="%0.2f", min_value=0.00,value=float(self.unit_price), key="unit_price")

        # with qty:
        #     self.item_qty = st.number_input("Quantity", min_value=1, key="qty", value=int(self.qty_value))

        # if self.item_unit_price > 0 or self.item_qty > 1:
        #     st.session_state.total_price = self.item_qty * self.item_unit_price

        # with tp:
        #     self.item_total_price = st.number_input("Total Price", format="%0.2f", key="total_price", disabled=True)

        # if st.button("**Update totals**"):
        #     self.add_items(self.item_descr, self.item_unit_price, self.item_qty, self.item_total_price)

        if not edited_df.empty:
            edited_df["Total amount"] = edited_df["Unit price"] * edited_df["Quantity"]

        st.session_state.edit_material_df = edited_df

        st.session_state.material_df = st.session_state.edit_material_df.copy()

        df = st.session_state.material_df.copy(deep=True)
        df["Total amount"] = df["Total amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
        
        df["Unit price"] = df["Unit price"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
        
        if st.session_state.get("edit items"):
            self.edit_items()

        st.write("**List of items**")
        st.table(df)
        #I must work on this section
        if len(st.session_state.material_df) > 0:
            if st.button("Edit Items"):
                st.session_state["edit items"] = True
                st.session_state.edit_material_df = st.session_state.material_df.copy()
                st.rerun()

        self.sub_total = st.session_state.material_df["Total amount"].sum()

        left, right = st.columns(2, border=True)
        with left:
            self.additional_totals()

        with right:
            self.totals()

    def edit_items(self):

        edited_df = st.data_editor(
            st.session_state.edit_material_df,
            num_rows="dynamic",
            use_container_width=True,
            key="materials_editor",
            column_config={
                "Unit price": st.column_config.NumberColumn(min_value=0),
                "Quantity": st.column_config.NumberColumn(min_value=1),
                "Total amount": st.column_config.NumberColumn(disabled=True),
            }
        )

        if not edited_df.empty:
            edited_df["Total amount"] = edited_df["Unit price"] * edited_df["Quantity"]

        st.session_state.edit_material_df = edited_df
#         for index, row in st.session_state.material_df.iterrows():
#             description, unit_price, quantity, total_amount, delete = st.columns(5, border=False)
# #"Description", "Unit price", "Quantity", "Total amount"
#             with description:
#                 st.text_area("Description",key="descr"+str(index), value=row['Description'])
#             with unit_price:
#                 st.text_input("Unit Price",key="unit_price_"+str(index), value=row["Unit price"])
#             with quantity:
#                 st.text_input("Qty", key="qty_"+str(index), value=row["Quantity"])
#             with total_amount:
#                 st.text_input("Total Amount", key="total_amount_"+str(index), value=row["Total amount"])
#             with delete:
#                 st.button("Delete...", key="delete_"+str(index))
            

        cancel, save = st.columns(2, border=False)
        with cancel:
            if st.button("Cancel"):
                pass
        with save:
            if st.button("Save"):
                pass

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

    def get_profile(self):
        return f"""**Staff ID:** {self.abs_user.get('user_id')}
    \n**Name:** {self.abs_user.get('full_names')}
    \n**Contacts:** {self.abs_user.get('contact_numbers') if self.abs_user.get('contact_numbers') else ''}
    \n**Residential Address:** {self.abs_user.get('home_location')}
    \n**Company Name:** {self.abs_user.get('work_location')}
    """
    
    def get_summary(self):
        return f"""
\nSalary: R
\nTotal number of days: {int(self.att_reg.get_tot_days())}
\n"""

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
        st.write(f"Create New Rate for: {self.staff.get('full_names')}")
        st.selectbox("Contract Type", options=['Daily Rate', 'Fixed Rate', 'Monthly Rate', 'Weekly Rate'], key='contract_type', index=None, placeholder='Select Contract')
        st.number_input(label="Rate Amount", min_value=0.00, format="%0.2f", key='rate_amount')

        self.cont_data['rate_type'] = st.session_state.contract_type
        self.cont_data['amount'] = st.session_state.rate_amount

        col1, col2 = st.columns(2, border=False)
        with col2:
            if st.button("Save Contract"):
                self.create_contract()
        with col1:
            if st.button("Cancel"):
                st.session_state.contract_updates = None
                st.rerun()            

    def create_contract(self):
        if self.validate_cont():
            response = supabase.table("StaffRates").insert(self.cont_data).execute()
            st.session_state.contract_updates = None
            st.write("Successfully Created a contract.")
        else:
            st.write("Uable to create a contract.")
    
    def validate_cont(self):
        return True
    
    def get_user_rate(self):
        s_rate = []
        for r in st.session_state.init_staffrate:
            if r.get('staff_id') == self.staff.get('user_id'):
                s_rate.append(r)
        return s_rate

    def print_rate(self):
        if self.get_user_rate():
            st.subheader("Agreement Details".upper())
            rate_df = pd.DataFrame(self.get_user_rate())
            rate_df = rate_df.drop(columns=['rate_id', 'staff_id'])
            rate_df["amount"] = rate_df["amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
            st.dataframe(
                rate_df,
                hide_index=True,
                column_config={
                    'rate_type': st.column_config.TextColumn('Rate Type'),
                    'amount': st.column_config.TextColumn('Rate Amount'),
                    'status': st.column_config.TextColumn('Status')
                },
                width='content'
            )
        else:
            st.write('There is no contract')

class StaffAttendence:
    def __init__(self, staff):
        self.staff = staff
        self.st_rate = self.get_rate()
        self.rate_data = {'staff_id': self.staff.get('user_id'), }
    
    def set_gui(self):
        st.write(f"**Attendentce Register for {self.staff.get('full_names')}**")
        staff_id = self.staff.get('user_id')
        # st.write(self.st_rate)
        rate_choice = st.radio(label='Select Rate', options=[f"{r.get('rate_type')} - R {r.get('amount')}" for r in self.st_rate])
        d_col, h_col, s_col = st.columns(3, border=False)
        # st.date_input("Inv Date", datetime.today(), format="DD-MM-YYYY", key="date")
        with d_col:
            st.date_input("Captured Date", datetime.today(), format="DD-MM-YYYY", key=f"capt_date_{staff_id}")
        with h_col:
            st.number_input("Total Hours", min_value=1, key=f"tot_hours_{staff_id}", value=int(8), max_value=24)
        with s_col:
            st.selectbox(label='Status', options=['Paid', 'Unpaid'], index=1, key=f'status_choice_{staff_id}')
        
        self.rate_data['att_date'] = st.session_state.get(f"capt_date_{staff_id}").isoformat()
        self.rate_data['status'] = st.session_state.get(f'status_choice_{staff_id}')
        self.rate_data['hours_worked'] = st.session_state.get(f"tot_hours_{staff_id}")
        self.rate_data['rate_id'] = self.st_rate[0].get('rate_id')

    def get_rate(self):
        s_rate = []
        for r in st.session_state.init_staffrate:
            if r.get('staff_id') == self.staff.get('user_id'):
                s_rate.append(r)
        return s_rate
    
    def capture_att(self):
        print(self.rate_data)
        response = supabase.table('StaffAttendance').insert(self.rate_data).execute()

    def get_days(self):
        att_list = []
        for att in st.session_state.init_att_register:
            if att.get('staff_id') == self.staff.get('user_id'):
                att_list.append(att)
        
        return att_list

    def print_att(self):
        att_list = self.get_days()
        if att_list:
            att_df = pd.DataFrame(att_list)
            att_df = att_df.drop(columns=['att_id', 'created_at', 'staff_id', 'rate_id'])
            st.subheader('Days worked'.upper())
            st.dataframe(
                att_df,
                hide_index=True,
                column_config={
                    'att_date': st.column_config.TextColumn('Date Attendet'),
                    'hours_worked': st.column_config.NumberColumn('Total Hours'),
                    'status': st.column_config.TextColumn('Status')
                },
                width='content'
            )
        else:
            st.write('There is no days worked.')

    def get_tot_days(self):
        return len(self.get_days())



