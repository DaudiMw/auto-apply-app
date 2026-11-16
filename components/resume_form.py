from datetime import date
from typing import Optional
import streamlit as st
from pydantic import ValidationError
from components.generic_form import generic_form, dynamic_list_form
from data_types import (
    Address, AddressFormData, Education, EducationFormData,
    Experience, ExperienceFormData, Name, Project, ProjectFormData,
    ResumeData, UserProfile
)
from utils.validation import validate_address


def render_user_profile_form(profile: Optional[UserProfile] = None) -> Optional[UserProfile]:
    """Renders a comprehensive user profile and resume editor."""
    st.markdown("### :material/person: Personal Details")
    c1, c2, c3 = st.columns(3)
    with c1:
        first_name = st.text_input("First Name", value=profile.name.first_name if profile else "", key="prof_fn")
    with c2:
        middle_name = st.text_input("Middle Name", value=(profile.name.middle_name or "") if profile else "", key="prof_mn")
    with c3:
        last_name = st.text_input("Last Name", value=profile.name.last_name if profile else "", key="prof_ln")

    c_bday, c_email, c_phone = st.columns(3)
    with c_bday:
        birth_date = st.date_input(
            "Date of Birth",
            value=profile.birth_date if profile else date(1998, 1, 1),
            min_value=date(1940, 1, 1),
            max_value=date(2010, 1, 1),
            key="prof_bday",
        )
    with c_email:
        email = st.text_input(
            "Email Address",
            value=profile.email if profile else (getattr(st.user, "email", "") or ""),
            key="prof_email",
        )
    with c_phone:
        phone = st.text_input(
            "Phone Number (US format e.g. +12025550123)",
            value=str(profile.phone) if profile else "",
            key="prof_phone",
        )

    st.markdown("### :material/home: Address")
    address_form_obj: AddressFormData = generic_form(
        form_data_model=AddressFormData,
        input_model=profile.address if profile else None,
        key_prefix="user_address",
        title="",
    )

    st.markdown("### :material/school: Education")
    current_edus = profile.resume_data.education if profile else []
    edu_forms = dynamic_list_form(
        item_model=EducationFormData,
        current_items=current_edus,
        key_prefix="user_edu",
        item_title="Education",
    )

    st.markdown("### :material/work: Work Experience")
    current_exps = (profile.resume_data.experience or []) if profile else []
    exp_forms = dynamic_list_form(
        item_model=ExperienceFormData,
        current_items=current_exps,
        key_prefix="user_exp",
        item_title="Experience",
    )

    st.markdown("### :material/rocket_launch: Projects")
    current_projs = (profile.resume_data.projects or []) if profile else []
    proj_forms = dynamic_list_form(
        item_model=ProjectFormData,
        current_items=current_projs,
        key_prefix="user_proj",
        item_title="Project",
    )

    st.markdown("### :material/build: Skills")
    skills_raw = st.text_input(
        "Skills (comma-separated)",
        value=", ".join(profile.resume_data.skills) if (profile and profile.resume_data.skills) else "",
        key="prof_skills",
    )
    skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]

    if st.button(":material/save: Save Profile", type="primary", use_container_width=True):
        # 1. Validate Name
        if not first_name.strip() or not last_name.strip():
            st.error("Please provide both First Name and Last Name.")
            return None

        # 2. Validate Address
        addr_dict = address_form_obj.model_dump()
        if not validate_address(addr_dict):
            st.error("Please provide a valid complete address (Street, City, State, Country, and a 5-digit Zip Code).")
            return None

        # 3. Build & Validate Sub-models
        try:
            name_obj = Name(first_name=first_name.strip(), middle_name=middle_name.strip() or None, last_name=last_name.strip())
            address_obj = Address(**addr_dict)

            valid_edus: list[Education] = []
            for e in edu_forms:
                e_dict = {k: v for k, v in e.model_dump().items() if v is not None and v != ""}
                if e_dict.get("institution_name") and e_dict.get("degree_type") and e_dict.get("start_date"):
                    valid_edus.append(Education(**e_dict))

            if not valid_edus:
                st.error("Please fill in at least one valid Education entry (School Name, Degree Type, Start Date).")
                return None

            valid_exps: list[Experience] = []
            for exp in exp_forms:
                exp_dict = {k: v for k, v in exp.model_dump().items() if v is not None and v != ""}
                if exp_dict.get("employer_name") and exp_dict.get("title") and exp_dict.get("description") and exp_dict.get("city") and exp_dict.get("start_date"):
                    valid_exps.append(Experience(**exp_dict))

            valid_projs: list[Project] = []
            for p in proj_forms:
                p_dict = {k: v for k, v in p.model_dump().items() if v is not None and v != ""}
                if p_dict.get("project_name") and p_dict.get("description") and p_dict.get("start_date"):
                    valid_projs.append(Project(**p_dict))

            resume_data_obj = ResumeData(
                education=valid_edus,
                experience=valid_exps or None,
                projects=valid_projs or None,
                skills=skills_list or None,
            )

            user_id_val = getattr(st.user, "user_id", None) or getattr(st.user, "email", None) or (profile.user_id if profile else "local_user")

            updated_profile = UserProfile(
                user_id=user_id_val,
                name=name_obj,
                birth_date=birth_date,
                email=email.strip(),
                phone=phone.strip(),
                address=address_obj,
                resume_data=resume_data_obj,
                cache=profile.cache if profile else [],
                applications=profile.applications if profile else [],
            )
            return updated_profile

        except ValidationError as ve:
            st.error(f"Validation Error: {ve}")
            return None

    return None
