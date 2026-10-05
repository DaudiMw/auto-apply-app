import streamlit as st
from data_types import Education, EducationFormData




def education_form(education_data: Education | None = None) -> EducationFormData:

    education_form_data = EducationFormData()
    education_container = st.container(key='Education', border=True)
    education_container.subheader('Education')

    if not education_data
