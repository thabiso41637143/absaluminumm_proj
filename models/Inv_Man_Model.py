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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reset_pages(self):
        for key in ("view_next_job", "view_prev_job", "view_next_qoute", "view_prev_qout"):
            st.session_state.pop(key, None)

    def update_database(self):
        init_data()
        st.session_state.loaded = True

    def close_inv(self):
        st.session_state.edit_inv = False
        st.session_state.inv_page = 0

    def next_list(self):
        data = self._filtered_data()
        total_pages = max(0, len(data) - 1) // st.session_state.inv_page_size
        if st.session_state.inv_page < total_pages:
            st.session_state.inv_page += 1

    def prev_list(self):
        if st.session_state.inv_page > 0:
            st.session_state.inv_page -= 1

    def _filtered_data(self):
        status_filter = st.session_state.get("inv_status_filter", "All")
        all_data = list(st.session_state.invoice_summary)
        if status_filter == "In Progress":
            return [i for i in all_data if str(i.get('inv_status', '')).lower() == 'inprogress']
        elif status_filter == "Complete":
            return [i for i in all_data if str(i.get('inv_status', '')).lower() == 'complete']
        elif status_filter == "Outstanding":
            return [i for i in all_data if float(i.get('out_amount', 0) or 0) > 0]
        return all_data

    # ------------------------------------------------------------------
    # Main UI
    # ------------------------------------------------------------------

    def set_inv_UI(self):
        if st.session_state.get('update_invoice'):
            if st.session_state.get('email'):
                self.email_inv()
            elif st.session_state.get('editing_invoice'):
                self._edit_inv_ui()
            else:
                self.fin_inv_conv()
            return

        # ── Header row ───────────────────────────────────────────────────
        hdr_col, refresh_col = st.columns([5, 1])
        with hdr_col:
            st.title("🧾 Manage Invoices")
        with refresh_col:
            st.write("")
            if st.button("🔄 Refresh", use_container_width=True):
                self.update_database()
                st.session_state.inv_page = 0
                st.rerun()

        # ── Stats bar ────────────────────────────────────────────────────
        self._render_stats()

        # ── Status filter ────────────────────────────────────────────────
        filter_options = ["All", "In Progress", "Complete", "Outstanding"]
        current_filter = st.session_state.get("inv_status_filter", "All")
        cols = st.columns(len(filter_options))
        for i, opt in enumerate(filter_options):
            with cols[i]:
                btn_type = "primary" if current_filter == opt else "secondary"
                if st.button(opt, key=f"inv_filter_{opt}", type=btn_type, use_container_width=True):
                    st.session_state.inv_status_filter = opt
                    st.session_state.inv_page = 0
                    st.rerun()

        st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0 1rem 0;'>", unsafe_allow_html=True)

        data = self._filtered_data()
        if not data:
            st.info("No invoices found for the selected filter.")
            self._render_close_button()
            return

        page      = st.session_state.inv_page
        size      = st.session_state.inv_page_size
        total     = len(data)
        last_page = max(0, (total - 1) // size)
        start     = page * size
        end       = min(start + size, total)
        page_data = data[start:end]

        for r in range(0, len(page_data), 3):
            cols = st.columns(3, gap="medium")
            for col, inv in zip(cols, page_data[r:r + 3]):
                with col:
                    with st.container(border=True):
                        self.set_inv_tile(inv)

        self._render_pagination(page, last_page, total, start, end)

    def _render_stats(self):
        all_inv    = st.session_state.invoice_summary
        inprogress = sum(1 for i in all_inv if str(i.get('inv_status', '')).lower() == 'inprogress')
        complete   = sum(1 for i in all_inv if str(i.get('inv_status', '')).lower() == 'complete')
        outstanding_total = sum(float(i.get('out_amount', 0) or 0) for i in all_inv)
        total      = len(all_inv)

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Total Invoices", total)
        with c2: st.metric("🚧 In Progress", inprogress)
        with c3: st.metric("✅ Complete", complete)
        with c4: st.metric("💰 Outstanding", f"R {outstanding_total:,.2f}")
        st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0;'>", unsafe_allow_html=True)

    def _render_pagination(self, page, last_page, total, start, end):
        st.markdown("<hr style='border:1px solid #d1d5db; margin:1rem 0 0.5rem 0;'>", unsafe_allow_html=True)
        close_col, prev_col, info_col, next_col = st.columns([1, 1, 2, 1])
        with close_col:
            st.button("✖ Close", on_click=self.close_inv, use_container_width=True, key="inv_close_btn")
        with prev_col:
            st.button("◀ Prev", on_click=self.prev_list,
                      disabled=(page == 0), type="primary", use_container_width=True, key="inv_prev")
        with info_col:
            st.markdown(
                f"<p style='text-align:center; margin-top:0.5rem; color:#6b7280; font-size:0.9rem;'>"
                f"Page <b>{page + 1}</b> of <b>{last_page + 1}</b> &nbsp;·&nbsp; "
                f"Showing <b>{start + 1}–{end}</b> of <b>{total}</b></p>",
                unsafe_allow_html=True,
            )
        with next_col:
            st.button("Next ▶", on_click=self.next_list,
                      disabled=(page >= last_page), type="primary", use_container_width=True, key="inv_next")

    def _render_close_button(self):
        if st.button("✖ Close", key="inv_close_empty"):
            self.close_inv()
            st.rerun()

    # ------------------------------------------------------------------
    # Tile
    # ------------------------------------------------------------------

    def set_inv_tile(self, inv):
        status      = str(inv.get('inv_status', '')).lower()
        inv_numb    = inv.get('inv_numb')
        out_amount  = float(inv.get('out_amount', 0) or 0)
        total_amount = float(inv.get('total_amount', 0) or 0)
        paid_amount  = float(inv.get('paid_amount', 0) or 0)

        # ── Status badge ─────────────────────────────────────────────────
        if status == 'complete':
            badge_colour, badge_label = "#16a34a", "✅ COMPLETE"
        elif status == 'inprogress':
            badge_colour, badge_label = "#d97706", "🚧 IN PROGRESS"
        else:
            badge_colour, badge_label = "#6b7280", f"⚪ {status.upper()}"

        st.markdown(
            f"<span style='background:{badge_colour}; color:white; padding:2px 10px; "
            f"border-radius:12px; font-size:0.78rem; font-weight:600;'>{badge_label}</span>",
            unsafe_allow_html=True,
        )

        # ── Client & amount ───────────────────────────────────────────────
        st.markdown(f"### {inv.get('inv_to', '—')}")
        st.markdown(f"**Invoice #:** `{inv_numb}`")

        # Outstanding amount chip
        if out_amount <= 0:
            chip_style = "background:#dcfce7; color:#166534; border:1px solid #86efac;"
            chip_text  = "💚 Fully Paid"
        else:
            chip_style = "background:#fee2e2; color:#b91c1c; border:1px solid #fca5a5;"
            chip_text  = f"⚠️ Outstanding: R {out_amount:,.2f}"

        st.markdown(
            f"<div style='{chip_style} padding:4px 12px; border-radius:20px; "
            f"font-size:0.82rem; display:inline-block; margin:4px 0 8px 0;'>"
            f"{chip_text}</div>",
            unsafe_allow_html=True,
        )

        st.markdown(f"**Total:** R {total_amount:,.2f} &nbsp;|&nbsp; **Paid:** R {paid_amount:,.2f}")

        # ── PDF / Doc buttons ────────────────────────────────────────────
        pdf_col, doc_col = st.columns(2)
        with pdf_col:
            if st.button("📄 PDF", key=f"pdf_{inv_numb}", use_container_width=True):
                webbrowser.open(inv.get("inv_pdf", ""))
        with doc_col:
            if st.button("📝 Doc", key=f"doc_{inv_numb}", use_container_width=True):
                webbrowser.open(inv.get("inv_doc", ""))

        st.markdown("<hr style='border:1px dotted #d1d5db; margin:6px 0;'>", unsafe_allow_html=True)

        # ── Action buttons ───────────────────────────────────────────────
        action_key     = f"inv_action_{inv_numb}"
        current_action = st.session_state.get(action_key)

        if current_action is None:
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("✏️ Edit", key=f"edit_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "edit"
                    st.rerun()
            with b2:
                if st.button("✉️ Email", key=f"email_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "email"
                    st.rerun()
            with b3:
                if st.button("📋 Clone", key=f"clone_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "clone"
                    st.rerun()

            b4, b5, b6, b7 = st.columns(4)
            with b4:
                if st.button("💳 Payment", key=f"payment_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "payment"
                    st.rerun()
            with b5:
                if st.button("🔁 To Quote", key=f"toquote_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "toquote"
                    st.rerun()
            with b6:
                if st.button("⏪ Incomplete", key=f"incomplete_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "incomplete"
                    st.rerun()
            with b7:
                if st.button("🗑️ Delete", key=f"delete_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "delete"
                    st.rerun()
        elif current_action == "edit":
            st.session_state.pop(action_key, None)
            self.edit_inv(inv=inv)

        elif current_action == "email":
            st.session_state.pop(action_key, None)
            st.session_state.selected_qoutation = {'invoice': inv}
            st.session_state.email = True
            st.session_state.update_invoice = True
            st.rerun()

        elif current_action == "clone":
            st.session_state.pop(action_key, None)
            self.clone_inv(inv=inv)

        elif current_action == "payment":
            self.update_inv_payment(inv=inv, action_key=action_key)

        elif current_action == "toquote":
            st.warning(f"Convert invoice **#{inv_numb}** back to a Quotation? This will remove the invoice record.")
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button("✔ Yes, convert", key=f"yes_toquote_{inv_numb}", type="primary", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    self.inv_to_qout(inv=inv)
            with no_col:
                if st.button("✖ Cancel", key=f"no_toquote_{inv_numb}", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    st.rerun()

        elif current_action == "incomplete":
            st.warning(f"Mark invoice **#{inv_numb}** as Incomplete (back to In Progress)?")
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button("✔ Yes", key=f"yes_incomplete_{inv_numb}", type="primary", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    self.mark_as_incomplete(inv=inv)
            with no_col:
                if st.button("✖ Cancel", key=f"no_incomplete_{inv_numb}", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    st.rerun()

        elif current_action == "delete":
            st.error(f"Permanently delete invoice **#{inv_numb}** for **{inv.get('inv_to')}**? This cannot be undone.")
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button("🗑️ Yes, delete", key=f"yes_del_{inv_numb}", type="primary", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    self.delete_inv(inv=inv)
            with no_col:
                if st.button("✖ Cancel", key=f"no_del_{inv_numb}", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    st.rerun()

    def _back_button(self, action_key, inv_numb, suffix):
        if st.button("← Back", key=f"back_{suffix}_{inv_numb}"):
            st.session_state.pop(action_key, None)
            st.rerun()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def inv_to_qout(self, inv):
        supabase.table("QouteSummary").update({"status": "Waiting"}).eq("inv_numb", inv.get("inv_numb")).execute()
        supabase.table("InvoiceSummary").delete().eq("inv_numb", inv.get("inv_numb")).execute()
        self.update_database()
        st.session_state.view_next_inv = st.session_state.invoice_summary
        st.session_state.view_prev_inv = []
        st.session_state.inv_page = 0
        self.close_inv()
        st.rerun()

    def email_inv(self):
        inv = Qoute_Manager()
        inv.send_email()

    def edit_inv(self, inv):
        """Load invoice into edit mode via InvQouteUI."""
        inv_numb = inv.get("inv_numb")
        details  = st.session_state.get("_inv_details_idx", {}).get(inv_numb, {})
        items    = st.session_state.get("_items_idx", {}).get(inv_numb, [])
        totals   = st.session_state.get("_inv_totals_idx", {}).get(inv_numb, {})

        # Pre-populate session state so InvQouteUI's edit path picks it up
        st.session_state.edit_qout_inv = {
            "Invto":    details.get("inv_to"),
            "cust_tax": details.get("cust_tax"),
            "email":    details.get("cust_email"),
            "contnumb": details.get("cust_numb"),
            "adr":      details.get("cust_address"),
            "custtype": details.get("cust_group"),
            "Invnumb":  details.get("inv_numb"),
            "date":     details.get("inv_date"),
            "duedate":  details.get("inv_duedate"),
        }

        # Load existing items into the confirmed items DataFrame
        df = pd.DataFrame(items)
        if not df.empty:
            df.rename(columns={
                "total_price":      "Total amount",
                "unit_price":       "Unit price",
                "item_description": "Description",
                "quantity":         "Quantity",
            }, inplace=True)
            df.drop(columns=[c for c in ["inv_numb", "item_id"] if c in df.columns], inplace=True)
        else:
            df = pd.DataFrame(columns=["Description", "Unit price", "Quantity", "Total amount"])
        st.session_state.material_df      = df
        st.session_state.edit_material_df = pd.DataFrame(columns=["Description", "Unit price", "Quantity"])

        # Stash the original totals so save_edit_inv can write them back
        st.session_state._editing_inv_totals = totals
        st.session_state._editing_inv_numb   = inv_numb

        # Signal which flow to use
        st.session_state.update_invoice  = True
        st.session_state.editing_invoice = True
        st.rerun()

    def _edit_inv_ui(self):
        """Full-page edit UI for an existing invoice."""
        inv_numb = st.session_state.get("_editing_inv_numb")

        st.markdown(
            f"<p style='font-size:1.1rem; font-weight:700; color:#2563eb;'>"
            f"✏️ Editing Invoice #{inv_numb}</p>",
            unsafe_allow_html=True,
        )

        # Reuse InvQouteUI in edit mode (edit_qout_inv is already populated)
        inv_ui = InvQouteUI()
        inv_ui.gen_ui(gen_message="💾 Save Invoice")

        # Intercept the submit: instead of insert, do update
        # This is handled by overriding submit via the save button below
        if st.session_state.get("finalise_details"):
            if st.button("💾 Confirm Save", type="primary", key="confirm_save_inv"):
                self._save_edit_inv()

        cancel_col, _ = st.columns([1, 4])
        with cancel_col:
            if st.button("✖ Cancel Edit", key="cancel_edit_inv"):
                st.session_state.update_invoice  = False
                st.session_state.editing_invoice = False
                st.session_state.pop("_editing_inv_numb", None)
                st.session_state.pop("_editing_inv_totals", None)
                st.session_state.edit_qout_inv = {}
                st.rerun()

    def _save_edit_inv(self):
        """Persist edited invoice details/items/totals to Supabase."""
        inv_numb = st.session_state.get("_editing_inv_numb")
        items = []
        for _, row in st.session_state.material_df.iterrows():
            items.append({
                "inv_numb":         int(inv_numb),
                "item_description": row["Description"],
                "unit_price":       float(row["Unit price"]),
                "quantity":         int(row["Quantity"]),
                "total_price":      float(row["Total amount"]),
            })

        inv_details = {
            "inv_to":       st.session_state.get("Invto"),
            "inv_duedate":  st.session_state.get("duedate").isoformat() if st.session_state.get("duedate") else None,
            "cust_email":   st.session_state.get("email"),
            "cust_numb":    st.session_state.get("contnumb"),
            "cust_address": st.session_state.get("adr"),
            "cust_tax":     int(st.session_state.get("cust_tax") or 0),
        }

        new_total = float(st.session_state.get("tot_bal", 0))
        paid      = float(st.session_state.get("_editing_inv_totals", {}).get("paid_amount") or 0)
        total_upd = {
            "total_balance":    new_total,
            "total_inctax":     float(st.session_state.get("tax_input", 0)),
            "total_lessdisc":   float(st.session_state.get("less_disc", 0)),
            "sub_total":        float(st.session_state.get("sub_tot", 0)),
            "deposit":          float(st.session_state.get("dep_input", 0)),
            "installation_cost":float(st.session_state.get("inst_cost_input", 0)),
            "discount":         float(st.session_state.get("discount_input_value", 0)),
        }

        try:
            with st.spinner("💾 Saving changes..."):
                supabase.table("InvoiceDetails").update(inv_details).eq("inv_numb", inv_numb).execute()
                supabase.table("Items").delete().eq("inv_numb", inv_numb).execute()
                supabase.table("Items").insert(items).execute()
                supabase.table("Totals").update(total_upd).eq("inv_numb", inv_numb).execute()
                # Recalculate outstanding
                out_amount = new_total - paid
                supabase.table("InvoiceSummary").update({
                    "total_amount": new_total,
                    "out_amount":   out_amount,
                }).eq("inv_numb", inv_numb).execute()

            st.success(f"✅ Invoice #{inv_numb} updated successfully.")
            self.update_database()
            st.session_state.update_invoice  = False
            st.session_state.editing_invoice = False
            st.session_state.finalise_details = False
            st.session_state.pop("_editing_inv_numb", None)
            st.session_state.pop("_editing_inv_totals", None)
            st.session_state.edit_qout_inv = {}
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save invoice: {e}")
            print(f"[edit_inv] save error: {e}")

    def update_inv_payment(self, inv, action_key):
        """Inline payment capture form — records a new payment against the invoice."""
        inv_numb    = inv.get("inv_numb")
        total       = float(inv.get("total_amount", 0) or 0)
        paid_so_far = float(inv.get("paid_amount", 0) or 0)
        outstanding = float(inv.get("out_amount", 0) or 0)

        st.markdown(
            f"<p style='font-weight:700; color:#2563eb; margin-bottom:4px;'>"
            f"💳 Record Payment — Invoice #{inv_numb}</p>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Total", f"R {total:,.2f}")
            with m2: st.metric("Paid So Far", f"R {paid_so_far:,.2f}")
            with m3: st.metric("Outstanding", f"R {outstanding:,.2f}")

            new_payment = st.number_input(
                "New Payment Amount (R)",
                min_value=0.00,
                max_value=float(outstanding),
                format="%.2f",
                key=f"new_payment_{inv_numb}",
            )

            if new_payment > 0:
                new_paid        = paid_so_far + new_payment
                new_outstanding = max(total - new_paid, 0)
                st.markdown(
                    f"<p style='color:#6b7280; font-size:0.88rem;'>"
                    f"After this payment: Paid = <b>R {new_paid:,.2f}</b> "
                    f"· Outstanding = <b>R {new_outstanding:,.2f}</b></p>",
                    unsafe_allow_html=True,
                )

            save_col, cancel_col = st.columns(2)
            with save_col:
                if st.button("💾 Save Payment", key=f"save_pmt_{inv_numb}", type="primary", use_container_width=True):
                    if new_payment <= 0:
                        st.warning("Please enter a payment amount greater than R 0.")
                    else:
                        new_paid        = paid_so_far + new_payment
                        new_outstanding = max(total - new_paid, 0)
                        new_status      = "complete" if new_outstanding == 0 else "inprogress"
                        try:
                            with st.spinner("Saving payment..."):
                                supabase.table("InvoiceSummary").update({
                                    "paid_amount": new_paid,
                                    "out_amount":  new_outstanding,
                                    "inv_status":  new_status,
                                }).eq("inv_numb", inv_numb).execute()
                            st.success(f"✅ Payment of R {new_payment:,.2f} recorded.")
                            self.update_database()
                            st.session_state.pop(action_key, None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to save payment: {e}")
                            print(f"[update_inv_payment] error: {e}")
            with cancel_col:
                if st.button("✖ Cancel", key=f"cancel_pmt_{inv_numb}", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    st.rerun()

    def clone_inv(self, inv):
        """Duplicate an invoice to a new invoice number and insert as a fresh draft."""
        src_numb = inv.get("inv_numb")
        details  = st.session_state.get("_inv_details_idx", {}).get(src_numb, {})
        items    = st.session_state.get("_items_idx", {}).get(src_numb, [])
        totals   = st.session_state.get("_inv_totals_idx", {}).get(src_numb, {})

        try:
            with st.spinner("📋 Cloning invoice..."):
                # Get a fresh invoice number from the generator
                new_gen = supabase.table("invGenerator").insert({"status": "used"}).execute()
                if not new_gen.data:
                    st.error("Could not generate a new invoice number.")
                    return
                new_gen_id  = new_gen.data[0]["gen_id"]
                cust_group  = details.get("cust_group", "")
                # Build the new invoice number in the same format
                new_inv_numb = int(f"{st.session_state.customer_category[0].get('starting_number', 1)}"
                                   f"{date.today().year}{new_gen_id}") \
                    if st.session_state.customer_category else int(f"{date.today().year}{new_gen_id}")

                # Clone InvoiceDetails
                new_details = {k: v for k, v in details.items()
                               if k not in ("inv_numb",)}
                new_details["inv_numb"]   = new_inv_numb
                new_details["inv_date"]   = date.today().isoformat()
                new_details["inv_duedate"]= (date.today() + timedelta(days=30)).isoformat()
                supabase.table("InvoiceDetails").insert(new_details).execute()

                # Clone Items
                new_items = []
                for item in items:
                    new_item = {k: v for k, v in item.items()
                                if k not in ("item_id", "inv_numb")}
                    new_item["inv_numb"] = new_inv_numb
                    new_items.append(new_item)
                if new_items:
                    supabase.table("Items").insert(new_items).execute()

                # Clone Totals
                new_totals = {k: v for k, v in totals.items()
                              if k not in ("inv_numb",)}
                new_totals["inv_numb"] = new_inv_numb
                supabase.table("Totals").insert(new_totals).execute()

                # Create a fresh QouteSummary entry for the clone (status=Waiting)
                src_qout = st.session_state.get("_qout_summary_idx", {}).get(src_numb, {})
                new_qout = {k: v for k, v in src_qout.items()
                            if k not in ("inv_numb", "qoute_pdf", "qoute_doc")}
                new_qout["inv_numb"]      = new_inv_numb
                new_qout["status"]        = "Waiting"
                new_qout["payed_amount"]  = 0
                new_qout["oust_amount"]   = totals.get("total_balance", 0)
                new_qout["qoute_pdf"]     = ""
                new_qout["qoute_doc"]     = ""
                supabase.table("QouteSummary").insert(new_qout).execute()

            st.success(f"✅ Invoice cloned as new draft #{new_inv_numb}.")
            self.update_database()
            st.rerun()
        except Exception as e:
            st.error(f"Clone failed: {e}")
            print(f"[clone_inv] error: {e}")

    def delete_inv(self, inv):
        supabase.table("InvoiceDetails").delete().eq("inv_numb", inv.get("inv_numb")).execute()
        supabase.table("InvoiceSummary").delete().eq("inv_numb", inv.get("inv_numb")).execute()
        self.update_database()
        self.close_inv()
        st.rerun()

    def fin_inv_conv(self):
        qm = Qoute_Manager()
        qm.fin_inv_conv()

    def mark_as_incomplete(self, inv):
        respond = (
            supabase.table("InvoiceSummary")
            .update({"inv_status": "inprogress"})
            .eq("inv_numb", inv.get("inv_numb"))
            .execute()
        )
        if respond.data:
            self.update_database()
            self.close_inv()
            st.rerun()

    # ------------------------------------------------------------------
    # Summary table view
    # ------------------------------------------------------------------

    def show_inv_tables(self):
        inv_df = pd.DataFrame(st.session_state.invoice_summary)
        inv_df = inv_df.drop(columns=[c for c in ["inv_id", "inv_doc"] if c in inv_df.columns])
        inv_df["total_amount"] = inv_df["total_amount"].apply(lambda x: f"R {float(x):,.2f}" if str(x).replace('.', '', 1).isdigit() else x)
        inv_df["paid_amount"]  = inv_df["paid_amount"].apply(lambda x: f"R {float(x):,.2f}"  if str(x).replace('.', '', 1).isdigit() else x)
        inv_df["out_amount"]   = inv_df["out_amount"].apply(lambda x: f"R {float(x):,.2f}"   if str(x).replace('.', '', 1).isdigit() else x)
        inv_df["inv_date"]     = pd.to_datetime(inv_df["inv_date"], errors="coerce").dt.strftime("%d %b %Y")

        st.dataframe(
            inv_df,
            hide_index=True,
            width="stretch",      # replaces deprecated use_container_width=True
            column_config={
                "inv_numb":     st.column_config.TextColumn("Inv Number"),
                "inv_to":       st.column_config.TextColumn("Invoiced To"),
                "total_amount": st.column_config.TextColumn("Total (R)"),
                "paid_amount":  st.column_config.TextColumn("Paid (R)"),
                "out_amount":   st.column_config.TextColumn("Outstanding (R)"),
                "inv_date":     st.column_config.TextColumn("Date"),
                "inv_status":   st.column_config.TextColumn("Status"),
                "inv_name":     st.column_config.TextColumn("Invoice Name"),
                "inv_pdf":      st.column_config.LinkColumn("Invoice", display_text="View Invoice"),
            },
        )

    def list_inv(self):
        hdr_col, refresh_col = st.columns([5, 1])
        with hdr_col:
            st.title("🧾 Invoices")
        with refresh_col:
            st.write("")
            if st.button("🔄 Refresh", use_container_width=True, key="inv_list_refresh"):
                self.update_database()
                st.rerun()

        if st.session_state.invoice_summary:
            self._render_stats()
            self.show_inv_tables()
        else:
            st.info("No invoices found.")
