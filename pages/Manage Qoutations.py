import streamlit as st
from models.Model import init_data, inject_css
from models.Qout_Manag_Model import *
import webbrowser
from models.User_Model import *

# Single CSS injection via the shared helper – no inline block needed.
inject_css()

abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(page_title="Absaluminum".upper(), page_icon=abs_icon)

with st.sidebar:
    st.header("Qoutation Navigation")
    page = st.selectbox(
        "Go to",
        ["All Qoutations", "Edit Qoutations", "Waiting Qoutations", "Approved Qoutations", "Overdue Qoutations"]
    )


def qouteTable_1(df):
    cols = st.columns([1, 2, 1, 1, 1, 1, 1, 1])
    headers = [
        "Invoice", "Client", "Paid", "Total",
        "Outstanding", "Status", "Quote Doc", "PDF"
    ]

    for col, header in zip(cols, headers):
        col.markdown(f"**{header}**")

    for _, row in df.iterrows():
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1, 2, 1, 1, 1, 1, 1, 1])

        c1.write(row["inv_numb"])
        c2.write(row["inv_to"])
        c3.write(row["payed_amount"])
        c4.write(row["total_amount"])
        c5.write(row["oust_amount"])
        c6.write(row["status"])

        # Use inv_numb as the unique key – qoute_id does not exist in this dataset.
        if c7.button("Open Doc", key=f"doc_{row['inv_numb']}"):
            webbrowser.open(row["qoute_doc"])

        if c8.button("Open PDF", key=f"pdf_{row['inv_numb']}"):
            webbrowser.open(row["qoute_pdf"])

def qouteTable(df):
    df = df.drop(columns=["qoute_doc"])
    df["payed_amount"] = df["payed_amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
    df["total_amount"] = df["total_amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
    df["oust_amount"] = df["oust_amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
    st.dataframe(
        df,
        hide_index=True,
        column_config={
            "inv_numb": st.column_config.TextColumn("Inv Number"),
            "inv_to": st.column_config.TextColumn("Inv To"),
            "payed_amount": st.column_config.TextColumn("Paid Amount (R)"),
            "total_amount": st.column_config.TextColumn("Total Amount (R)"),
            "oust_amount": st.column_config.TextColumn("Outstanding (R)"),
            "status": st.column_config.TextColumn("Status"),
            "qoute_pdf": st.column_config.LinkColumn(
                "Quotation",
                display_text="View Qoutation"
            ),
        }
    )

def edit_qoutation():
    edit_qout = Qoute_Manager()
    edit_qout.set_qout_UI()


def qoutation_list():
    if st.session_state.qouteSummary:
        st.header("List of Qoutation")
        df = pd.DataFrame(st.session_state.qouteSummary)
        qouteTable(df=df)
    else:
        st.header("There is no qoutations")

#============================================================
user = User()
if user.get_user():
    st.title("Qoutations")

    if "loaded" not in st.session_state:
        init_data()
        st.session_state.loaded = True

    if not st.session_state.get("edit_qoute", False):
        qoutation_list()

        if st.button("**More Options...**"):
            st.session_state.edit_qoute = True
            st.session_state.qout_page = 0
            st.rerun()

    else:
        edit_qoutation()


