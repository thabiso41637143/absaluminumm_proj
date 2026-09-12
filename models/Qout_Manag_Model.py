from models.Model import *
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reset_pages(self):
        for key in ("view_next_job", "view_prev_job", "view_next_inv", "view_prev_inv"):
            st.session_state.pop(key, None)

    def get_qout_summary(self, inv_numb):
        return st.session_state.get('_qout_summary_idx', {}).get(inv_numb)

    def get_qout_details(self, inv_numb):
        return st.session_state.get('_inv_details_idx', {}).get(inv_numb)

    def get_qout_totals(self, inv_numb):
        return st.session_state.get('_inv_totals_idx', {}).get(inv_numb)

    def get_qout_items(self, inv_numb):
        return st.session_state.get('_items_idx', {}).get(inv_numb, [])

    def close_qoutation(self):
        st.session_state.edit_qoute = False
        st.session_state.qout_page = 0
        st.session_state.selected_qoute = None

    def next_list(self):
        data = self._filtered_data()
        total_pages = max(0, len(data) - 1) // st.session_state.qout_page_size
        if st.session_state.qout_page < total_pages:
            st.session_state.qout_page += 1

    def prev_list(self):
        if st.session_state.qout_page > 0:
            st.session_state.qout_page -= 1

    def _filtered_data(self):
        status_filter = st.session_state.get("qout_status_filter", "All")
        today = date.today()
        all_data = [q for q in st.session_state.qouteSummary if q.get('status') != 'Invoiced']

        if status_filter == "Waiting":
            return [q for q in all_data if str(q.get('status', '')).lower() == 'waiting']
        elif status_filter == "In Progress":
            return [q for q in all_data if str(q.get('status', '')).lower() == 'inprogress']
        elif status_filter == "Overdue":
            result = []
            for q in all_data:
                details = self.get_qout_details(q.get('inv_numb'))
                due = details.get('inv_duedate') if details else None
                if due:
                    try:
                        due_date = date.fromisoformat(str(due)[:10])
                        if due_date < today:
                            result.append(q)
                    except (ValueError, TypeError):
                        pass
            return result
        return all_data

    # ------------------------------------------------------------------
    # Main UI
    # ------------------------------------------------------------------

    def set_qout_UI(self):
        if st.session_state.get('update_qoutation'):
            if st.session_state.get('email'):
                self.send_email()
            elif st.session_state.get('edit_qoutation'):
                self.set_qoutation()
            else:
                self.fin_inv_conv()
            return

        # ── Header row ───────────────────────────────────────────────────
        hdr_col, refresh_col = st.columns([5, 1])
        with hdr_col:
            st.title("📋 Manage Quotations")
        with refresh_col:
            st.write("")
            if st.button("🔄 Refresh", use_container_width=True):
                init_data()
                st.session_state.loaded = True
                st.session_state.qout_page = 0
                st.rerun()

        # ── Stats bar ────────────────────────────────────────────────────
        self._render_stats()

        # ── Status filter ────────────────────────────────────────────────
        filter_options = ["All", "Waiting", "In Progress", "Overdue"]
        current_filter = st.session_state.get("qout_status_filter", "All")
        cols = st.columns(len(filter_options))
        for i, opt in enumerate(filter_options):
            with cols[i]:
                btn_type = "primary" if current_filter == opt else "secondary"
                if st.button(opt, key=f"qout_filter_{opt}", type=btn_type, use_container_width=True):
                    st.session_state.qout_status_filter = opt
                    st.session_state.qout_page = 0
                    st.rerun()

        st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0 1rem 0;'>", unsafe_allow_html=True)

        data = self._filtered_data()
        if not data:
            st.info("No quotations found for the selected filter.")
            self._render_close_button()
            return

        page = st.session_state.qout_page
        size = st.session_state.qout_page_size
        total = len(data)
        last_page = max(0, (total - 1) // size)
        start = page * size
        end = min(start + size, total)
        page_data = data[start:end]

        for r in range(0, len(page_data), 3):
            cols = st.columns(3, gap="medium")
            for col, qout in zip(cols, page_data[r:r + 3]):
                with col:
                    with st.container(border=True):
                        self.set_tiles(qout)

        self._render_pagination(page, last_page, total, start, end)

    def _render_stats(self):
        today = date.today()
        all_q = st.session_state.qouteSummary
        waiting    = sum(1 for q in all_q if str(q.get('status', '')).lower() == 'waiting')
        inprogress = sum(1 for q in all_q if str(q.get('status', '')).lower() == 'inprogress')
        invoiced   = sum(1 for q in all_q if str(q.get('status', '')).lower() == 'invoiced')
        overdue = 0
        for q in all_q:
            det = self.get_qout_details(q.get('inv_numb'))
            due = det.get('inv_duedate') if det else None
            if due:
                try:
                    if date.fromisoformat(str(due)[:10]) < today:
                        overdue += 1
                except (ValueError, TypeError):
                    pass

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("⏳ Waiting", waiting)
        with c2: st.metric("🚧 In Progress", inprogress)
        with c3: st.metric("⚠️ Overdue", overdue)
        with c4: st.metric("✅ Invoiced", invoiced)
        st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0;'>", unsafe_allow_html=True)

    def _render_pagination(self, page, last_page, total, start, end):
        st.markdown("<hr style='border:1px solid #d1d5db; margin:1rem 0 0.5rem 0;'>", unsafe_allow_html=True)
        close_col, prev_col, info_col, next_col = st.columns([1, 1, 2, 1])
        with close_col:
            st.button("✖ Close", on_click=self.close_qoutation, use_container_width=True)
        with prev_col:
            st.button("◀ Prev", on_click=self.prev_list,
                      disabled=(page == 0), type="primary", use_container_width=True, key="qout_prev")
        with info_col:
            st.markdown(
                f"<p style='text-align:center; margin-top:0.5rem; color:#6b7280; font-size:0.9rem;'>"
                f"Page <b>{page + 1}</b> of <b>{last_page + 1}</b> &nbsp;·&nbsp; "
                f"Showing <b>{start + 1}–{end}</b> of <b>{total}</b></p>",
                unsafe_allow_html=True,
            )
        with next_col:
            st.button("Next ▶", on_click=self.next_list,
                      disabled=(page >= last_page), type="primary", use_container_width=True, key="qout_next")

    def _render_close_button(self):
        if st.button("✖ Close", key="qout_close_empty"):
            self.close_qoutation()
            st.rerun()

    # ------------------------------------------------------------------
    # Tile
    # ------------------------------------------------------------------

    def set_tiles(self, qout):
        today     = date.today()
        status    = str(qout.get('status', '')).lower()
        inv_numb  = qout.get('inv_numb')

        # ── Status badge ─────────────────────────────────────────────────
        details  = self.get_qout_details(inv_numb)
        due_raw  = details.get('inv_duedate') if details else None
        is_overdue = False
        if due_raw:
            try:
                is_overdue = date.fromisoformat(str(due_raw)[:10]) < today
            except (ValueError, TypeError):
                pass

        if is_overdue:
            badge_colour, badge_label = "#b91c1c", "🔴 OVERDUE"
        elif status == "inprogress":
            badge_colour, badge_label = "#d97706", "🟠 IN PROGRESS"
        elif status == "waiting":
            badge_colour, badge_label = "#2563eb", "🔵 WAITING"
        else:
            badge_colour, badge_label = "#6b7280", f"⚪ {status.upper()}"

        st.markdown(
            f"<span style='background:{badge_colour}; color:white; padding:2px 10px; "
            f"border-radius:12px; font-size:0.78rem; font-weight:600;'>{badge_label}</span>",
            unsafe_allow_html=True,
        )

        # ── Client & amount ───────────────────────────────────────────────
        st.markdown(f"### {qout.get('inv_to', '—')}")
        st.markdown(f"**Quote #:** `{inv_numb}`")
        st.markdown(
            f"<p style='font-size:1.1rem; font-weight:700; color:#1f2937;'>"
            f"R {float(qout.get('total_amount', 0)):.2f}</p>",
            unsafe_allow_html=True,
        )

        # ── PDF / Doc buttons ────────────────────────────────────────────
        pdf_col, doc_col = st.columns(2)
        with pdf_col:
            if st.button("📄 PDF", key=f"pdf_{inv_numb}", use_container_width=True):
                webbrowser.open(qout.get("qoute_pdf", ""))
        with doc_col:
            if st.button("📝 Doc", key=f"doc_{inv_numb}", use_container_width=True):
                webbrowser.open(qout.get("qoute_doc", ""))

        st.markdown("<hr style='border:1px dotted #d1d5db; margin:6px 0;'>", unsafe_allow_html=True)

        # ── Action buttons ───────────────────────────────────────────────
        action_key = f"qout_action_{inv_numb}"
        current_action = st.session_state.get(action_key)

        if current_action is None:
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("✅ Approve", key=f"approve_{inv_numb}", use_container_width=True, type="primary"):
                    st.session_state[action_key] = "approve"
                    st.rerun()
            with b2:
                if st.button("🧾 Invoice", key=f"invoice_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "invoice"
                    st.rerun()
            with b3:
                if st.button("✏️ Edit", key=f"edit_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "edit"
                    st.rerun()

            b4, b5, b6 = st.columns(3)
            with b4:
                if st.button("✉️ Email", key=f"email_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "email"
                    st.rerun()
            with b5:
                if st.button("📋 Clone", key=f"clone_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "clone"
                    st.rerun()
            with b6:
                if st.button("🗑️ Delete", key=f"delete_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "delete"
                    st.rerun()

        elif current_action == "approve":
            self._action_back_button(action_key, inv_numb, "approve")
            self.approve_qoute(qout=qout)

        elif current_action == "invoice":
            st.warning(f"Convert **{qout.get('inv_to')}** (#{inv_numb}) to an invoice?")
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button("✔ Yes, convert", key=f"yes_inv_{inv_numb}", type="primary", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    self.convert_inv(qout=qout)
            with no_col:
                if st.button("✖ Cancel", key=f"no_inv_{inv_numb}", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    st.rerun()

        elif current_action == "edit":
            st.session_state.pop(action_key, None)
            self.edit_qoutation(qout=qout)

        elif current_action == "email":
            st.session_state.pop(action_key, None)
            self.send_qoutation(qout=qout)

        elif current_action == "clone":
            st.session_state.pop(action_key, None)
            self.clone_qoutation(qout=qout)

        elif current_action == "delete":
            st.error(f"Permanently delete quote **#{inv_numb}** for **{qout.get('inv_to')}**? This cannot be undone.")
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button("🗑️ Yes, delete", key=f"yes_del_{inv_numb}", type="primary", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    self.delete_qoutation(qout=qout)
            with no_col:
                if st.button("✖ Cancel", key=f"no_del_{inv_numb}", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    st.rerun()

    def _action_back_button(self, action_key, inv_numb, suffix):
        if st.button("← Back", key=f"back_{suffix}_{inv_numb}"):
            st.session_state.pop(action_key, None)
            st.rerun()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def edit_qoutation(self, qout):
        qout_details = self.get_qout_details(inv_numb=qout.get('inv_numb'))
        st.session_state.edit_qout_inv = {
            "Invto":     qout.get('inv_to'),
            "cust_tax":  qout_details.get('cust_tax'),
            "email":     qout_details.get('cust_email'),
            "contnumb":  qout_details.get('cust_numb'),
            "adr":       qout_details.get('cust_address'),
            "custtype":  qout_details.get('cust_group'),
            "Invnumb":   qout_details.get('inv_numb'),
            "date":      qout_details.get('inv_date'),
            "duedate":   qout_details.get('inv_duedate'),
        }
        items = self.get_qout_items(inv_numb=qout.get('inv_numb'))
        st.session_state.material_df = pd.DataFrame(items)
        if not st.session_state.material_df.empty:
            st.session_state.material_df.rename(columns={
                "total_price":       "Total amount",
                "unit_price":        "Unit price",
                "item_description":  "Description",
                "quantity":          "Quantity",   # fixed typo: was 'Qantity'
            }, inplace=True)
            st.session_state.material_df.drop(
                columns=[c for c in ['inv_numb', 'item_id'] if c in st.session_state.material_df.columns],
                inplace=True,
            )
        st.session_state.update_qoutation = True
        st.session_state.edit_qoutation = True
        st.rerun()

    def set_qoutation(self):
        qout_ui = InvQouteUI(invQouteUrl=(
            "https://script.google.com/macros/s/"
            "AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCV"
            "KsLwqrAJWkjOUVhZd7k9qA/exec?option=supabaseDB&invNumb="
        ))
        qout_ui.gen_ui(gen_message="**Generate Quotation**")

    def clone_qoutation(self, qout):
        """Duplicate a quotation to a new invoice number as a fresh Waiting draft."""
        src_numb = qout.get("inv_numb")
        details  = self.get_qout_details(src_numb) or {}
        items    = self.get_qout_items(src_numb)
        totals   = self.get_qout_totals(src_numb) or {}

        try:
            with st.spinner("📋 Cloning quotation..."):
                # Allocate a fresh invoice number from the generator
                new_gen = supabase.table("invGenerator").insert({"status": "used"}).execute()
                if not new_gen.data:
                    st.error("Could not generate a new invoice number.")
                    return
                new_gen_id = new_gen.data[0]["gen_id"]

                # Build new inv_numb using the same customer group prefix
                cust_group   = details.get("cust_group", "")
                cat_map      = {r["category"]: r["starting_number"]
                                for r in st.session_state.get("customer_category", [])}
                prefix       = cat_map.get(cust_group, 1)
                new_inv_numb = int(f"{prefix}{date.today().year}{new_gen_id}")

                # ── Clone InvoiceDetails ──────────────────────────────────
                new_details = {k: v for k, v in details.items()
                               if k != "inv_numb"}
                new_details["inv_numb"]    = new_inv_numb
                new_details["inv_date"]    = date.today().isoformat()
                new_details["inv_duedate"] = (date.today() + timedelta(days=30)).isoformat()
                supabase.table("InvoiceDetails").insert(new_details).execute()

                # ── Clone Items ───────────────────────────────────────────
                new_items = []
                for item in items:
                    new_item = {k: v for k, v in item.items()
                                if k not in ("item_id", "inv_numb")}
                    new_item["inv_numb"] = new_inv_numb
                    new_items.append(new_item)
                if new_items:
                    supabase.table("Items").insert(new_items).execute()

                # ── Clone Totals ──────────────────────────────────────────
                new_totals = {k: v for k, v in totals.items()
                              if k != "inv_numb"}
                new_totals["inv_numb"] = new_inv_numb
                supabase.table("Totals").insert(new_totals).execute()

                # ── Create fresh QouteSummary row (status = Waiting) ──────
                src_qout = st.session_state.get("_qout_summary_idx", {}).get(src_numb, {})
                new_qout = {k: v for k, v in src_qout.items()
                            if k not in ("inv_numb", "qoute_pdf", "qoute_doc")}
                new_qout["inv_numb"]     = new_inv_numb
                new_qout["status"]       = "Waiting"
                new_qout["payed_amount"] = 0
                new_qout["oust_amount"]  = totals.get("total_balance", 0)
                new_qout["qoute_pdf"]    = ""
                new_qout["qoute_doc"]    = ""
                supabase.table("QouteSummary").insert(new_qout).execute()

            st.success(f"✅ Quotation cloned as new draft #{new_inv_numb}. "
                       f"Find it under **Waiting** status.")
            init_data()
            st.session_state.loaded = True
            st.rerun()

        except Exception as e:
            st.error(f"Clone failed: {e}")
            print(f"[clone_qoutation] error: {e}")

    def approve_qoute(self, qout):
        st.write("You are about to approve this quotation.")
        st.markdown(
            f"<p style='color:#d97706; font-weight:bold;'>To: {qout.get('inv_to')}</p>",
            unsafe_allow_html=True,
        )
        total_qout = self.get_qout_totals(qout.get("inv_numb"))
        if not total_qout:
            st.warning("Could not load totals for this quotation.")
            return

        st.write(f"**Required Deposit: R {float(total_qout.get('deposit', 0)):.2f}**")
        payed_amount = st.number_input(
            "Amount Paid", format="%0.2f",
            key=f"payed_amount_{inv_numb}" if (inv_numb := qout.get('inv_numb')) else "payed_amount",
            min_value=0.00,
        )
        if st.button("✅ Confirm Approval", key=f"continue_{qout.get('inv_numb')}"):
            response = (
                supabase.table("QouteSummary")
                .update({
                    "status": "Inprogress",
                    "payed_amount": payed_amount,
                    "oust_amount": float(total_qout.get("total_balance", 0)) - payed_amount,
                })
                .eq("inv_numb", qout.get("inv_numb"))
                .execute()
            )
            if response.data:
                st.success(f"Quotation #{qout.get('inv_numb')} is now In Progress 🚧")
                init_data()
                st.session_state.loaded = True
                st.rerun()
            else:
                st.warning("Quotation was not found ⚠️")

    def convert_inv(self, qout):
        st.session_state.selected_qoutation = {
            "invoice details": qout,
            "invoice summary": self.get_qout_summary(inv_numb=qout.get('inv_numb')),
            "invoice total":   self.get_qout_totals(inv_numb=qout.get('inv_numb')),
        }
        items_list = self.get_qout_items(qout.get('inv_numb'))
        st.session_state.selected_qoutation['invoice items'] = items_list

        if st.session_state.selected_qoutation.get('invoice summary') and items_list:
            st.session_state.update_qoutation = True
            st.rerun()
        else:
            st.error("Failed to load the quotation details. Please refresh and try again.")

    def fin_inv_conv(self):
        invoice_details = st.session_state.selected_qoutation['invoice details']
        invoice_items   = st.session_state.selected_qoutation['invoice items']
        invoice_summary = st.session_state.selected_qoutation['invoice summary']
        invoice_totals  = st.session_state.selected_qoutation['invoice total']

        with st.container(border=True):
            st.markdown(
                "<p style='color:#2563eb; font-weight:700; font-size:1rem; text-align:center;'>"
                "INVOICE DETAILS</p>",
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Invoice Number:** {invoice_details.get('inv_numb')}")
                st.write(f"**Invoice Date:** {date.today().strftime('%d %b %Y')}")
            with col2:
                st.write(f"**Invoice To:** {invoice_details.get('inv_to')}")
                st.write(f"**Email:** {invoice_details.get('cust_email')}")
                st.write(f"**Contact:** {invoice_details.get('cust_numb')}")
                st.write(f"**Address:** {invoice_details.get('cust_address')}")

            st.markdown("<hr style='border:1px dotted #d1d5db;'>", unsafe_allow_html=True)
            st.markdown(
                "<p style='color:#2563eb; font-weight:700; font-size:1rem; text-align:center;'>"
                "INVOICE ITEMS</p>",
                unsafe_allow_html=True,
            )
            df = pd.DataFrame(invoice_items)
            df = df.drop(columns=[c for c in ["item_id", "inv_numb"] if c in df.columns])
            df["unit_price"]  = df["unit_price"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
            df["total_price"] = df["total_price"].apply(lambda x: f"R {float(x):.2f}" if str(x).replace('.', '', 1).isdigit() else x)
            st.dataframe(df, hide_index=True, width="stretch",
                column_config={
                    "item_description": st.column_config.TextColumn("Description"),
                    "unit_price":       st.column_config.TextColumn("Unit Price (R)"),
                    "quantity":         st.column_config.TextColumn("Qty"),
                    "total_price":      st.column_config.TextColumn("Total (R)"),
                })

            st.markdown("<hr style='border:1px dotted #d1d5db;'>", unsafe_allow_html=True)
            st.markdown(
                "<p style='color:#2563eb; font-weight:700; font-size:1rem; text-align:center;'>"
                "TOTAL SUMMARY</p>",
                unsafe_allow_html=True,
            )
            tot1, tot2 = st.columns(2)
            with tot1:
                st.write(f"**Deposit:** R {float(invoice_totals.get('deposit', 0)):.2f}")
                st.write(f"**Installation Cost:** R {float(invoice_totals.get('installation_cost', 0)):.2f}")
                st.write(f"**Discount:** R {float(invoice_totals.get('discount', 0)):.2f}")
            with tot2:
                st.write(f"**Total Amount:** R {float(invoice_summary.get('total_amount', 0)):.2f}")
                st.write(f"**Amount Paid:** R {float(invoice_summary.get('payed_amount', 0)):.2f}")
                st.write(f"**Outstanding:** R {float(invoice_summary.get('oust_amount', 0)):.2f}")

            st.markdown(
                f"<p style='color:#b91c1c; font-weight:700; font-size:1.1rem;'>"
                f"Balance Due: R {float(invoice_summary.get('total_amount', 0)):.2f}</p>",
                unsafe_allow_html=True,
            )

            left, spacer, right = st.columns([1, 2, 1])
            with left:
                inv_numb_key = str(invoice_details.get("inv_numb"))
                if st.button("🧾 Generate Invoice", key=f"generate_{inv_numb_key}", type="primary", use_container_width=True):
                    gen_inv_url = (
                        "https://script.google.com/macros/s/"
                        "AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCV"
                        "KsLwqrAJWkjOUVhZd7k9qA/exec?option=supabaseDB&menue=createInvoice&invNumb="
                        + inv_numb_key
                    )
                    with st.spinner("⏳ Generating invoice..."):
                        resultsSet = requests.get(gen_inv_url)
                        results = json.loads(resultsSet.text)
                        print(results)
                    init_data()
                    st.session_state.update_qoutation = False
                    st.session_state.current_job_qout = False
                    st.session_state.loaded = True
                    st.rerun()
            with right:
                if st.button("✖ Cancel", key=f"cancel_inv_{inv_numb_key}", type="secondary", use_container_width=True):
                    st.session_state.update_qoutation = False
                    st.session_state.current_job_qout = False
                    st.rerun()

    def delete_qoutation(self, qout):
        response = supabase.table("InvoiceDetails").delete().eq("inv_numb", qout.get("inv_numb")).execute()
        url_delete = (
            "https://script.google.com/macros/s/"
            "AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCV"
            "KsLwqrAJWkjOUVhZd7k9qA/exec?option=supabaseDB&menue=deleteQoutation&invNumb="
            + str(qout.get("inv_numb"))
        )
        requests.get(url_delete)
        if response.data:
            st.success(f"Quotation #{qout.get('inv_numb')} permanently deleted 🗑️")
            init_data()
            st.session_state.loaded = True
            st.rerun()
        else:
            st.warning("Quotation not found ⚠️")

    def send_email(self):
        selected = st.session_state.get('selected_qoutation', {})
        if 'qoutation' in selected:
            qout       = selected['qoutation']
            email_type = 'emailQoutation'
            subject_line = f"Quotation Number: {qout.get('inv_numb')}"
            cont_message = (
                "Dear Sir/Madam,\n\n"
                "Please find the attached quotation for your review.\n\n"
                "Kind regards,\nABSALUMINUM (PTY) LTD\n"
            )
        elif 'invoice' in selected:
            qout       = selected['invoice']
            email_type = 'emailInvoice'
            subject_line = f"Invoice Number: {qout.get('inv_numb')}"
            cont_message = (
                "Dear Sir/Madam,\n\n"
                "Please find the attached invoice for your reference.\n\n"
                "Kind regards,\nABSALUMINUM (PTY) LTD\n"
            )
        else:
            st.error("No quotation or invoice selected for emailing.")
            return

        email_address = ""
        for inv_details in st.session_state.invoice_details:
            if inv_details.get("inv_numb") == qout.get('inv_numb'):
                email_address = inv_details.get("cust_email", "")
                break

        with st.container(border=True):
            st.markdown("### ✉️ Send Email")
            email    = st.text_input("Email address", key=f"emails_{qout.get('inv_numb')}", value=email_address)
            subj     = st.text_input("Subject",       key=f"subject_{qout.get('inv_numb')}", value=subject_line)
            contents = st.text_area("Message",        key=f"contents_{qout.get('inv_numb')}", value=cont_message, height=150)

            send_col, cancel_col, _ = st.columns([1, 1, 3])
            with send_col:
                if st.button("📤 Send", key=f"send_{qout.get('inv_numb')}", type="primary", use_container_width=True):
                    supabase.table("InvoiceDetails").update({"cust_email": email}).eq("inv_numb", qout.get("inv_numb")).execute()
                    base_url = (
                        "https://script.google.com/macros/s/"
                        "AKfycbw5AToPOc7vpUhNGLLQ-9SEaWiXTXkBRDny8AiLBPwgUwCV"
                        "KsLwqrAJWkjOUVhZd7k9qA/exec"
                    )
                    params = {"option": "supabaseDB", "menue": email_type,
                              "subject": subj, "contents": contents, "invNumb": str(qout.get('inv_numb'))}
                    with st.spinner("⏳ Sending..."):
                        requests.get(base_url + "?" + urlencode(params))
                    st.session_state.update_qoutation = False
                    st.session_state.email = False
                    st.session_state.update_invoice = False
                    st.rerun()
            with cancel_col:
                if st.button("✖ Cancel", key=f"cancel_{qout.get('inv_numb')}", use_container_width=True):
                    st.session_state.update_qoutation = False
                    st.session_state.email = False
                    st.session_state.update_invoice = False
                    st.rerun()

    def send_qoutation(self, qout):
        st.session_state.selected_qoutation = {"qoutation": qout}
        st.session_state.update_qoutation = True
        st.session_state.email = True
        st.rerun()
