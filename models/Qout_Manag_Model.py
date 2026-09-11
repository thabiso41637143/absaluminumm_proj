from Model import *
import webbrowser
from urllib.parse import urlencode

# CSS is now centralised in Model.inject_css() – no inline block needed here.

class Qoute_Manager:
    def __init__(self):
        if "loaded" not in st.session_state:
            init_data()
            st.session_state.loaded = True

        if "view_next_qoute" not in st.session_state and "view_prev_qout" not in st.session_state:
            st.session_state.view_next_qoute = st.session_state.qouteSummary
            st.session_state.view_prev_qout = []

        if "qout_page" not in st.session_state:
            st.session_state.qout_page = 0

        if "qout_page_size" not in st.session_state:
            st.session_state.qout_page_size = 6
   
        self.reset_pages()

    def reset_pages(self):
        if "view_next_job" in st.session_state:
            st.session_state.pop("view_next_job")
        if "view_prev_job" in st.session_state:
            st.session_state.pop("view_prev_job")

        if "view_next_inv" in st.session_state:
            st.session_state.pop("view_next_inv")
        if "view_prev_inv" in st.session_state:
            st.session_state.pop("view_prev_inv")

    def edit_qoutation(self, qout):
        st.markdown(f"""
                    <hr style="border: 1px dotted red;">
                    <p style='color:black; font-weight:bold;'>
                        You are about to edit the qoutation of {qout.get("inv_to")}.
                    </p>
                """, unsafe_allow_html=True
            )
        qout_details = self.get_qout_details(inv_numb=qout.get('inv_numb'))
        st.session_state.edit_qout_inv = {
                                        #customer Details
                                        "Invto":qout.get('inv_to'),
                                        "cust_tax":qout_details.get('cust_tax'), 
                                        "email":qout_details.get('cust_email'),
                                        "contnumb":qout_details.get('cust_numb'),
                                        "adr":qout_details.get('cust_address'),

                                        #Invoice Details
                                        "custtype":qout_details.get('cust_group'),
                                        "Invnumb":qout_details.get('inv_numb'),
                                        "date":qout_details.get('inv_date'),
                                        "duedate":qout_details.get('inv_duedate'),

                                        }
        st.session_state.material_df = pd.DataFrame(self.get_qout_items(inv_numb=qout.get('inv_numb')))
        st.session_state.material_df.rename(columns={
            "total_price": "Total amount",
            "unit_price": "Unit price",
            'item_description': 'Description',
            'quantity':'Qantity'
            }, inplace=True)
        st.session_state.material_df.drop(columns=['inv_numb', 'item_id'], inplace=True)
        st.write(st.session_state.edit_qout_inv)
        st.session_state.update_qoutation = True
        st.session_state.edit_qoutation = True
        st.rerun()

    def set_qoutation(self):
        qout_ui = InvQouteUI(invQouteUrl="https://script.google.com/macros/s/AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCVKsLwqrAJWkjOUVhZd7k9qA/exec?option=supabaseDB&invNumb=")
        qout_ui.gen_ui(gen_message="**Generate Qoutation**")

    def clone_qoutation(self, qout):
        pass

    def approve_qoute(self, qout): 
        st.markdown(
                """
                <hr style="border: 2px dotted red;">
                """,
                unsafe_allow_html=True
            )     
        st.write("You are about to approve this qoutation.")
        st.markdown(f"""
                    <p style='color:red; text-decoration:underline; font-weight:bold;'>
                        To: {qout.get("inv_to")}
                    </p>
                """, unsafe_allow_html=True
            )
        
        total_qout = st.session_state.get('_inv_totals_idx', {}).get(qout.get("inv_numb"))

        st.write(f"**Deposit: R {total_qout.get('deposit'):.2f}**")
        payed_amount = st.number_input("Amount Payed",format="%0.2f", key="payed_amount_"+str(qout.get("inv_numb")), min_value=0.00)
        # oust_amount = total_qout.get("total_balance") - payed_amount
        if st.button("Continue...", key='continue_'+str(qout.get("inv_numb"))):
            response = (supabase.table("QouteSummary")
            .update({"status": "Inprogress", "payed_amount":payed_amount,
                     "oust_amount":total_qout.get("total_balance") - payed_amount}).eq("inv_numb", qout.get("inv_numb"))
            .execute())

            if response.data:
                st.success(f"Qoutation number {qout.get('inv_numb')} is now In Progress 🚧")
                init_data()
                st.session_state.loaded = True
            else:
                st.warning("Qoutation was not found ⚠️")

    def convert_inv(self, qout):
        st.markdown(f"""
                    <hr style="border: 1px dotted red;">
                    <p style='color:black; font-weight:bold;'>
                        You are about to convert the qoutation of {qout.get("inv_to")} to invoice.
                    </p>
                """, unsafe_allow_html=True
            )
        # if st.button("Continue...", key='continue_'+str(qout.get('inv_numb'))):
        st.session_state.selected_qoutation = {"invoice details":qout,
                                               'invoice summary':self.get_qout_summary(inv_numb=qout.get('inv_numb')),
                                               'invoice total':self.get_qout_totals(inv_numb=qout.get('inv_numb'))
                                               }
        
        items_list = st.session_state.get('_items_idx', {}).get(qout.get('inv_numb'), [])
        st.session_state.selected_qoutation['invoice items'] = items_list
        
        if st.session_state.selected_qoutation.get('invoice summary') and st.session_state.selected_qoutation.get('invoice items'):
            st.session_state.update_qoutation = True
            st.rerun()
        else:
            st.write("Failed to load the qoutation")

    def get_qout_summary(self, inv_numb):
        # O(1) lookup via index built in init_data()
        return st.session_state.get('_qout_summary_idx', {}).get(inv_numb)

    def get_qout_details(self, inv_numb):
        return st.session_state.get('_inv_details_idx', {}).get(inv_numb)

    def get_qout_totals(self, inv_numb):
        return st.session_state.get('_inv_totals_idx', {}).get(inv_numb)

    def get_qout_items(self, inv_numb):
        return st.session_state.get('_items_idx', {}).get(inv_numb, [])

    def fin_inv_conv(self):
        invoice_details = st.session_state.selected_qoutation['invoice details']
        invoice_items = st.session_state.selected_qoutation['invoice items']
        invoice_summary = st.session_state.selected_qoutation['invoice summary']
        invoice_totals = st.session_state.selected_qoutation['invoice total']
          
        qout_summary = st.container(border=True)
        with qout_summary:
            st.markdown(
                    f"""
                        <p style='color:red; text-decoration:underline; font-weight:bold;text-align:center;'>
                            INVOICE DETAILS
                        </p>
                    """, unsafe_allow_html=True
                )
            col1, col2 = st.columns(2, border=False)
            with col1:
                st.write(f"**Invoice Number:** {invoice_details.get('inv_numb')}")
                st.write(f"**Invoice Date:** {date.today().strftime('%d %b %Y')}")
            
            with col2:
                st.write(f"**Invoice To:** {invoice_details.get('inv_to')}")
                st.write(f"**Email Address:** {invoice_details.get('cust_email')}")
                st.write(f"**Contact Numbers:** {invoice_details.get('cust_numb')}")
                st.write(f"**Address:** {invoice_details.get('cust_address')}")
            
            st.markdown("""<hr style="border: 1px dotted red;">""", unsafe_allow_html=True)

            st.markdown(
                    f"""
                        <p style='color:red; text-decoration:underline; font-weight:bold;text-align:center;'>
                            INVOICE ITEMS
                        </p>
                    """, unsafe_allow_html=True
                )
            
            df = pd.DataFrame(invoice_items)
            df = df.drop(columns=["item_id", "inv_numb"])
            df["unit_price"] = df["unit_price"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
            df["total_price"] = df["total_price"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
            st.dataframe(df, hide_index=True,
                            column_config={
                                    "item_description": st.column_config.TextColumn("Item Description"),
                                    "unit_price": st.column_config.TextColumn("Unit Price (R)"),
                                    "quantity": st.column_config.TextColumn("Quantity"),
                                    "total_price": st.column_config.TextColumn("Total Amount (R)"),
                                }
                        )
            #Add tables

            st.markdown("""<hr style="border: 1px dotted red;">""", unsafe_allow_html=True)

            # st.write("**total summary**".upper())
            st.markdown(
                    f"""
                        <p style='color:red; text-decoration:underline; font-weight:bold;text-align:center;'>
                            TOTAL SUMMARY
                        </p>
                    """, unsafe_allow_html=True
                )

            tot1, tot2 = st.columns(2, border=False)
            with tot1:
                st.write(f"**Amount Deposited:** R {float(invoice_totals.get('deposit')):.2f}")
                st.write(f"**Installation Cost:** R {float(invoice_totals.get('installation_cost')):.2f}")
                st.write(f"**Discount:** R {float(invoice_totals.get('discount')):.2f}")

            with tot2:
                st.write(f"**Total Amount:** R {float(invoice_summary.get('total_amount')):.2f}")
                st.write(f"**Amount Paid:** R {float(invoice_summary.get('payed_amount')):.2f}")
                st.write(f"**Oustanding Amount:** R {float(invoice_summary.get('oust_amount')):.2f}")

            st.markdown("""<hr style="border: 1px dotted red;">""", unsafe_allow_html=True)

            st.markdown(
                    f"""
                        <p style='color:red; text-decoration:underline; font-weight:bold;'>
                            Balance Due: R {float(invoice_summary.get('total_amount')):.2f}
                        </p>
                    """, unsafe_allow_html=True
                )

            left, spacer, right = st.columns([1, 2, 1])
            with left:

                if st.button('**Generate Invoice**', key='generate_'+str(st.session_state.selected_qoutation.get("inv_numb"))
                             , use_container_width=True, type="primary"):
                    gen_inv_url = "https://script.google.com/macros/s/AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCVKsLwqrAJWkjOUVhZd7k9qA/exec?option=supabaseDB&menue=createInvoice&invNumb="+ str(invoice_details.get("inv_numb"))
                    print(gen_inv_url)
                    with st.spinner("⏳ Generating a new invoice... Please wait."):
                        resultsSet = requests.get(gen_inv_url)
                        results = json.loads(resultsSet.text)

                        print("\n=================\n")
                        print(results)
                    init_data()
                    st.session_state.update_qoutation = False
                    st.session_state.current_job_qout = False
                    st.session_state.loaded = True
                    st.rerun()

            with right:
                if st.button("**Cancel Invoice**", use_container_width=True, type="secondary"):
                    st.session_state.update_qoutation = False
                    st.session_state.current_job_qout = False
                    st.rerun()

    def delete_qoutation(self, qout):
        st.markdown(f"""
                    <hr style="border: 1px dotted red;">
                    <p style='color:red;  font-weight:bold;'>
                        Are you sure you want to delete these qoutations of {qout.get("inv_to")}?
                    </p>
                """, unsafe_allow_html=True
            )

        if st.button("Yes", key='yes_'+str(qout.get("inv_numb"))):
            response = (supabase.table("InvoiceDetails").delete().eq("inv_numb", qout.get("inv_numb")).execute())
            url_delete = "https://script.google.com/macros/s/AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCV"\
                "KsLwqrAJWkjOUVhZd7k9qA/exec?option=supabaseDB&menue=deleteQoutation&invNumb=" + str(qout.get("inv_numb"))
            resultsSet = requests.get(url_delete)

            if response.data:
                st.success(f"Qoutation {qout.get('inv_numb')} is permanently deleted 🗑️")
                init_data()
                st.session_state.loaded = True
            else:
                st.warning("Qoutation not found")


    def next_list(self):
        total_pages = (len(st.session_state.qouteSummary) - 1) // st.session_state.qout_page_size
        if st.session_state.qout_page < total_pages:
            st.session_state.qout_page += 1

    def prev_list(self):
        if st.session_state.qout_page > 0:
            st.session_state.qout_page -= 1

    def close_qoutation(self):
        st.session_state.edit_qoute = False
        st.session_state.qout_page = 0
        st.session_state.selected_qoute = None

    def set_qout_UI(self):
        if st.session_state.get('update_qoutation'):
            if st.session_state.get('email'):
                self.send_email()
            elif st.session_state.get('edit_qoutation'):
                self.set_qoutation()
            else:
                self.fin_inv_conv()
        else:
            data = [q for q in st.session_state.qouteSummary if not (q.get('status') == 'Invoiced')]
            page = st.session_state.qout_page
            size = st.session_state.qout_page_size

            start = page * size
            end = start + size
            page_data = data[start:end]

            for r in range(0, len(page_data), 3):
                cols = st.columns(3, border=True)
                for c, qout in zip(cols, page_data[r:r+3]):
                    with c:
                        self.set_tiles(qout)

            self.set_bottom_buttons()

    def send_email(self):
        email_address = ""

        selected = st.session_state.get('selected_qoutation', {})

        # Guard: determine document type and extract the relevant record.
        # Previously, if neither key was present all variables below were
        # unbound, causing an UnboundLocalError at runtime.
        if 'qoutation' in selected:
            qout = selected['qoutation']
            email_type = 'emailQoutation'
            subject_line = "Quotation Number: " + str(qout.get('inv_numb'))
            cont_message = (
                "Dear Sir/Madam,\n\n"
                "Please find the attached quotation for your review.\n\n"
                "Should you require any further information or clarification, "
                "please do not hesitate to contact us.\n\n"
                "Kind regards,\nABSALUMINUM (PTY) LTD\n"
            )
        elif 'invoice' in selected:
            qout = selected['invoice']
            email_type = 'emailInvoice'
            subject_line = "Invoice Number: " + str(qout.get('inv_numb'))
            cont_message = (
                "Dear Sir/Madam,\n\n"
                "Please find the attached invoice for your reference.\n\n"
                "Should you require any further information or clarification, "
                "please do not hesitate to contact us.\n\n"
                "Kind regards,\nABSALUMINUM (PTY) LTD\n"
            )
        else:
            st.error("No quotation or invoice selected for emailing.")
            return

        for inv_details in st.session_state.invoice_details:
            if inv_details.get("inv_numb") == qout.get('inv_numb'):
                email_address = inv_details.get("cust_email", "")
                break

        cont = st.container(border=True)
        with cont:
            email = st.text_input(label="E-mail address", key="emails_"+str(qout.get('inv_numb')), value=email_address)
            subj = st.text_input(label="Subject", key="subject_"+str(qout.get('inv_numb')), value=subject_line)
            contents = st.text_area(label='Message', key='contents_'+str(qout.get('inv_numb')), value=cont_message, height="content")

            left, spacer, right = st.columns([1, 3, 1])
            with left:
                if st.button(label="Send", key="send_"+str(qout.get('inv_numb'))):
                    supabase.table("InvoiceDetails").update({"cust_email": email}).eq("inv_numb", qout.get("inv_numb")).execute()

                    # Use urlencode so that special characters in subject/body
                    # cannot break the URL or inject extra query parameters.
                    base_url = (
                        "https://script.google.com/macros/s/"
                        "AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCV"
                        "KsLwqrAJWkjOUVhZd7k9qA/exec"
                    )
                    params = {
                        "option": "supabaseDB",
                        "menue": email_type,
                        "subject": subj,
                        "contents": contents,
                        "invNumb": str(qout.get('inv_numb')),
                    }
                    url_send = base_url + "?" + urlencode(params)

                    with st.spinner("⏳ Sending the email... Please wait."):
                        requests.get(url_send)

                    st.session_state.update_qoutation = False
                    st.session_state.email = False
                    st.session_state.update_invoice = False
                    st.rerun()
            with right:
                if st.button(label="Cancel", key="cancel_"+str(qout.get('inv_numb'))):
                    st.session_state.update_qoutation = False
                    st.session_state.email = False
                    st.session_state.update_invoice = False
                    st.rerun()

    def set_tiles(self, qout):
        st.write(f"**Invoice Number:** {qout.get('inv_numb')}")
        st.write(f"**Invoice To:** {qout.get('inv_to')}")
        st.write(f"**Status:** {qout.get('status')}")
        st.write(f"**Total Amount:** R {qout.get('total_amount'):.2f}")

        col1, col2 = st.columns(2, border=False)
        with col1:
            if st.button("PDF", key=f"pdf_{qout['inv_numb']}"):
                webbrowser.open(qout["qoute_pdf"])

        with col2:
            if st.button(label='Doc', key='doc_'+str(qout.get("inv_numb"))):
                webbrowser.open(qout["qoute_doc"])

        
        st.markdown(
    """
    <hr style="border: 1px dotted red;">
    """, unsafe_allow_html=True )

        option = st.radio(label="**Select Option**",options=["Approve Qoutaion", "Generate Invoice",
                                                              "Edit Qoutation", "Email Qoutation",
                                                                "Delete Qoutation", "Clone Qoutation"],
                        key='radio_'+ str(qout.get("inv_numb")), index=None)
        if option == "Approve Qoutaion":
            self.approve_qoute(qout=qout)
        elif option == "Generate Invoice":
            self.convert_inv(qout=qout)
        elif option == "Edit Qoutation":
            self.edit_qoutation(qout=qout)
        elif option == "Delete Qoutation":
            self.delete_qoutation(qout=qout)
        elif option == "Email Qoutation":
            self.send_qoutation(qout=qout)
        elif option == "Clone Qoutation":
            self.clone_qoutation(qout=qout)

    def send_qoutation(self, qout):
        st.session_state.selected_qoutation = {"qoutation": qout}
        st.session_state.update_qoutation = True
        st.session_state.email = True
        st.rerun()

    def set_bottom_buttons(self):
        close, prev_button, next_button = st.columns(3)

        with close:
            st.button("Close", on_click=self.close_qoutation)

        with prev_button:
            st.button("<< Prev", on_click=self.prev_list, disabled=st.session_state.qout_page == 0, type="primary")

        with next_button:
            last_page = (len(st.session_state.qouteSummary)-1) // st.session_state.qout_page_size
            st.button("Next >>", on_click=self.next_list, disabled=st.session_state.qout_page >= last_page, type="primary")

