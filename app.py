import logging
import streamlit as st
from utils.db import get_user_profile
from utils.logging_config import hash_id, setup_logging

setup_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Auto Apply",
    page_icon=":material/work:",
    layout="wide",
)

# Initialize Session State
if "current_user_id" not in st.session_state:
    st.session_state["current_user_id"] = None

# Detect user from Streamlit native auth if available
if hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
    st.session_state["current_user_id"] = getattr(st.user, "user_id", None) or getattr(st.user, "email", None)

user_id = st.session_state.get("current_user_id")

if user_id and not st.session_state.get("_login_logged"):
    logger.info("User session started", extra={"user": hash_id(user_id)})
    st.session_state["_login_logged"] = True

# Top-level / Sidebar Auth controls
with st.sidebar:
    st.markdown("### :material/smart_toy: Auto Apply")
    if user_id:
        st.caption(f"Logged in as **{user_id}**")
        if hasattr(st, "logout") and hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
            st.button("Log out", icon=":material/logout:", on_click=st.logout)
        else:
            if st.button("Log out", icon=":material/logout:"):
                logger.info("User logged out", extra={"user": hash_id(user_id)})
                st.session_state["_login_logged"] = False
                st.session_state["current_user_id"] = None
                st.session_state["user_profile"] = None
                st.rerun()
    else:
        st.warning("Not signed in")

# If unauthenticated, show clean sign-in screen
if not user_id:
    st.markdown("## Automated Job Applications")
    st.caption("Sign in to configure your resume details, review screening questions, and track automated applications.")

    with st.container(border=True):
        st.markdown("#### Authentication")
        if hasattr(st, "login"):
            st.button("Sign in with Google", icon=":material/login:", on_click=st.login, type="primary")
        else:
            dev_email = st.text_input("Developer Email (Local Mode)", value="user@example.com")
            if st.button("Sign in", icon=":material/login:", type="primary"):
                st.session_state["current_user_id"] = dev_email
                st.rerun()
    st.stop()

# Define Modern Streamlit Navigation
nav = st.navigation(
    [
        st.Page("app_pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
        st.Page("app_pages/profile.py", title="Profile & Resume", icon=":material/account_circle:"),
        st.Page("app_pages/applications.py", title="Applications", icon=":material/work:"),
        st.Page("app_pages/question_cache.py", title="Screening Memory", icon=":material/quiz:"),
    ],
    position="sidebar",
)

nav.run()
