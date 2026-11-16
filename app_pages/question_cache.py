import logging
import streamlit as st
from data_types import UserProfile
from utils.db import get_user_profile, save_user_profile, upsert_cached_question
from utils.logging_config import hash_id

logger = logging.getLogger(__name__)

user_id = st.session_state.get("current_user_id")

if not user_id:
    st.warning("Please sign in to view screening questions.")
    st.stop()

profile: UserProfile | None = st.session_state.get("user_profile")
if not profile:
    profile = get_user_profile(user_id)
    st.session_state["user_profile"] = profile

if not profile:
    st.warning("Please configure your profile first.")
    st.stop()

st.markdown("### Screening question memory")
st.caption(
    "Pre-configured answers for common ATS screening prompts (e.g. work authorization, visa status, years of experience)."
)

# Add Question Form
with st.expander(":material/add: Add screening question & answer", expanded=False):
    with st.form("new_q_form", border=False):
        q_val = st.text_input("Screening question", placeholder="e.g. Will you require employer sponsorship now or in the future?")
        a_val = st.text_input("Answer to provide", placeholder="e.g. No")

        if st.form_submit_button("Save answer", icon=":material/save:"):
            if q_val.strip() and a_val.strip():
                upsert_cached_question(user_id, q_val.strip(), a_val.strip())
                logger.info("Screening answer saved", extra={"user": hash_id(user_id)})
                profile = get_user_profile(user_id) or profile
                st.session_state["user_profile"] = profile
                st.toast("Question saved to memory!", icon=":material/save:")
                st.rerun()
            else:
                st.error("Please fill in both the question and answer.")

# Search questions
search_query = st.text_input("Search questions", placeholder="Filter by keyword...", label_visibility="collapsed")

matching_cache = profile.cache
if search_query.strip():
    q_lower = search_query.lower()
    matching_cache = [c for c in profile.cache if q_lower in c.question.lower() or q_lower in c.answer.lower()]

st.markdown(f"**Showing {len(matching_cache)} saved question(s)**")

if not matching_cache:
    st.info("No matching questions in memory.")
else:
    for idx, item in enumerate(matching_cache):
        real_idx = profile.cache.index(item)
        with st.container(border=True):
            col_q, col_a, col_del = st.columns([0.5, 0.38, 0.12], gap="medium")
            with col_q:
                st.markdown(f"**Q:** {item.question}")
                st.caption(f"Used in {item.hits} application(s)")
            with col_a:
                new_ans = st.text_input("Answer", value=item.answer, key=f"q_ans_{idx}", label_visibility="collapsed")
                if new_ans != item.answer:
                    profile.cache[real_idx].answer = new_ans
                    save_user_profile(profile)
                    logger.info("Screening answer updated", extra={"user": hash_id(user_id)})
                    st.session_state["user_profile"] = profile
                    st.toast("Answer updated!", icon=":material/edit:")
            with col_del:
                if st.button("Delete", icon=":material/delete:", key=f"del_q_btn_{idx}"):
                    profile.cache.pop(real_idx)
                    save_user_profile(profile)
                    logger.info("Screening answer deleted", extra={"user": hash_id(user_id)})
                    st.session_state["user_profile"] = profile
                    st.toast("Question deleted", icon=":material/delete:")
                    st.rerun()
