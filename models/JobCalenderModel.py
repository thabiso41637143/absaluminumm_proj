from models.Model import *
from models.Qout_Manag_Model import *
import webbrowser


class JobCalender:
    def __init__(self):
        # Use "view_next_job" as the sentinel — if it's absent the full data
        # load hasn't happened yet for this page visit.
        if "view_next_job" not in st.session_state:
            self.update_database()

        if "job_page" not in st.session_state:
            st.session_state.job_page = 0

        if "job_page_size" not in st.session_state:
            st.session_state.job_page_size = 4

        self.reset_pages()

    def reset_pages(self):
        if "view_next_qoute" in st.session_state:
            st.session_state.pop("view_next_qoute")
        if "view_prev_qout" in st.session_state:
            st.session_state.pop("view_prev_qout")

        if "view_next_inv" in st.session_state:
            st.session_state.pop("view_next_inv")
        if "view_prev_inv" in st.session_state:
            st.session_state.pop("view_prev_inv")
    def update_database(self):
        init_data()
        st.session_state.loaded = True

        st.session_state.jobsummary = []

        self.set_jobsummary(type="qoutation",jobs=st.session_state.qouteSummary)
        self.set_jobsummary(type="invoice",jobs=st.session_state.invoice_summary)

        st.session_state.view_next_job = st.session_state.jobsummary
        st.session_state.view_prev_job = []

    def set_jobsummary(self, type, jobs):
        for j in jobs:
            status = str(j.get('status')).lower() if type == 'qoutation' else str(j.get('inv_status')).lower()
            if status == 'inprogress':
                for inv_det in st.session_state.invoice_details:
                    if inv_det.get('inv_numb') == j.get('inv_numb'):
                        j['cust_email'] = inv_det.get('cust_email')
                        j['cust_numb'] = inv_det.get('cust_numb')
                        j['cust_address'] = inv_det.get('cust_address')
                j['duedate'] = date.today()
                j["type"] = type
                st.session_state.jobsummary.append(j)

    def set_job_UI(self):
        # Ensure jobsummary exists even if the user navigated here mid-session.
        if "jobsummary" not in st.session_state:
            self.update_database()

        if st.session_state.get('update_job'):
            if st.session_state.get("pending_job_qout"):
                # Re-instantiate fresh so no stale object lives in session state.
                qm = Qoute_Manager()
                qm.convert_inv(qout=st.session_state.pending_job_qout)
            else:
                st.session_state.update_job = False
                self.update_database()
                st.rerun()
        else:
            st.title("List of Jobs that are in progress")
            data = list(st.session_state.jobsummary)

            if not data:
                st.info("There are no jobs currently in progress.")
                return

            page = st.session_state.job_page
            size = st.session_state.job_page_size

            start = page * size
            end = start + size
            page_data = data[start:end]

            for r in range(0, len(page_data), 2):
                cols = st.columns(2, border=True)
                for c, job in zip(cols, page_data[r:r+2]):
                    with c:
                        self.set_job_tile(job=job)

            self.set_bottom_buttons()

    def set_bottom_buttons(self):
        total = len(st.session_state.get('jobsummary', []))
        last_page = max((total - 1), 0) // st.session_state.job_page_size

        prev_button, next_button = st.columns(2)
        with prev_button:
            st.button("<< Prev", on_click=self.prev_job_list,
                      disabled=st.session_state.job_page == 0, type="primary")
        with next_button:
            st.button("Next >>", on_click=self.next_job_list,
                      disabled=st.session_state.job_page >= last_page, type="primary")

    def update_payment(self, inv):
        pass

    def next_job_list(self):
        total = len(st.session_state.get('jobsummary', []))
        total_pages = max((total - 1), 0) // st.session_state.job_page_size
        if st.session_state.job_page < total_pages:
            st.session_state.job_page += 1

    def prev_job_list(self):
        if st.session_state.job_page > 0:
            st.session_state.job_page -= 1

    def set_job_tile(self, job):
        st.subheader(str(job.get("type")).upper())
        st.write(f"**Invoice Number:** {job.get('inv_numb')}")
        st.write(f"**Invoice To:** {job.get('inv_to')}")

        if str(job.get('cust_numb')).strip() != "":
            st.write(f"**Contacts:** {job.get('cust_numb')}")

        if str(job.get('cust_email')).strip() != "":
            st.write(f"**E-mail:** {job.get('cust_email')}")

        if str(job.get('cust_address')).strip() != "":
            st.write(f"Address")
            st.write(job.get('cust_address'))
        
        if job.get('duedate'):
            st.write(f"**Due date:** {job.get('duedate')}")

        st.markdown(
"""
<hr style="border: 1px dotted red;">
"""
        , unsafe_allow_html=True )
        option = st.radio(label="**Select Option**",options=["Mark as complete", "Edit Job", "Set due date"],
                        key='radio_'+ str(job.get("inv_numb")), index=None)
        if option == "Mark as complete":
            self.close_job(job=job)
        elif option == "Edit Job":
            self.edit_job(job=job)
        elif option == "Set due date":
            self.set_duedate(job=job)
    
    def close_job(self, job):
        if job.get('type') == 'invoice':
            respond = supabase.table("InvoiceSummary").update({"inv_status": "complete"})\
                .eq("inv_numb", job.get("inv_numb")).execute()
            if respond.data:
                self.update_database()
                st.rerun()
        elif job.get('type') == 'qoutation':
            # Store only the plain data dict, not a class instance, to avoid
            # session-state serialisation issues across reruns.
            st.session_state.update_job = True
            st.session_state.pending_job_qout = job
            st.rerun()

    def edit_job(self, job):
        pass

    def set_duedate(self, job):
        """Prompt for a new due date and persist it into the session-state list."""
        new_date = st.date_input(
            "Set due date",
            value=job.get('duedate', date.today()),
            format="DD-MM-YYYY",
            key=f"duedate_{job.get('inv_numb')}",
        )
        if st.button("Save due date", key=f"save_due_{job.get('inv_numb')}"):
            # Update the record inside the shared session-state list so the
            # change survives the next Streamlit rerun.
            for j in st.session_state.jobsummary:
                if j.get('inv_numb') == job.get('inv_numb'):
                    j['duedate'] = new_date
                    break
            st.rerun()

