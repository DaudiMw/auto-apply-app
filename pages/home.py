
import streamlit as st
from datetime import date

def HomePage() -> None:
    
    st.title("Apply to Jobs Automatically")

    st.header("Resume Information")

    if not st.user.is_logged_in:
        st.button(label='login with Google', on_click=st.login)

    else:

        st.button(label='Logout', on_click=st.logout)

    # sample code for fetching the resume data from an unstructured database on aws.

    resume_data = None
    # resume_data = unstructured_database_aws.get(st.user.get('user_id'))

    if not resume_data:

        


    

        # resume_information = get_resume_information(st.user())

    # if not resume_information:
    #     st.write("Resume information not found.")
    #     st.write("Create one: ")

    #     st.form()
