import streamlit as st
from models.Model import AbsStaff, Contract, StaffAttendence, Users, inject_css, supabase, init_users, init_staff_rate, init_att_reg, init_loans, init_payments
from models.User_Model import *
import time
from datetime import date

abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(
    page_title="Staff Members | Absaluminum".upper(),
    page_icon=abs_icon,
    layout="wide",
)
inject_css()

# ──────────────────────────────────────────────────────────────────────────────
# Staff Summary view
# ──────────────────────────────────────────────────────────────────────────────

def show_staff(abs_staff: Users):
    staff_list = abs_staff.get_abs_staff()   # group 219 only (was get_all_users)

    if not staff_list:
        st.info("No staff members found.")
        return

    # Two-column grid
    for i in range(0, len(staff_list), 2):
        cols = st.columns(2, gap="medium")
        for col, user in zip(cols, staff_list[i:i + 2]):
            with col:
                _render_staff_card(user)


def _delete_staff(user_id: str, full_names: str):
    """Delete a staff member and all their related records from Supabase,
    then refresh the in-session caches so the card disappears immediately."""
    try:
        # Delete child records first to respect foreign key constraints.
        # StaffPayment.staff_id is ON DELETE SET NULL, so payment history is
        # preserved (staff_id becomes NULL) rather than deleted.
        supabase.table("StaffLoans").delete().eq("staff_id", user_id).execute()
        supabase.table("StaffAttendance").delete().eq("staff_id", user_id).execute()
        supabase.table("StaffRates").delete().eq("staff_id", user_id).execute()
        supabase.table("users").delete().eq("user_id", user_id).execute()

        # Refresh caches
        init_users()
        init_staff_rate()
        init_att_reg()
        init_loans()
        init_payments()

        st.success(f"✅ **{full_names}** (`{user_id}`) has been deleted.")
        time.sleep(0.5)   # let the socket close cleanly before rerun
        st.rerun()
    except Exception as e:
        st.error(f"Failed to delete staff member: {e}")


def _render_loans_panel(abs_user, uid):
    """List a staff member's loans with review/edit/payment controls, plus a
    form to record a new advance."""
    loans_mgr = abs_user.loans
    loans = loans_mgr.get_loans()

    outstanding = loans_mgr.get_total_outstanding()
    if outstanding > 0:
        st.warning(f"⚠️ Total outstanding across all loans: **R {outstanding:,.2f}**")
    else:
        st.success("✅ No outstanding loans.")

    # ── Existing loans ────────────────────────────────────────────────────
    for loan in loans:
        loan_id = loan.get("loan_id")
        loan_amt = float(loan.get("loan_amount", 0) or 0)
        paid_amt = float(loan.get("paid_amount", 0) or 0)
        out_amt  = float(loan.get("out_amount", 0) or 0)
        status   = loan.get("status", "unsettled")

        badge = {"settled": "#16a34a", "partially settled": "#d97706"}.get(status, "#b91c1c")

        with st.container(border=True):
            st.markdown(
                f"**📅 {loan.get('loan_date', '—')}**  "
                f"<span style='background:{badge}; color:white; padding:1px 8px; "
                f"border-radius:10px; font-size:0.72rem;'>{status}</span>",
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns(3)
            c1.metric("Borrowed", f"R {loan_amt:,.2f}")
            c2.metric("Repaid",   f"R {paid_amt:,.2f}")
            c3.metric("Outstanding", f"R {out_amt:,.2f}")
            if loan.get("comments"):
                st.caption(f"📝 {loan.get('comments')}")

            # Record a repayment (only if something is still owed)
            if out_amt > 0:
                pay_col, btn_col = st.columns([2, 1])
                with pay_col:
                    pay = st.number_input(
                        "Repayment amount (R)", min_value=0.00, max_value=float(out_amt),
                        format="%0.2f", key=f"pay_{uid}_{loan_id}",
                    )
                with btn_col:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💵 Record Payment", key=f"paybtn_{uid}_{loan_id}", use_container_width=True):
                        if pay > 0:
                            loans_mgr.record_payment(loan_id, pay)
                            st.success(f"Recorded R {pay:,.2f} repayment.")
                            st.rerun()
                        else:
                            st.info("Enter an amount greater than R 0.00.")

            # Edit borrowed amount
            with st.expander("✏️ Edit borrowed amount"):
                new_amt = st.number_input(
                    "New borrowed amount (R)", min_value=0.00, value=loan_amt,
                    format="%0.2f", key=f"edit_{uid}_{loan_id}",
                )
                ec1, ec2 = st.columns(2)
                with ec1:
                    if st.button("💾 Save", key=f"editbtn_{uid}_{loan_id}", use_container_width=True):
                        loans_mgr.edit_loan_amount(loan_id, new_amt)
                        st.success("Loan amount updated.")
                        st.rerun()
                with ec2:
                    if st.button("🗑️ Delete Loan", key=f"delloan_{uid}_{loan_id}", use_container_width=True):
                        loans_mgr.delete_loan(loan_id)
                        st.success("Loan deleted.")
                        st.rerun()

    if not loans:
        st.info("No loans recorded for this staff member yet.")

    # ── New loan ──────────────────────────────────────────────────────────
    st.markdown("<hr style='border:1px dotted #d1d5db; margin:0.8rem 0;'>", unsafe_allow_html=True)
    st.markdown("**➕ Record a new advance / loan**")
    with st.form(f"new_loan_{uid}", clear_on_submit=True):
        f1, f2 = st.columns(2)
        with f1:
            new_date = st.date_input("Loan Date", value=date.today(), format="DD-MM-YYYY")
        with f2:
            new_loan_amt = st.number_input("Loan Amount (R)", min_value=0.00, format="%0.2f")
        new_comment = st.text_input("Reason / Comment", placeholder="Optional")
        if st.form_submit_button("💾 Save Loan", type="primary", use_container_width=True):
            if new_loan_amt <= 0:
                st.error("Loan amount must be greater than R 0.00.")
            else:
                loans_mgr.create_loan(new_date, new_loan_amt, new_comment)
                st.success(f"Loan of R {new_loan_amt:,.2f} recorded.")
                st.rerun()


def _render_pay_panel(abs_user, uid):
    """Record a payment. Pre-fills gross salary + full outstanding loan
    (both overridable — option C), computes net, and settles the loan portion."""
    gross, outstanding = abs_user.get_pay_figures()

    st.markdown(
        f"<p style='color:#6b7280; font-size:0.88rem;'>"
        f"Computed gross salary (Active agreements): <b>R {gross:,.2f}</b>. "
        f"Outstanding loans: <b>R {outstanding:,.2f}</b>.</p>",
        unsafe_allow_html=True,
    )

    with st.form(f"pay_form_{uid}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            pay_date = st.date_input("Payment Date", value=date.today(), format="DD-MM-YYYY")
            gross_amount = st.number_input(
                "Gross Amount (R)", min_value=0.00, value=float(round(gross, 2)), format="%0.2f",
                help="Pre-filled from Active agreements; override if needed.",
            )
            method = st.selectbox("Payment Method", ["Cash", "EFT", "Cheque", "Other"], index=0)
        with c2:
            # Option C: pre-fill full outstanding, but user can override.
            loan_deduction = st.number_input(
                "Loan Deduction (R)", min_value=0.00,
                value=float(round(min(outstanding, gross), 2)),
                max_value=float(round(outstanding, 2)) if outstanding > 0 else 0.00,
                format="%0.2f",
                help="Pre-filled with the full outstanding loan; reduce if paying less.",
            )
            other_deduction = st.number_input(
                "Other Deduction (R)", min_value=0.00, value=0.00, format="%0.2f",
                help="Optional — e.g. damages, uniform.",
            )
            status = st.selectbox("Status", ["Paid", "Pending", "Cancelled"], index=0)

        # Optional pay period
        with st.expander("📆 Pay period (optional)"):
            p1, p2 = st.columns(2)
            with p1:
                period_start = st.date_input("Period Start", value=None, format="DD-MM-YYYY", key=f"ps_{uid}")
            with p2:
                period_end = st.date_input("Period End", value=None, format="DD-MM-YYYY", key=f"pe_{uid}")

        notes = st.text_input("Notes", placeholder="Optional")

        net_preview = gross_amount - loan_deduction - other_deduction
        st.markdown(
            f"<div style='background:#eef2ff; padding:8px 12px; border-radius:8px;'>"
            f"<b>Net to pay: R {net_preview:,.2f}</b>  "
            f"<span style='color:#6b7280;'>(Gross R {gross_amount:,.2f} "
            f"− Loan R {loan_deduction:,.2f} − Other R {other_deduction:,.2f})</span></div>",
            unsafe_allow_html=True,
        )

        submitted = st.form_submit_button("💵 Record Payment", type="primary", use_container_width=True)

    if submitted:
        if gross_amount <= 0:
            st.error("Gross amount must be greater than R 0.00.")
            return
        if net_preview < 0:
            st.error("Deductions exceed the gross amount — net payment would be negative.")
            return
        abs_user.payments.create_payment(
            pay_date=pay_date,
            gross_amount=gross_amount,
            loan_deduction=loan_deduction,
            other_deduction=other_deduction,
            method=method,
            status=status,
            period_start=period_start,
            period_end=period_end,
            notes=notes,
        )
        st.success(
            f"✅ Payment of R {net_preview:,.2f} recorded"
            + (f" (R {loan_deduction:,.2f} applied to loans)." if loan_deduction > 0 else ".")
        )
        st.rerun()


def _render_payment_history(abs_user, uid):
    """Show all payments made to the staff member, with payslip links."""
    payments = abs_user.payments.get_payments()
    if not payments:
        st.info("No payments recorded for this staff member yet.")
        return

    st.metric("Total paid to date", f"R {abs_user.payments.get_total_paid():,.2f}")

    for p in payments:
        with st.container(border=True):
            st.markdown(
                f"**📅 {p.get('pay_date', '—')}**  ·  "
                f"Net **R {float(p.get('net_amount', 0) or 0):,.2f}**  ·  "
                f"{p.get('method', '—')}  ·  _{p.get('status', '—')}_"
            )
            st.caption(
                f"Gross R {float(p.get('gross_amount', 0) or 0):,.2f} "
                f"− Loan R {float(p.get('loan_deduction', 0) or 0):,.2f} "
                f"− Other R {float(p.get('other_deduction', 0) or 0):,.2f}"
            )
            if p.get("period_start") or p.get("period_end"):
                st.caption(f"Period: {p.get('period_start', '—')} → {p.get('period_end', '—')}")
            if p.get("notes"):
                st.caption(f"📝 {p.get('notes')}")

            # Payslip document links (populated later by the Google Script)
            links = []
            if p.get("pay_pdf"):
                links.append(f"[📄 View PDF]({p.get('pay_pdf')})")
            if p.get("pay_doc"):
                links.append(f"[📝 View Doc]({p.get('pay_doc')})")
            if links:
                st.markdown("  ·  ".join(links))
            else:
                st.caption("🧾 Payslip not generated yet.")


def _render_staff_card(user: dict):
    abs_user   = AbsStaff(abs_user=user)
    staff_cont = Contract(staff=user)
    uid        = user.get("user_id", "")

    with st.container(border=True):
        # ── Header ───────────────────────────────────────────────────────
        name_col, badge_col = st.columns([3, 1])
        with name_col:
            st.markdown(f"### 👤 {user.get('full_names', '—')}")
        with badge_col:
            st.markdown(
                "<span style='background:#2563eb; color:white; padding:2px 10px; "
                "border-radius:12px; font-size:0.75rem; font-weight:600;'>ABS STAFF</span>",
                unsafe_allow_html=True,
            )

        st.markdown(f"**ID:** `{uid}`")
        if user.get("contact_numbers"):
            st.markdown(f"📞 {user.get('contact_numbers')}")
        if user.get("email"):
            st.markdown(f"✉️ {user.get('email')}")

        st.markdown("<hr style='border:1px dotted #d1d5db; margin:6px 0;'>", unsafe_allow_html=True)

        # ── Summary line (salary is based on Active agreements only) ──────
        try:
            st.markdown(abs_user.get_summary())
        except Exception as e:
            st.warning(f"Could not load summary: {e}")

        # ── Action buttons (two rows) ─────────────────────────────────────
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        with r1c1:
            st.button("📅 Days",       key=f"{uid}_view_days",    use_container_width=True)
        with r1c2:
            st.button("📋 Agreements", key=f"{uid}_agreements",   use_container_width=True)
        with r1c3:
            st.button("➕ Add Rate",   key=f"{uid}_contract",     use_container_width=True)
        with r1c4:
            st.button("👤 Profile",    key=f"{uid}_view_profile", use_container_width=True)

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1:
            st.button("💰 Loans",      key=f"{uid}_view_loans",   use_container_width=True)
        with r2c2:
            st.button("💵 Pay",        key=f"{uid}_pay",          use_container_width=True)
        with r2c3:
            st.button("🧾 Payslips",   key=f"{uid}_payhist",      use_container_width=True)
        with r2c4:
            st.button("🗑️ Delete",     key=f"{uid}_delete",       use_container_width=True, type="primary")

        # Track which panel to keep open across reruns
        if "contract_updates" not in st.session_state:
            st.session_state.contract_updates = None

        # Determine active panel
        if st.session_state.get(f"{uid}_view_days"):
            st.session_state[f"{uid}_days_open"] = True

        if st.session_state.get(f"{uid}_days_open"):
            st.session_state.contract_updates = None
            _panel_header("📅 Days Worked")
            try:
                abs_user.print_staff_dates()
            except Exception as e:
                st.error(f"Could not load days: {e}")
            if st.button("✖ Close Days", key=f"{uid}_days_close", use_container_width=True):
                st.session_state[f"{uid}_days_open"] = False
                st.rerun()

        elif st.session_state.get(f"{uid}_view_profile"):
            st.session_state.contract_updates = None
            _panel_header("👤 Staff Profile")
            try:
                st.markdown(abs_user.get_profile())
            except Exception as e:
                st.error(f"Could not load profile: {e}")

        elif (
            st.session_state.get(f"{uid}_contract")
            or st.session_state.contract_updates == f"{uid}_contract"
        ):
            _panel_header("➕ Add New Rate / Contract")
            try:
                staff_cont.set_gui()
                st.session_state.contract_updates = f"{uid}_contract"
            except Exception as e:
                st.error(f"Could not load contract editor: {e}")

        # ── Agreements review: persistent flag so status-change reruns keep
        #    the panel open (mirrors the delete-panel pattern).
        if st.session_state.get(f"{uid}_agreements"):
            st.session_state[f"{uid}_agreements_open"] = True

        if st.session_state.get(f"{uid}_agreements_open"):
            st.session_state.contract_updates = None
            _panel_header("📋 Agreements — Review & Update Status")
            st.caption("Only **Active** agreements are used to calculate salary. "
                       "Set others to Completed/Paused/etc. to keep them for history only.")
            try:
                staff_cont.review_agreements_gui()
            except Exception as e:
                st.error(f"Could not load agreements: {e}")
            if st.button("✖ Close Agreements", key=f"{uid}_agreements_close", use_container_width=True):
                st.session_state[f"{uid}_agreements_open"] = False
                st.rerun()

        # ── Loans review/edit: persistent flag so payment/edit reruns keep
        #    the panel open.
        if st.session_state.get(f"{uid}_view_loans"):
            st.session_state[f"{uid}_loans_open"] = True

        if st.session_state.get(f"{uid}_loans_open"):
            st.session_state.contract_updates = None
            _panel_header("💰 Loans / Advances")
            try:
                _render_loans_panel(abs_user, uid)
            except Exception as e:
                st.error(f"Could not load loans: {e}")
            if st.button("✖ Close Loans", key=f"{uid}_loans_close", use_container_width=True):
                st.session_state[f"{uid}_loans_open"] = False
                st.rerun()

        # ── Pay Staff: persistent flag so the save rerun keeps the panel open.
        if st.session_state.get(f"{uid}_pay"):
            st.session_state[f"{uid}_pay_open"] = True

        if st.session_state.get(f"{uid}_pay_open"):
            st.session_state.contract_updates = None
            _panel_header("💵 Pay Staff Member")
            try:
                _render_pay_panel(abs_user, uid)
            except Exception as e:
                st.error(f"Could not load pay form: {e}")
            if st.button("✖ Close Pay", key=f"{uid}_pay_close", use_container_width=True):
                st.session_state[f"{uid}_pay_open"] = False
                st.rerun()

        # ── Payment history (payslips) ────────────────────────────────────
        if st.session_state.get(f"{uid}_payhist"):
            st.session_state[f"{uid}_payhist_open"] = True

        if st.session_state.get(f"{uid}_payhist_open"):
            st.session_state.contract_updates = None
            _panel_header("🧾 Payment History")
            try:
                _render_payment_history(abs_user, uid)
            except Exception as e:
                st.error(f"Could not load payment history: {e}")
            if st.button("✖ Close History", key=f"{uid}_payhist_close", use_container_width=True):
                st.session_state[f"{uid}_payhist_open"] = False
                st.rerun()

        # ── Delete: use a persistent flag so the confirmation panel survives
        # the rerun that happens when the user clicks "Yes, Delete".
        if st.session_state.get(f"{uid}_delete"):
            st.session_state[f"{uid}_confirm_pending"] = True

        if st.session_state.get(f"{uid}_confirm_pending"):
            st.session_state.contract_updates = None
            _panel_header("🗑️ Delete Staff Member")
            st.warning(
                f"You are about to permanently delete **{user.get('full_names')}** (`{uid}`).\n\n"
                "This will also remove all their attendance records and contract rates. "
                "**This cannot be undone.**"
            )
            confirm_col, cancel_col, _ = st.columns([1, 1, 3])
            with confirm_col:
                if st.button("✅ Yes, Delete", key=f"{uid}_confirm_delete", type="primary", use_container_width=True):
                    st.session_state[f"{uid}_confirm_pending"] = False
                    _delete_staff(uid, user.get("full_names", uid))
            with cancel_col:
                if st.button("✖ Cancel", key=f"{uid}_cancel_delete", use_container_width=True):
                    st.session_state[f"{uid}_confirm_pending"] = False
                    st.rerun()


def _panel_header(title: str):
    st.markdown(
        f"<p style='font-weight:700; font-size:0.95rem; color:#2563eb; "
        f"margin:8px 0 4px 0;'>{title}</p>",
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Staff Register (attendance capture)
# ──────────────────────────────────────────────────────────────────────────────

def staff_register(abs_staff: Users):
    st.markdown("### 📋 Staff Attendance Register")
    st.markdown(
        "<p style='color:#6b7280; font-size:0.88rem;'>"
        "Step 1: Select staff who came to work. Step 2: Fill in their hours and rate.</p>",
        unsafe_allow_html=True,
    )

    staff_list = abs_staff.get_abs_staff()   # group 219 only

    if not staff_list:
        st.info("No staff members found.")
        return

    # ── Step 1: staff selection ──────────────────────────────────────────
    st.markdown("#### Step 1 — Select staff present today")

    # Reset checkboxes if requested
    if st.session_state.get("reset_register"):
        for user in staff_list:
            st.session_state[f"sel_staff_{user.get('user_id')}"] = False
        st.session_state.reset_register = False

    selected_staff = []
    # Display checkboxes in two columns for readability
    chk_cols = st.columns(2)
    for idx, user in enumerate(staff_list):
        with chk_cols[idx % 2]:
            if st.checkbox(
                user.get("full_names", "Unknown"),
                key=f"sel_staff_{user.get('user_id')}",
            ):
                selected_staff.append(user)

    if not selected_staff:
        st.info("Select at least one staff member above to continue.")
        return

    # ── Step 2: capture attendance ───────────────────────────────────────
    st.markdown("<hr style='border:2px dotted #2563eb; margin:1rem 0;'>", unsafe_allow_html=True)
    st.markdown(f"#### Step 2 — Capture hours for {len(selected_staff)} selected staff member{'s' if len(selected_staff) != 1 else ''}")

    updated_register = []
    for u in selected_staff:
        with st.container(border=True):
            name_col, _ = st.columns([3, 1])
            with name_col:
                st.markdown(f"**{u.get('full_names')}**")
            try:
                user_st = StaffAttendence(u)
                user_st.set_gui()
                updated_register.append(user_st)
            except Exception as e:
                st.error(f"Could not load attendance form for {u.get('full_names')}: {e}")

    # ── Action buttons ───────────────────────────────────────────────────
    st.markdown("<hr style='border:1px solid #d1d5db; margin:1rem 0;'>", unsafe_allow_html=True)
    close_col, capture_col, _ = st.columns([1, 1, 3])
    with close_col:
        if st.button("✖ Close", use_container_width=True):
            st.session_state["show_register"] = False
            st.rerun()
    with capture_col:
        if st.button("💾 Capture Attendance", type="primary", use_container_width=True):
            errors = []
            for capt in updated_register:
                try:
                    capt.capture_att()
                except Exception as e:
                    errors.append(str(e))
            if errors:
                for err in errors:
                    st.error(f"Capture error: {err}")
            else:
                st.success(f"✅ Successfully captured attendance for {len(updated_register)} staff member{'s' if len(updated_register) != 1 else ''}.")
                st.session_state.reset_register = True
                st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Add New Staff Member
# ──────────────────────────────────────────────────────────────────────────────

def _next_user_ids() -> tuple:
    """
    Generate the next sequential ABS user_id and user_number by querying the
    users table.  Returns (user_id: str, user_number: int).
    Falls back to ('ABS1001', 1001) if no existing rows are found.
    """
    try:
        result = supabase.table("users").select("user_id, user_number").execute()
        abs_ids      = []
        user_numbers = []
        for row in result.data or []:
            uid = str(row.get("user_id", ""))
            if uid.upper().startswith("ABS"):
                try:
                    abs_ids.append(int(uid[3:]))
                except ValueError:
                    pass
            try:
                un = row.get("user_number")
                if un is not None:
                    user_numbers.append(int(un))
            except (TypeError, ValueError):
                pass
        next_num    = max(abs_ids)      + 1 if abs_ids      else 1001
        next_un     = max(user_numbers) + 1 if user_numbers else next_num
        return f"ABS{next_num}", next_un
    except Exception:
        return "ABS1001", 1001


def _next_user_id() -> str:
    """Convenience wrapper — returns just the user_id string."""
    return _next_user_ids()[0]


def add_staff():
    st.markdown("### ➕ Add New Staff Member")
    st.markdown(
        "<p style='color:#6b7280; font-size:0.88rem;'>"
        "Fields marked <b>*</b> are required. The staff ID is generated automatically.</p>",
        unsafe_allow_html=True,
    )

    # Generate the next ID upfront so we can display it in the form
    next_id = _next_user_id()
    st.info(f"🪪 New Staff ID will be: **{next_id}**")

    with st.form("add_staff_form", clear_on_submit=True):

        st.markdown("#### 👤 Personal Details")
        col1, col2 = st.columns(2)

        with col1:
            full_names = st.text_input(
                "Full Names *",
                placeholder="e.g. John Doe",
            )
            home_location = st.text_input(
                "Home Address *",
                placeholder="e.g. 12 Main St, Johannesburg",
            )
            contact_numbers = st.text_input(
                "Contact Number",
                placeholder="e.g. 071 234 5678",
            )

        with col2:
            email = st.text_input(
                "Email Address",
                placeholder="e.g. john@example.com",
            )
            work_location = st.text_input(
                "Work / Company",
                placeholder="Leave blank to default to Absaluminum (PTY) LTD",
            )
            comments = st.text_input(
                "Comments / Notes",
                placeholder="Optional",
            )

        st.markdown("<hr style='border:1px dotted #d1d5db; margin:0.8rem 0;'>", unsafe_allow_html=True)
        st.markdown("#### 💼 Contract / Rate")
        st.markdown(
            "<p style='color:#6b7280; font-size:0.85rem; margin-top:-0.4rem;'>"
            "Set the initial rate for this staff member.</p>",
            unsafe_allow_html=True,
        )

        r1, r2, r3 = st.columns(3)
        with r1:
            rate_type = st.selectbox(
                "Rate Type *",
                options=["Daily", "Hourly", "Monthly", "Weekly", "Per Job", "Contract"],
                index=0,
            )
        with r2:
            rate_amount = st.number_input(
                "Rate Amount (R) *",
                min_value=0.00,
                format="%0.2f",
            )
        with r3:
            rate_status = st.selectbox(
                "Rate Status *",
                options=["Active", "Completed", "Suspended", "Closed"],
                index=0,
            )

        # Per Job / Contract need an identifier. Shown always inside the form
        # (Streamlit forms can't react mid-render); only used when relevant.
        rate_description = st.text_input(
            "Job Name / Contract Link (only for 'Per Job' or 'Contract')",
            placeholder="e.g. Kitchen windows – 12 Main St  |  or  https://contract-link",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button(
            "💾 Save Staff Member", type="primary", use_container_width=True
        )

    if submitted:
        # ── Validation ────────────────────────────────────────────────────
        errors = []
        if not full_names.strip():
            errors.append("Full Names is required.")
        if not home_location.strip():
            errors.append("Home Address is required.")
        if rate_amount <= 0:
            errors.append("Rate Amount must be greater than R 0.00.")
        if rate_type in ("Per Job", "Contract") and not rate_description.strip():
            label = "job name" if rate_type == "Per Job" else "contract link"
            errors.append(f"Please provide a {label} for the {rate_type} rate.")

        if errors:
            for err in errors:
                st.error(err)
            return

        # ── Build payloads ────────────────────────────────────────────────
        resolved_work = work_location.strip() or "Absaluminum (PTY) LTD"
        new_user_id, new_user_number = _next_user_ids()   # re-query at submit time to avoid race

        new_staff = {
            "user_id":         new_user_id,
            "user_number":     new_user_number,
            "full_names":      full_names.strip(),
            "type":            "ABSALUMINUM",
            "home_location":   home_location.strip(),
            "work_location":   resolved_work,
            "email":           email.strip() or None,
            "contact_numbers": contact_numbers.strip() or None,
            "comments":        comments.strip() or None,
            "group_id":        219,
        }

        new_rate = {
            "staff_id":    new_user_id,
            "rate_type":   rate_type,
            "amount":      rate_amount,
            "status":      rate_status,
            "description": rate_description.strip() or None,
        }

        try:
            supabase.table("users").insert(new_staff).execute()
            supabase.table("StaffRates").insert(new_rate).execute()

            # Refresh in-session caches so the new member & rate show immediately
            init_users()
            # Invalidate staff rate cache so it reloads on next render
            if "init_staffrate" in st.session_state:
                del st.session_state["init_staffrate"]

            st.success(
                f"✅ **{full_names.strip()}** has been added with ID `{new_user_id}` "
                f"and a {rate_type} rate of R {rate_amount:,.2f}."
            )
        except Exception as e:
            st.error(f"Failed to save staff member: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Page entry point
# ──────────────────────────────────────────────────────────────────────────────

user = User()
if user.get_user():
    st.title("👥 Staff Members")
    abs_staff = Users()

    st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0 1rem 0;'>", unsafe_allow_html=True)

    # ── Active-view toggle using segmented_control ────────────────────────
    view = st.segmented_control(
        label="View",
        options=["Staff Summary", "Staff Register", "Add Staff"],
        default="Staff Summary",
        key="staff_view_toggle",
    )

    st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0 1rem 0;'>", unsafe_allow_html=True)

    if view == "Staff Summary":
        try:
            show_staff(abs_staff)
        except Exception as e:
            st.error(f"🚨 Unable to show staff information: {e}")
            print(f"[Staff Members] show_staff error: {e}")

    elif view == "Staff Register":
        try:
            staff_register(abs_staff)
        except Exception as e:
            st.error(f"🚨 Unable to load staff register: {e}")
            print(f"[Staff Members] staff_register error: {e}")

    elif view == "Add Staff":
        try:
            add_staff()
        except Exception as e:
            st.error(f"🚨 Unable to load add staff form: {e}")
            print(f"[Staff Members] add_staff error: {e}")
