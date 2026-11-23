from models.Model import *
import pandas as pd
from datetime import date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fmt_date(value):
    """Format an ISO date string for display; return '—' if missing/invalid."""
    if not value:
        return "—"
    try:
        return date.fromisoformat(str(value)[:10]).strftime("%d %b %Y")
    except (ValueError, TypeError):
        return str(value)


def _money(value):
    """Format a numeric value as R currency, tolerating None/strings."""
    try:
        return f"R {float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "—"


class PaymentManager:
    """Backs the Payment page.

    Three views:
      * Payment Summary — tables of outstanding (not-invoiced, unpaid)
        quotations and unpaid invoices, each showing total / paid / outstanding.
      * Pay Quotation    — radio-list of quotations needing payment; selecting
        one reveals its summary and a payment capture form.
      * Pay Invoice      — same interaction for invoices.
    """

    def __init__(self):
        if "loaded" not in st.session_state:
            init_data()
            st.session_state.loaded = True

    # ------------------------------------------------------------------
    # Data filters
    # ------------------------------------------------------------------
    def quotes_needing_payment(self):
        """Quotations that have not been invoiced and have not been paid
        (status != invoiced AND outstanding > 0)."""
        return [
            q for q in st.session_state.qouteSummary
            if str(q.get("status", "")).lower() != "invoiced"
            and float(q.get("oust_amount", 0) or 0) > 0
        ]

    def invoices_needing_payment(self):
        """Invoices that have not been fully paid (outstanding > 0)."""
        return [
            i for i in st.session_state.invoice_summary
            if float(i.get("out_amount", 0) or 0) > 0
        ]

    def _quote_label(self, q):
        return (f"#{q.get('inv_numb', '—')}  ·  {q.get('inv_to', '—')}"
                f"  ·  Outstanding {_money(q.get('oust_amount', 0))}")

    def _invoice_label(self, i):
        return (f"#{i.get('inv_numb', '—')}  ·  {i.get('inv_to', '—')}"
                f"  ·  Outstanding {_money(i.get('out_amount', 0))}")

    # ------------------------------------------------------------------
    # Tab 1 — Payment Summary
    # ------------------------------------------------------------------
    def payment_summary(self):
        st.markdown("### 📊 Payment Summary")
        st.caption("Outstanding quotations (not invoiced, not paid) and unpaid invoices.")

        quotes = self.quotes_needing_payment()
        invoices = self.invoices_needing_payment()

        q_out = sum(float(q.get("oust_amount", 0) or 0) for q in quotes)
        i_out = sum(float(i.get("out_amount", 0) or 0) for i in invoices)

        k1, k2, k3, k4 = st.columns(4)
        with k1: st.metric("📋 Quotes to Pay", len(quotes))
        with k2: st.metric("🧾 Invoices to Pay", len(invoices))
        with k3: st.metric("💰 Quote Outstanding", _money(q_out))
        with k4: st.metric("💰 Invoice Outstanding", _money(i_out))

        st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0 1rem 0;'>",
                    unsafe_allow_html=True)

        st.markdown("#### 📋 Quotations Awaiting Payment")
        if quotes:
            self._quote_summary_table(quotes)
        else:
            st.success("✅ No quotations are awaiting payment.")

        st.markdown("")

        st.markdown("#### 🧾 Invoices Awaiting Payment")
        if invoices:
            self._invoice_summary_table(invoices)
        else:
            st.success("✅ No invoices are awaiting payment.")

    def _quote_summary_table(self, quotes):
        df = pd.DataFrame(quotes)
        cols = [c for c in ["inv_numb", "inv_to", "total_amount",
                            "payed_amount", "oust_amount", "status"]
                if c in df.columns]
        df = df[cols].copy()
        for col in ("total_amount", "payed_amount", "oust_amount"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").apply(_money)
        st.dataframe(
            df, hide_index=True, width="stretch",
            column_config={
                "inv_numb":     st.column_config.TextColumn("Quote #"),
                "inv_to":       st.column_config.TextColumn("Client"),
                "total_amount": st.column_config.TextColumn("Total Amount"),
                "payed_amount": st.column_config.TextColumn("Amount Paid"),
                "oust_amount":  st.column_config.TextColumn("Outstanding"),
                "status":       st.column_config.TextColumn("Status"),
            },
        )

    def _invoice_summary_table(self, invoices):
        df = pd.DataFrame(invoices)
        cols = [c for c in ["inv_numb", "inv_to", "total_amount",
                            "paid_amount", "out_amount", "inv_status"]
                if c in df.columns]
        df = df[cols].copy()
        for col in ("total_amount", "paid_amount", "out_amount"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").apply(_money)
        st.dataframe(
            df, hide_index=True, width="stretch",
            column_config={
                "inv_numb":     st.column_config.TextColumn("Invoice #"),
                "inv_to":       st.column_config.TextColumn("Client"),
                "total_amount": st.column_config.TextColumn("Total Amount"),
                "paid_amount":  st.column_config.TextColumn("Amount Paid"),
                "out_amount":   st.column_config.TextColumn("Outstanding"),
                "inv_status":   st.column_config.TextColumn("Status"),
            },
        )

    # ------------------------------------------------------------------
    # Tab 2 — Pay Quotation
    # ------------------------------------------------------------------
    def pay_quotation(self):
        st.markdown("### 💳 Pay Quotation")
        st.caption("Select a quotation, review its summary, then capture a payment.")

        quotes = self.quotes_needing_payment()
        if not quotes:
            st.success("✅ No quotations need payment right now.")
            return

        qout_idx = st.session_state.get("_qout_summary_idx", {})
        options = [q.get("inv_numb") for q in quotes]
        selected = st.radio(
            "Select a quotation to pay",
            options,
            format_func=lambda n: self._quote_label(qout_idx.get(n, {})),
        )
        if selected is None:
            return

        qout = qout_idx.get(selected, {})
        self._quote_detail_and_payment(qout)

    def _quote_detail_and_payment(self, qout):
        inv_numb = qout.get("inv_numb")
        details = st.session_state.get("_inv_details_idx", {}).get(inv_numb, {})
        items = st.session_state.get("_items_idx", {}).get(inv_numb, [])

        total = float(qout.get("total_amount", 0) or 0)
        paid = float(qout.get("payed_amount", 0) or 0)
        outstanding = float(qout.get("oust_amount", 0) or 0)

        with st.container(border=True):
            st.markdown(f"#### Quotation #{inv_numb}")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Document Details**")
                st.markdown(f"- **Number:** {inv_numb}")
                st.markdown(f"- **Client:** {qout.get('inv_to', '—')}")
                st.markdown(f"- **Date:** {_fmt_date(details.get('inv_date'))}")
                st.markdown(f"- **Due Date:** {_fmt_date(details.get('inv_duedate'))}")
                st.markdown(f"- **Status:** {qout.get('status', '—')}")
            with col2:
                st.markdown("**Payment Status**")
                m1, m2, m3 = st.columns(3)
                m1.metric("Total", _money(total))
                m2.metric("Paid", _money(paid))
                m3.metric("Outstanding", _money(outstanding))

            self._render_items(items)

            st.markdown("**Capture Payment**")
            new_payment = st.number_input(
                "Payment Amount (R)",
                min_value=0.00,
                max_value=float(outstanding),
                format="%.2f",
                key=f"quote_pay_amt_{inv_numb}",
            )
            if new_payment > 0:
                new_paid = paid + new_payment
                new_out = max(total - new_paid, 0)
                st.markdown(
                    f"<p style='color:#6b7280; font-size:0.88rem;'>"
                    f"After this payment: Paid = <b>{_money(new_paid)}</b> "
                    f"· Outstanding = <b>{_money(new_out)}</b></p>",
                    unsafe_allow_html=True,
                )

            if st.button("💾 Save Payment", type="primary",
                         use_container_width=True, key=f"save_quote_pmt_{inv_numb}"):
                if new_payment <= 0:
                    st.warning("Please enter a payment amount greater than R 0.")
                else:
                    self.save_quote_payment(inv_numb, new_payment)

    def save_quote_payment(self, inv_numb, amount):
        qout = st.session_state.get("_qout_summary_idx", {}).get(inv_numb, {})
        total = float(qout.get("total_amount", 0) or 0)
        paid_so_far = float(qout.get("payed_amount", 0) or 0)
        new_paid = paid_so_far + amount
        new_outstanding = max(total - new_paid, 0)

        update = {
            "payed_amount": new_paid,
            "oust_amount": new_outstanding,
        }
        # A first payment moves a waiting quotation into progress.
        if str(qout.get("status", "")).lower() == "waiting":
            update["status"] = "Inprogress"

        try:
            with st.spinner("Saving payment..."):
                supabase.table("QouteSummary").update(update)\
                    .eq("inv_numb", inv_numb).execute()
            st.success(f"✅ Payment of {_money(amount)} recorded for quotation #{inv_numb}.")
            init_data()
            st.session_state.loaded = True
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save payment: {e}")
            print(f"[save_quote_payment] error: {e}")

    # ------------------------------------------------------------------
    # Tab 3 — Pay Invoice
    # ------------------------------------------------------------------
    def pay_invoice(self):
        st.markdown("### 💳 Pay Invoice")
        st.caption("Select an invoice, review its summary, then capture a payment.")

        invoices = self.invoices_needing_payment()
        if not invoices:
            st.success("✅ No invoices need payment right now.")
            return

        inv_idx = {i.get("inv_numb"): i for i in st.session_state.invoice_summary}
        options = [i.get("inv_numb") for i in invoices]
        selected = st.radio(
            "Select an invoice to pay",
            options,
            format_func=lambda n: self._invoice_label(inv_idx.get(n, {})),
        )
        if selected is None:
            return

        inv = inv_idx.get(selected, {})
        self._invoice_detail_and_payment(inv)

    def _invoice_detail_and_payment(self, inv):
        inv_numb = inv.get("inv_numb")
        details = st.session_state.get("_inv_details_idx", {}).get(inv_numb, {})
        items = st.session_state.get("_items_idx", {}).get(inv_numb, [])

        total = float(inv.get("total_amount", 0) or 0)
        paid = float(inv.get("paid_amount", 0) or 0)
        outstanding = float(inv.get("out_amount", 0) or 0)

        with st.container(border=True):
            st.markdown(f"#### Invoice #{inv_numb}")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Document Details**")
                st.markdown(f"- **Number:** {inv_numb}")
                st.markdown(f"- **Client:** {inv.get('inv_to', '—')}")
                st.markdown(f"- **Date:** {_fmt_date(inv.get('inv_date'))}")
                st.markdown(f"- **Due Date:** {_fmt_date(details.get('inv_duedate'))}")
                st.markdown(f"- **Status:** {inv.get('inv_status', '—')}")
                if details.get("cust_email"):
                    st.markdown(f"- **Email:** {details.get('cust_email')}")
            with col2:
                st.markdown("**Payment Status**")
                m1, m2, m3 = st.columns(3)
                m1.metric("Total", _money(total))
                m2.metric("Paid", _money(paid))
                m3.metric("Outstanding", _money(outstanding))

            self._render_items(items)

            st.markdown("**Capture Payment**")
            new_payment = st.number_input(
                "Payment Amount (R)",
                min_value=0.00,
                max_value=float(outstanding),
                format="%.2f",
                key=f"inv_pay_amt_{inv_numb}",
            )
            if new_payment > 0:
                new_paid = paid + new_payment
                new_out = max(total - new_paid, 0)
                st.markdown(
                    f"<p style='color:#6b7280; font-size:0.88rem;'>"
                    f"After this payment: Paid = <b>{_money(new_paid)}</b> "
                    f"· Outstanding = <b>{_money(new_out)}</b></p>",
                    unsafe_allow_html=True,
                )

            if st.button("💾 Save Payment", type="primary",
                         use_container_width=True, key=f"save_inv_pmt_{inv_numb}"):
                if new_payment <= 0:
                    st.warning("Please enter a payment amount greater than R 0.")
                else:
                    self.save_invoice_payment(inv_numb, new_payment)

    def save_invoice_payment(self, inv_numb, amount):
        inv = next((i for i in st.session_state.invoice_summary
                    if i.get("inv_numb") == inv_numb), {})
        total = float(inv.get("total_amount", 0) or 0)
        paid_so_far = float(inv.get("paid_amount", 0) or 0)
        new_paid = paid_so_far + amount
        new_outstanding = max(total - new_paid, 0)
        new_status = "complete" if new_outstanding == 0 else "inprogress"

        try:
            with st.spinner("Saving payment..."):
                supabase.table("InvoiceSummary").update({
                    "paid_amount": new_paid,
                    "out_amount": new_outstanding,
                    "inv_status": new_status,
                }).eq("inv_numb", inv_numb).execute()
            st.success(f"✅ Payment of {_money(amount)} recorded for invoice #{inv_numb}.")
            init_data()
            st.session_state.loaded = True
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save payment: {e}")
            print(f"[save_invoice_payment] error: {e}")

    # ------------------------------------------------------------------
    # Shared: items table
    # ------------------------------------------------------------------
    def _render_items(self, items):
        st.markdown("**Items**")
        if not items:
            st.info("No items on record.")
            return
        df = pd.DataFrame(items)
        drop = [c for c in ("item_id", "inv_numb") if c in df.columns]
        if drop:
            df = df.drop(columns=drop)
        for col in ("unit_price", "total_price"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").apply(_money)
        st.dataframe(
            df, hide_index=True, width="stretch",
            column_config={
                "item_description": st.column_config.TextColumn("Description"),
                "unit_price":       st.column_config.TextColumn("Unit Price"),
                "quantity":         st.column_config.NumberColumn("Qty"),
                "total_price":      st.column_config.TextColumn("Total"),
            },
        )
