from models.Model import *
from models.Qout_Manag_Model import *
import webbrowser


class JobCalender:
    def __init__(self):
        if "view_next_job" not in st.session_state:
            self.update_database()

        if "job_page" not in st.session_state:
            st.session_state.job_page = 0

        if "job_page_size" not in st.session_state:
            st.session_state.job_page_size = 4

        self.reset_pages()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reset_pages(self):
        for key in ("view_next_qoute", "view_prev_qout", "view_next_inv", "view_prev_inv"):
            st.session_state.pop(key, None)

    def update_database(self):
        init_data()
        st.session_state.loaded = True
        st.session_state.jobsummary = []
        self.set_jobsummary(type="qoutation", jobs=st.session_state.qouteSummary)
        self.set_jobsummary(type="invoice",   jobs=st.session_state.invoice_summary)
        st.session_state.view_next_job = st.session_state.jobsummary
        st.session_state.view_prev_job = []

    def set_jobsummary(self, type, jobs):
        """Build a unified job list from quotations and invoices that are InProgress."""
        inv_details_idx = st.session_state.get("_inv_details_idx", {})

        for j in jobs:
            status = str(j.get("status") if type == "qoutation" else j.get("inv_status")).lower()
            if status != "inprogress":
                continue

            job = dict(j)          # work on a copy so we don't mutate session state
            job["type"] = type

            # ── Pull contact info from invoice details ──────────────────
            inv_det = inv_details_idx.get(job.get("inv_numb"), {})
            if not inv_det:
                # Fall back to linear scan if index miss
                for d in st.session_state.invoice_details:
                    if d.get("inv_numb") == job.get("inv_numb"):
                        inv_det = d
                        break

            job["cust_email"]   = inv_det.get("cust_email", "")
            job["cust_numb"]    = inv_det.get("cust_numb", "")
            job["cust_address"] = inv_det.get("cust_address", "")

            # ── Task 1: use real due date, not today ────────────────────
            raw_due = inv_det.get("inv_duedate") or job.get("inv_duedate") or job.get("duedate")
            if raw_due:
                try:
                    if isinstance(raw_due, date):
                        job["duedate"] = raw_due
                    else:
                        job["duedate"] = date.fromisoformat(str(raw_due)[:10])
                except (ValueError, TypeError):
                    job["duedate"] = None
            else:
                job["duedate"] = None

            st.session_state.jobsummary.append(job)

    # ------------------------------------------------------------------
    # Main UI
    # ------------------------------------------------------------------

    def set_job_UI(self):
        if "jobsummary" not in st.session_state:
            self.update_database()

        # ── Task 2: fix infinite loop – clear pending keys after use ───
        if st.session_state.get("update_job"):
            if st.session_state.get("pending_job_qout"):
                pending = st.session_state.pending_job_qout
                # Clear BEFORE rerun so we don't re-enter this branch
                st.session_state.pop("pending_job_qout", None)
                st.session_state.pop("update_job", None)
                qm = Qoute_Manager()
                qm.convert_inv(qout=pending)
                return
            else:
                st.session_state.pop("update_job", None)
                self.update_database()
                st.rerun()

        # ── Page header ─────────────────────────────────────────────────
        hdr_col, refresh_col = st.columns([5, 1])
        with hdr_col:
            st.title("🏗️ Jobs In Progress")
        with refresh_col:
            st.write("")   # vertical spacing
            if st.button("🔄 Refresh", use_container_width=True):
                # Clear view sentinel so update_database runs on next __init__
                st.session_state.pop("view_next_job", None)
                st.rerun()

        data = list(st.session_state.jobsummary)

        # ── Task 3: summary stats bar ────────────────────────────────────
        self._render_stats(data)

        if not data:
            st.info("✅ No jobs currently in progress.")
            return

        # ── Pagination ───────────────────────────────────────────────────
        page      = st.session_state.job_page
        size      = st.session_state.job_page_size
        total     = len(data)
        last_page = max(0, (total - 1) // size)
        start     = page * size
        end       = min(start + size, total)
        page_data = data[start:end]

        # ── Tiles ────────────────────────────────────────────────────────
        for r in range(0, len(page_data), 2):
            cols = st.columns(2, gap="medium")
            for col, job in zip(cols, page_data[r : r + 2]):
                with col:
                    with st.container(border=True):
                        self.set_job_tile(job=job)

        # ── Task 6: pagination bar with page indicator ───────────────────
        self._render_pagination(page, last_page, total, start, end)

    # ------------------------------------------------------------------
    # Stats bar
    # ------------------------------------------------------------------

    def _render_stats(self, data):
        today = date.today()
        total   = len(data)
        overdue = sum(1 for j in data if j.get("duedate") and j["duedate"] < today)
        no_date = sum(1 for j in data if not j.get("duedate"))
        on_time = total - overdue - no_date

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Jobs", total)
        with c2:
            st.metric("On Track", on_time)
        with c3:
            st.metric("⚠️ Overdue", overdue, delta=None)
        with c4:
            st.metric("No Due Date", no_date)

        st.markdown("<hr style='border:1px solid #d1d5db; margin:0.5rem 0 1rem 0;'>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Pagination bar
    # ------------------------------------------------------------------

    def _render_pagination(self, page, last_page, total, start, end):
        st.markdown("<hr style='border:1px solid #d1d5db; margin:1rem 0 0.5rem 0;'>", unsafe_allow_html=True)
        prev_col, info_col, next_col = st.columns([1, 2, 1])

        with prev_col:
            st.button(
                "◀ Prev", key="job_prev_btn",
                on_click=self.prev_job_list,
                disabled=(page == 0),
                type="primary",
                use_container_width=True,
            )
        with info_col:
            st.markdown(
                f"<p style='text-align:center; margin-top:0.5rem; color:#6b7280; font-size:0.9rem;'>"
                f"Page <b>{page + 1}</b> of <b>{last_page + 1}</b> &nbsp;·&nbsp; "
                f"Showing <b>{start + 1}–{end}</b> of <b>{total}</b> jobs</p>",
                unsafe_allow_html=True,
            )
        with next_col:
            st.button(
                "Next ▶", key="job_next_btn",
                on_click=self.next_job_list,
                disabled=(page >= last_page),
                type="primary",
                use_container_width=True,
            )

    def next_job_list(self):
        total = len(st.session_state.get("jobsummary", []))
        last_page = max(0, (total - 1)) // st.session_state.job_page_size
        if st.session_state.job_page < last_page:
            st.session_state.job_page += 1

    def prev_job_list(self):
        if st.session_state.job_page > 0:
            st.session_state.job_page -= 1

    # ------------------------------------------------------------------
    # Job tile  (Tasks 4 & 5)
    # ------------------------------------------------------------------

    def set_job_tile(self, job):
        today     = date.today()
        job_type  = str(job.get("type", "")).lower()
        inv_numb  = job.get("inv_numb")
        duedate   = job.get("duedate")
        is_overdue = duedate and duedate < today

        # ── Coloured type badge ──────────────────────────────────────────
        badge_colour = "#2563eb" if job_type == "invoice" else "#d97706"
        badge_label  = "🔵 INVOICE" if job_type == "invoice" else "🟡 QUOTATION"
        st.markdown(
            f"<span style='background:{badge_colour}; color:white; padding:2px 10px; "
            f"border-radius:12px; font-size:0.78rem; font-weight:600;'>{badge_label}</span>",
            unsafe_allow_html=True,
        )

        # ── Client details ───────────────────────────────────────────────
        st.markdown(f"### {job.get('inv_to', '—')}")
        st.markdown(f"**Invoice #:** `{inv_numb}`")

        if str(job.get("cust_numb", "")).strip():
            st.markdown(f"📞 {job.get('cust_numb')}")
        if str(job.get("cust_email", "")).strip():
            st.markdown(f"✉️ {job.get('cust_email')}")
        if str(job.get("cust_address", "")).strip():
            st.markdown(f"📍 {job.get('cust_address')}")

        # ── Due date chip ────────────────────────────────────────────────
        if duedate:
            days_left = (duedate - today).days
            if is_overdue:
                chip_style = "background:#fee2e2; color:#b91c1c; border:1px solid #fca5a5;"
                chip_text  = f"⚠️ Overdue by {abs(days_left)} day{'s' if abs(days_left) != 1 else ''} — {duedate.strftime('%d %b %Y')}"
            elif days_left <= 3:
                chip_style = "background:#fef9c3; color:#92400e; border:1px solid #fde68a;"
                chip_text  = f"🔔 Due in {days_left} day{'s' if days_left != 1 else ''} — {duedate.strftime('%d %b %Y')}"
            else:
                chip_style = "background:#dcfce7; color:#166534; border:1px solid #86efac;"
                chip_text  = f"✅ Due {duedate.strftime('%d %b %Y')}"
        else:
            chip_style = "background:#f3f4f6; color:#6b7280; border:1px solid #d1d5db;"
            chip_text  = "📅 No due date set"

        st.markdown(
            f"<div style='{chip_style} padding:4px 12px; border-radius:20px; "
            f"font-size:0.82rem; display:inline-block; margin:6px 0 10px 0;'>"
            f"{chip_text}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='border:1px dotted #d1d5db; margin:6px 0;'>", unsafe_allow_html=True)

        # ── Task 5: explicit action buttons ─────────────────────────────
        # Use session state flags keyed by inv_numb so tiles don't interfere.
        action_key   = f"job_action_{inv_numb}"
        confirm_key  = f"job_confirm_{inv_numb}"

        current_action = st.session_state.get(action_key)

        if current_action is None:
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("✔ Complete", key=f"complete_{inv_numb}", use_container_width=True, type="primary"):
                    st.session_state[action_key] = "complete"
                    st.rerun()
            with b2:
                if st.button("✏️ Edit", key=f"edit_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "edit"
                    st.rerun()
            with b3:
                if st.button("📅 Due Date", key=f"due_{inv_numb}", use_container_width=True):
                    st.session_state[action_key] = "duedate"
                    st.rerun()

        elif current_action == "complete":
            # ── Inline confirmation ──────────────────────────────────────
            st.warning(f"Mark **{job.get('inv_to')}** (#{inv_numb}) as complete?")
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button("✔ Yes, complete", key=f"yes_{inv_numb}", type="primary", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    self.close_job(job=job)
            with no_col:
                if st.button("✖ Cancel", key=f"no_{inv_numb}", use_container_width=True):
                    st.session_state.pop(action_key, None)
                    st.rerun()

        elif current_action == "edit":
            st.info("✏️ Edit Job functionality is coming soon.")
            if st.button("← Back", key=f"back_edit_{inv_numb}"):
                st.session_state.pop(action_key, None)
                st.rerun()

        elif current_action == "duedate":
            self.set_duedate(job=job, action_key=action_key)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def close_job(self, job):
        if job.get("type") == "invoice":
            respond = (
                supabase.table("InvoiceSummary")
                .update({"inv_status": "complete"})
                .eq("inv_numb", job.get("inv_numb"))
                .execute()
            )
            if respond.data:
                st.session_state.pop("view_next_job", None)
                st.rerun()
        elif job.get("type") == "qoutation":
            st.session_state.update_job = True
            st.session_state.pending_job_qout = job
            st.rerun()

    def edit_job(self, job):
        pass

    def set_duedate(self, job, action_key):
        new_date = st.date_input(
            "Select new due date",
            value=job.get("duedate") or date.today(),
            format="DD-MM-YYYY",
            key=f"duedate_input_{job.get('inv_numb')}",
        )
        save_col, cancel_col = st.columns(2)
        with save_col:
            if st.button("💾 Save", key=f"save_due_{job.get('inv_numb')}", type="primary", use_container_width=True):
                for j in st.session_state.jobsummary:
                    if j.get("inv_numb") == job.get("inv_numb"):
                        j["duedate"] = new_date
                        break
                st.session_state.pop(action_key, None)
                st.rerun()
        with cancel_col:
            if st.button("✖ Cancel", key=f"cancel_due_{job.get('inv_numb')}", use_container_width=True):
                st.session_state.pop(action_key, None)
                st.rerun()
