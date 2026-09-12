import streamlit as st
from models.Model import AbsStaff, Contract, StaffAttendence, Users, inject_css
from models.User_Model import *

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

        # ── Summary line ─────────────────────────────────────────────────
        try:
            st.markdown(abs_user.get_summary())
        except Exception as e:
            st.warning(f"Could not load summary: {e}")

        # ── Contract / rates ─────────────────────────────────────────────
        try:
            staff_cont.print_rate()
        except Exception as e:
            st.warning(f"Could not load contract: {e}")

        # ── Action buttons ────────────────────────────────────────────────
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            st.button("📅 Days",    key=f"{uid}_view_days",    use_container_width=True)
        with b2:
            st.button("💰 Loans",   key=f"{uid}_view_loans",   use_container_width=True)
        with b3:
            st.button("👤 Profile", key=f"{uid}_view_profile", use_container_width=True)
        with b4:
            st.button("📄 Contract",key=f"{uid}_contract",     use_container_width=True)

        # Track which panel to keep open across reruns
        if "contract_updates" not in st.session_state:
            st.session_state.contract_updates = None

        # Determine active panel
        if st.session_state.get(f"{uid}_view_days"):
            st.session_state.contract_updates = None
            _panel_header("📅 Days Worked")
            try:
                abs_user.print_staff_dates()
            except Exception as e:
                st.error(f"Could not load days: {e}")

        elif st.session_state.get(f"{uid}_view_profile"):
            st.session_state.contract_updates = None
            _panel_header("👤 Staff Profile")
            try:
                st.markdown(abs_user.get_profile())
            except Exception as e:
                st.error(f"Could not load profile: {e}")

        elif st.session_state.get(f"{uid}_view_loans"):
            st.session_state.contract_updates = None
            _panel_header("💰 Loans")
            try:
                result = abs_user.get_staff_loan()
                st.info(result)
            except Exception as e:
                st.error(f"Could not load loan info: {e}")

        elif (
            st.session_state.get(f"{uid}_contract")
            or st.session_state.contract_updates == f"{uid}_contract"
        ):
            _panel_header("📄 Contract / Rates")
            try:
                staff_cont.set_gui()
                st.session_state.contract_updates = f"{uid}_contract"
            except Exception as e:
                st.error(f"Could not load contract editor: {e}")


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
        options=["Staff Summary", "Staff Register"],
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
