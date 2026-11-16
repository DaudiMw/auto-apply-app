import logging
from datetime import date
import pandas as pd
import streamlit as st
from pydantic import ValidationError
from data_types import Application, ApplicationStatus, UserProfile
from utils.db import get_user_profile, save_user_profile
from utils.logging_config import hash_id

logger = logging.getLogger(__name__)

user_id = st.session_state.get("current_user_id")

if not user_id:
    st.warning("Please sign in to view applications.")
    st.stop()

profile: UserProfile | None = st.session_state.get("user_profile")
if not profile:
    profile = get_user_profile(user_id)
    st.session_state["user_profile"] = profile

if not profile:
    st.warning("Please configure your profile first.")
    st.page_link("app_pages/profile.py", label="Complete profile", icon=":material/arrow_forward:")
    st.stop()

st.markdown("### Applications tracker")
st.caption("Manage queued job links and track ongoing submission statuses.")

# Add New Job Form
with st.expander(":material/add: Queue new job application", expanded=False):
    with st.form("new_app_form", border=False):
        c_link, c_comp = st.columns([0.6, 0.4], gap="medium")
        with c_link:
            link_input = st.text_input("Job link (URL)", placeholder="https://boards.greenhouse.io/company/jobs/12345")
        with c_comp:
            company_input = st.text_input("Company name", placeholder="e.g. Acme Corp")

        c_title, c_loc, c_pay = st.columns([0.4, 0.3, 0.3], gap="medium")
        with c_title:
            title_input = st.text_input("Job title", placeholder="e.g. Software Engineer")
        with c_loc:
            city_input = st.text_input("City & state", placeholder="e.g. Austin, TX")
        with c_pay:
            salary_input = st.number_input("Yearly salary ($)", min_value=0, step=5000, value=0)

        submitted = st.form_submit_button("Add to queue", icon=":material/queue:")

        if submitted:
            if not link_input.strip():
                st.error("Please enter a valid job URL.")
            else:
                try:
                    new_app = Application(
                        link=link_input.strip(),
                        date_applied=date.today(),
                        status=ApplicationStatus.QUEUED,
                        company_name=company_input.strip() or None,
                        title=title_input.strip() or None,
                        office_city=city_input.strip() or None,
                        pay_yearly=salary_input if salary_input > 0 else None,
                    )
                    profile.applications.append(new_app)
                    save_user_profile(profile)
                    logger.info("Application queued", extra={"user": hash_id(user_id), "application_id": new_app.application_id})
                    st.session_state["user_profile"] = profile
                    st.toast("Application added to queue!", icon=":material/rocket_launch:")
                    st.rerun()
                except ValidationError as ve:
                    logger.warning("Application validation failed", extra={"user": hash_id(user_id), "error_count": ve.error_count()})
                    st.error(f"Validation error: {ve}")

# Filter Controls with st.segmented_control
filter_options = ["All"] + [s.value for s in ApplicationStatus]
selected_filter = st.segmented_control(
    "Filter by status",
    options=filter_options,
    default="All",
    label_visibility="collapsed",
)

# Filter applications
apps_to_display = profile.applications
if selected_filter and selected_filter != "All":
    apps_to_display = [a for a in profile.applications if a.status.value == selected_filter]

st.markdown(f"**Showing {len(apps_to_display)} application(s)**")

if not apps_to_display:
    st.info("No applications match the selected filter.")
else:
    for idx, app in enumerate(reversed(apps_to_display)):
        # Match real index in profile
        real_idx = profile.applications.index(app)

        with st.container(border=True):
            col_details, col_status, col_actions = st.columns([0.5, 0.35, 0.15], gap="medium")

            with col_details:
                st.markdown(f"##### {app.title or 'Role'} @ {app.company_name or 'Company'}")
                st.caption(f":material/link: [Open job posting]({app.link}) • Applied: `{app.date_applied}`")

            with col_status:
                current_st = app.status
                status_opts = [current_st] + [s for s in ApplicationStatus.user_editable() if s != current_st]
                selected_st = st.selectbox(
                    "Status",
                    options=status_opts,
                    key=f"status_sel_{app.application_id}",
                    label_visibility="collapsed",
                )
                if selected_st != current_st:
                    profile.applications[real_idx].status = selected_st
                    save_user_profile(profile)
                    logger.info(
                        "Application status changed",
                        extra={"user": hash_id(user_id), "application_id": app.application_id, "status": selected_st.value},
                    )
                    st.session_state["user_profile"] = profile
                    st.toast(f"Status updated to {selected_st.value}", icon=":material/sync:")
                    st.rerun()

            with col_actions:
                if st.button("Delete", icon=":material/delete:", key=f"del_btn_{app.application_id}"):
                    profile.applications.pop(real_idx)
                    save_user_profile(profile)
                    logger.info("Application deleted", extra={"user": hash_id(user_id), "application_id": app.application_id})
                    st.session_state["user_profile"] = profile
                    st.toast("Application removed", icon=":material/delete:")
                    st.rerun()
