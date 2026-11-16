import logging
import streamlit as st
from components.resume_form import render_user_profile_form
from data_types import UserProfile
from utils.db import get_user_profile, save_user_profile
from utils.logging_config import hash_id
from utils.upload_resume import parse_resume_file

logger = logging.getLogger(__name__)

user_id = st.session_state.get("current_user_id")

if not user_id:
    st.warning("Please sign in to view and edit your profile.")
    st.stop()

# Load profile from state or DB
profile: UserProfile | None = st.session_state.get("user_profile")
if not profile:
    profile = get_user_profile(user_id)
    st.session_state["user_profile"] = profile

st.markdown("### Profile & resume builder")
st.caption("Manage your personal details, work history, and education used by the auto-apply engine.")

# Resume Auto-fill Tool
with st.expander(":material/description: Auto-fill from resume file", expanded=False):
    uploaded_file = st.file_uploader(
        "Upload PDF or text resume",
        type=["pdf", "docx", "txt"],
        help="Extracts contact information and skills automatically",
    )
    if uploaded_file is not None:
        if st.button("Parse resume", icon=":material/document_scanner:"):
            with st.spinner("Extracting content..."):
                parsed = parse_resume_file(uploaded_file)
                st.session_state["parsed_resume_data"] = parsed
                logger.info("Resume parsed", extra={"user": hash_id(user_id), "skills_found": len(parsed.get("skills", []))})
                st.success(
                    f"Extracted {len(parsed.get('skills', []))} skills and contact information. Review the form below to confirm."
                )

# Form Rendering
updated_profile = render_user_profile_form(profile)
if updated_profile:
    saved = save_user_profile(updated_profile)
    st.session_state["user_profile"] = updated_profile
    if saved:
        st.toast("Profile saved successfully!", icon=":material/check_circle:")
        st.success("Your profile details have been saved to the database.")
    else:
        logger.warning("Profile persisted to session only", extra={"user": hash_id(user_id)})
        st.toast("Profile saved to session.", icon=":material/info:")
        st.info("Saved to active session. (AWS DynamoDB write unavailable in local mode).")
