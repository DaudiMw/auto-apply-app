import streamlit as st
from datetime import date
from data_types import UserProfile
from components.address_form import address_form


def info_form(user_form: UserProfile | None = None):

    name = user_form.name if user_form else None
    address = user_form.address if user_form else None
    resume_data = user_form.resume_data if user_form else None

    with st.form("Input information"):

        first_name = st.text_input('First Name', value=name.first_name if name else "")
        middle_name = st.text_input('Middle Name', value=name.middle_name if name else "")
        last_name = st.text_input('Last Name', value=name.last_name if name else "")
        birth_date = st.date_input('Date of Birth (Select min year to see years that come before.)', min_value=date(1900, 1, 1), max_value=date(2013, 1, 1))


        address = address_form(address)
        
        st.form_submit_button('Save resume information.')



