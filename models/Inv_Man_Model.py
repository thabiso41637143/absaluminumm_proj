from models.Model import *
from models.Qout_Manag_Model import *
import webbrowser


class InvManager:
    def __init__(self):
        if "loaded" not in st.session_state:
            self.update_database()

        if "view_next_inv" not in st.session_state and "view_prev_inv" not in st.session_state:
            st.session_state.view_next_inv = st.session_state.invoice_summary
            st.session_state.view_prev_inv = []

        if "inv_page" not in st.session_state:
            st.session_state.inv_page = 0

        if "inv_page_size" not in st.session_state:
            st.session_state.inv_page_size = 6
        
        self.reset_pages()

    def reset_pages(self):
        if "view_next_job" in st.session_state:
            st.session_state.pop("view_next_job")
        if "view_prev_job" in st.session_state:
            st.session_state.pop("view_prev_job")

        if "view_next_qoute" in st.session_state:
            st.session_state.pop("view_next_qoute")
        if "view_prev_qout" in st.session_state:
            st.session_state.pop("view_prev_qout")

    def set_inv_UI(self):
        if st.session_state.get('update_invoice'):
            if st.session_state.get('email'):
                self.email_inv()
            else:
                self.fin_inv_conv()
        else:
            data = [inv for inv in st.session_state.invoice_summary]# if not (q.get('status') == 'Invoiced')]
            page = st.session_state.inv_page
            size = st.session_state.inv_page_size

            start = page * size
            end = start + size
            page_data = data[start:end]

            for r in range(0, len(page_data), 3):
                cols = st.columns(3, border=True)
                for c, inv in zip(cols, page_data[r:r+3]):
                    with c:
                        self.set_inv_tile(inv)

            self.set_bottom_buttons()

    def close_inv(self):
        st.session_state.edit_inv = False
        st.session_state.inv_page = 0

    def update_inv_payment(self, inv):
        pass

    def update_database(self):
        init_data()
        st.session_state.loaded = True

    def inv_to_qout(self, inv):
        respond = supabase.table("QouteSummary").update({"status": "Waiting"})\
            .eq("inv_numb", inv.get("inv_numb")).execute()
        respond = supabase.table("InvoiceSummary").delete()\
            .eq("inv_numb", inv.get("inv_numb")).execute()
        
        if respond.data:
            self.update_database()
            st.session_state.view_next_inv = st.session_state.invoice_summary
            st.session_state.view_prev_inv = []
            st.session_state.inv_page = 0
            st.session_state.inv_page_size = 6
            self.close_inv()
            st.rerun()

    def email_inv(self):
        inv = Qoute_Manager()
        inv.send_email()

    def edit_inv(self, inv):
        pass

    def finalise_inv(self, inv):
        pass

    def clone_inv(self, inv):
        pass

    def delete_inv(self, inv):
        """Delete an invoice and all related records after user confirmation."""
        st.markdown(
            f"<hr style='border: 1px dotted red;'>"
            f"<p style='color:red; font-weight:bold;'>"
            f"Are you sure you want to permanently delete invoice {inv.get('inv_numb')} "
            f"for {inv.get('inv_to')}?</p>",
            unsafe_allow_html=True,
        )
        if st.button("Yes, delete", key="del_inv_" + str(inv.get("inv_numb"))):
            supabase.table("InvoiceDetails").delete().eq("inv_numb", inv.get("inv_numb")).execute()
            supabase.table("InvoiceSummary").delete().eq("inv_numb", inv.get("inv_numb")).execute()
            self.update_database()
            self.close_inv()
            st.rerun()

    def fin_inv_conv(self):
        """Delegate to the shared quotation-to-invoice conversion UI in Qoute_Manager."""
        qm = Qoute_Manager()
        qm.fin_inv_conv()

    def mark_as_incomplete(self, inv):
        respond = supabase.table("InvoiceSummary").update({"inv_status": "inprogress"})\
            .eq("inv_numb", inv.get("inv_numb")).execute()
        if respond.data:
            self.update_database()
            self.close_inv()
            st.rerun()

    def next_list(self):
        total_pages = (len(st.session_state.invoice_summary) - 1) // st.session_state.inv_page_size
        if st.session_state.inv_page < total_pages:
            st.session_state.inv_page += 1

    def prev_list(self):
        if st.session_state.inv_page > 0:
            st.session_state.inv_page -= 1

    def set_inv_tile(self, inv):
        st.write(f"**Invoice Number:** {inv.get('inv_numb')}")
        st.write(f"**Invoice To:** {inv.get('inv_to')}")
        st.write(f"**Status:** {inv.get('inv_status')}")
        st.write(f"**Oustanding Amount:** R {inv.get('out_amount'):.2f}")

        col1, col2 = st.columns(2, border=False)
        with col1:
            if st.button("PDF", key=f"pdf_{inv['inv_numb']}"):
                webbrowser.open(inv["inv_pdf"])

        with col2:
            if st.button(label='Doc', key='doc_'+str(inv.get("inv_numb"))):
                webbrowser.open(inv["inv_doc"])

        st.markdown(
"""
<hr style="border: 1px dotted red;">
"""
        , unsafe_allow_html=True )
        # Each label here must match exactly what appears in the options list.
        option = st.radio(label="**Select Option**", options=[
                              "Finalise Invoice",
                              "Edit Invoice",
                              "Convert to Quotation",   # was "Delete/Convert to Qoutation" – ambiguous
                              "Delete Invoice",          # was missing from the options list entirely
                              "Email Invoice",
                              "Mark as Incomplete",      # was "Mark as incomplte" (typo)
                              "Clone Invoice",
                          ],
                          key='radio_'+ str(inv.get("inv_numb")), index=None)
        if option == "Finalise Invoice":
            self.finalise_inv(inv=inv)
        elif option == "Edit Invoice":
            self.edit_inv(inv=inv)
        elif option == "Convert to Quotation":
            self.inv_to_qout(inv=inv)
        elif option == "Delete Invoice":
            self.delete_inv(inv=inv)
        elif option == "Email Invoice":
            st.session_state.selected_qoutation = {'invoice': inv}
            st.session_state.email = True
            st.session_state.update_invoice = True
            st.rerun()
        elif option == "Mark as Incomplete":
            self.mark_as_incomplete(inv=inv)
        elif option == "Clone Invoice":
            self.clone_inv(inv=inv)

    def set_bottom_buttons(self):
        close, prev_button, next_button = st.columns(3)

        with close:
            st.button("Close", on_click=self.close_inv)

        with prev_button:
            st.button("<< Prev", on_click=self.prev_list, disabled=st.session_state.inv_page == 0, type="primary")

        with next_button:
            last_page = (len(st.session_state.invoice_summary)-1) // st.session_state.inv_page_size
            st.button("Next >>", on_click=self.next_list, disabled=st.session_state.inv_page >= last_page, type="primary")
    
    def show_inv_tables(self):
        inv_df = pd.DataFrame(st.session_state.invoice_summary)

        inv_df = inv_df.drop(columns=["inv_id", "inv_doc"])
        inv_df["total_amount"] = inv_df["total_amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
        inv_df["paid_amount"] = inv_df["paid_amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
        inv_df["out_amount"] = inv_df["out_amount"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
        inv_df["inv_date"] = pd.to_datetime(inv_df["inv_date"], errors="coerce").dt.strftime("%d %b %Y")

        st.dataframe(inv_df, hide_index=True,
                column_config={
                    "inv_numb": st.column_config.TextColumn("Inv Number"),
                    "inv_to": st.column_config.TextColumn("Invoiced To"),
                    "total_amount": st.column_config.TextColumn("Total Amount (R)"),
                    "paid_amount": st.column_config.TextColumn("Paid Amount (R)"),
                    "out_amount": st.column_config.TextColumn("Outstanding (R)"),
                    "inv_date": st.column_config.TextColumn("Invoice Date"),
                    "inv_status": st.column_config.TextColumn("Status"),
                    "inv_name": st.column_config.TextColumn("Invoice Name"),
                    "inv_pdf": st.column_config.LinkColumn(
                            "Invoice", display_text="View Invoice"
                        ),
                    }
                )

    def list_inv(self):
        if st.session_state.invoice_summary:
            st.title("List of Invoices".upper())
            self.show_inv_tables()
        else:
            st.write("There is no Invoice")