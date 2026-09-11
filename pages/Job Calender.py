from models.User_Model import *
from models.JobCalenderModel import *

user = User()
if user.get_user():
    jobs = JobCalender()
    jobs.set_job_UI()