import streamlit as st
from models.Model import AbsStaff, Contract, StaffAttendence, Users
from models.User_Model import *

abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(page_title="Absaluminum".upper(), page_icon=abs_icon)

def show_staff():
    try:
        for user in abs_staff.get_all_users():
            abs_user = AbsStaff(abs_user=user)
            staff_cont = Contract(staff=user)
            staff_summary = st.container(border=True)

            with staff_summary:
                st.header(user.get('full_names'))
                st.subheader("SUMMARY")
                st.write(abs_user.get_summary())
                staff_cont.print_rate()

                col1, col2, col3, col4 = st.columns(4, border=False)
                with col1:
                    st.button("View Days", key=user.get('user_id') + "view_days")
                with col2:
                    st.button("View Loans", key=user.get('user_id') + "view_loans")
                with col3:
                    st.button("View Profile", key=user.get('user_id') + "view_profile")
                with col4:
                    st.button('Contract', key=user.get('user_id') + "contract")
                
                if not 'contract_updates' in st.session_state:
                    st.session_state.contract_updates = None

                if st.session_state.get(user.get('user_id') + "view_days"):
                    abs_user.print_staff_dates()
                    st.session_state.contract_updates = None
                elif st.session_state.get(user.get('user_id') + "view_profile"):
                    st.write(abs_user.get_profile())
                    st.session_state.contract_updates = None
                elif st.session_state.get(user.get('user_id') + "view_loans"):
                    st.write(abs_user.get_staff_loan())
                    st.session_state.contract_updates = None
                elif st.session_state.get(user.get('user_id') + "contract") or st.session_state.contract_updates == user.get('user_id') + "contract":
                    staff_cont.set_gui()
                    st.session_state.contract_updates = user.get('user_id') + "contract"

            # st.divider()
    except Exception:
        st.error("Unable to show staff information.", icon="🚨")


def staff_register():
    selected_staff = []

    for user in abs_staff.get_all_users():
        if st.session_state.get('reset_register'):
            st.session_state[f"sel_staff_{user.get('user_id')}"] = False
        if st.checkbox(user.get('full_names'), key=f"sel_staff_{user.get('user_id')}"):
            selected_staff.append(user)
    st.session_state.reset_register = False
    if len(selected_staff) > 0:
        st.markdown(
    """
    <hr style="border: 4px dotted red;">
    """,
    unsafe_allow_html=True
    )
        st.subheader("**List of staff that come to work**")
        updated_register = []
        for u in selected_staff:
            user_st = StaffAttendence(u)
            user_st.set_gui()
            updated_register.append(user_st)
            st.divider()
        
        col1, col2 = st.columns(2, border=False)
        with col1:
            if st.button("Close"):
                st.session_state["show register"] = False
                st.rerun()

        with col2:
            if st.button("Capture Staff"):
                for capt in updated_register:
                    capt.capture_att()
                st.write("Successfully captured the staff")
                st.session_state.reset_register = True
                st.rerun()

        st.markdown(
    """
    <hr style="border: 4px dotted red;">
    """,
    unsafe_allow_html=True
    )

user = User()
if user.get_user():
    st.title("Staff Members")
    abs_staff = Users()
    st.divider()

    left, right = st.columns(2, border=False)
    with left:
        st.button("View Staff Summary", key="staff_summary")
        if st.session_state.get("staff_summary"):
            st.session_state["show staff"] = True
            st.session_state["show register"] = False
            
    with right:
        st.button("Staff Register", key= "staff_register")
        if st.session_state.get("staff_register"):
            st.session_state["show staff"] = False
            st.session_state["show register"] = True

    if st.session_state.get("show staff"):
        show_staff()
    elif st.session_state.get("show register"):
        staff_register()

