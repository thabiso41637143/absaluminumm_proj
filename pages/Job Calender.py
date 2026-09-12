from models.User_Model import *
from models.JobCalenderModel import *
from models.Model import inject_css

abs_icon = open("Images/AbsAppIcon.png", "rb").read()
st.set_page_config(page_title="Job Calendar | Absaluminum".upper(), page_icon=abs_icon, layout="wide")

inject_css()

user = User()
if user.get_user():
    jobs = JobCalender()
    jobs.set_job_UI()
