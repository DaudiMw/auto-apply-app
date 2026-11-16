import altair as alt
import pandas as pd
import streamlit as st
from data_types import ApplicationStatus, UserProfile
from utils.db import get_user_profile

user_id = st.session_state.get("current_user_id")
profile: UserProfile | None = st.session_state.get("user_profile")

if not profile and user_id:
    profile = get_user_profile(user_id)
    st.session_state["user_profile"] = profile

if not user_id or not profile:
    st.warning("Please complete your profile to view your dashboard analytics.")
    st.page_link("app_pages/profile.py", label="Go to profile setup", icon=":material/arrow_forward:")
    st.stop()

# Header greeting
st.markdown(f"### Welcome back, {profile.name.first_name}")
st.caption(f"Signed in as `{user_id}` • Tracking automated job applications")

# KPI Metrics Grid
c1, c2, c3, c4 = st.columns(4, gap="medium")

total_apps = len(profile.applications)
queued = len([a for a in profile.applications if a.status == ApplicationStatus.QUEUED])
submitted = len([a for a in profile.applications if a.status == ApplicationStatus.SUBMITTED])
interviews = len([a for a in profile.applications if a.status == ApplicationStatus.INTERVIEWING])

with c1:
    with st.container(border=True):
        st.metric("Total tracked", total_apps)
with c2:
    with st.container(border=True):
        st.metric("Queued", queued)
with c3:
    with st.container(border=True):
        st.metric("Submitted", submitted)
with c4:
    with st.container(border=True):
        st.metric("Interviewing", interviews)

# Charts & Breakdown
if profile.applications:
    col_chart, col_recent = st.columns([0.45, 0.55], gap="medium")

    with col_chart:
        with st.container(border=True):
            st.markdown("##### Application pipeline")
            status_counts = {}
            for app in profile.applications:
                status_counts[app.status.value] = status_counts.get(app.status.value, 0) + 1

            df_status = pd.DataFrame(
                list(status_counts.items()),
                columns=["Status", "Count"],
            )

            chart = (
                alt.Chart(df_status)
                .mark_bar(cornerRadius=4)
                .encode(
                    x=alt.X("Count:Q", title="Number of applications"),
                    y=alt.Y("Status:N", sort="-x", title=None),
                    color=alt.Color(
                        "Status:N",
                        legend=None,
                        scale=alt.Scale(scheme="tableau10"),
                    ),
                    tooltip=["Status", "Count"],
                )
                .properties(height=240)
            )
            st.altair_chart(chart)

    with col_recent:
        with st.container(border=True):
            st.markdown("##### Recent activity")
            recent = list(reversed(profile.applications))[:5]
            for r in recent:
                with st.container():
                    st.markdown(f"**{r.title or 'Role'}** @ {r.company_name or 'Company'}")
                    st.caption(f"Status: `{r.status}` • Applied: `{r.date_applied}`")
else:
    with st.container(border=True):
        st.info("No applications submitted or queued yet. Head over to the Applications page to add your first job link.")
        st.page_link("app_pages/applications.py", label="Add an application", icon=":material/add:")
