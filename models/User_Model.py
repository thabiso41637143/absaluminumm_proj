from models.Model import *

class User:
    def __init__(self):
        pass

    def get_user(self) -> dict:
        if st.session_state.get("user"):
            return st.session_state.user["username"]
        self.login()

    def login(self):
        user_cont = st.container(border=True)
        with user_cont:
            user_name = st.text_input(label="User Name")
            password = st.text_input("Password", type="password")

            if st.button("Login"):
                try:
                    user_details = (
                        supabase.table('Profiles')
                        .select('username', 'role', 'email')
                        .eq('username', user_name)
                        .execute()
                    )
                    supabase.auth.sign_in_with_password({
                        "email": user_details.data[0].get("email"),
                        "password": password,
                    })
                    st.session_state.user = {
                        'user_role': user_details.data[0].get("role"),
                        "username": user_details.data[0].get("username"),
                    }
                    st.rerun()
                except Exception:
                    st.error("Invalid credentials")

    def logout(self):
        """Sign out from Supabase and clear the local session."""
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        st.session_state.pop("user", None)
        st.rerun()

    def get_user_role(self):
        if st.session_state.get("user"):
            # Key stored at login is 'user_role', not 'role'.
            return st.session_state.user["user_role"]
        self.login()
