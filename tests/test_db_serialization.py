from datetime import date
from data_types import (
    Name, Address, Education, Experience, Project,
    ResumeData, Application, ApplicationStatus, UserProfile, CachedQuestion
)
from utils.db import profile_to_item, item_to_profile


def test_profile_roundtrip_serialization():
    edu = Education(
        institution_name="Stanford University",
        degree_type="Master of Science",
        degree_field="Computer Science",
        start_date=date(2018, 9, 1),
        end_date=date(2020, 6, 15),
    )
    exp = Experience(
        employer_name="Google",
        title="Software Engineer",
        city="Mountain View",
        state="CA",
        country="USA",
        description="Backend distributed systems",
        start_date=date(2020, 7, 1),
        end_date=date(2023, 8, 1),
    )
    proj = Project(
        project_name="AI Bot",
        project_link="https://github.com/example/bot",
        description="Built automation tool",
        start_date=date(2023, 9, 1),
    )
    resume = ResumeData(
        education=[edu],
        experience=[exp],
        projects=[proj],
        skills=["Python", "Streamlit", "AWS", "Playwright"],
    )
    addr = Address(
        street="456 Elm St",
        apt_number="Suite 100",
        city="San Jose",
        state="CA",
        country="USA",
        zip_code="95112",
    )
    app = Application(
        link="https://boards.greenhouse.io/job/123",
        date_applied=date(2024, 1, 10),
        status=ApplicationStatus.SUBMITTED,
        company_name="Stripe",
        title="Python Engineer",
        pay_yearly=150000,
    )
    cache_q = CachedQuestion(
        question="Are you legally authorized to work in the United States?",
        answer="Yes",
        hits=5,
    )
    profile = UserProfile(
        user_id="google-oauth2|123456789",
        name=Name(first_name="Alice", last_name="Smith"),
        birth_date=date(1995, 5, 20),
        email="alice.smith@example.com",
        phone="+14155552671",
        address=addr,
        resume_data=resume,
        cache=[cache_q],
        applications=[app],
    )

    # Convert to DynamoDB item dict
    item = profile_to_item(profile)
    assert item["PK"] == "google-oauth2|123456789"
    assert item["name"]["first_name"] == "Alice"
    assert item["applications"][0]["status"] == "SUBMITTED"
    assert item["resume_data"]["skills"] == ["Python", "Streamlit", "AWS", "Playwright"]

    # Reconstruct back into UserProfile
    reconstructed = item_to_profile(item)
    assert reconstructed.user_id == profile.user_id
    assert reconstructed.name.first_name == profile.name.first_name
    assert reconstructed.name.last_name == profile.name.last_name
    assert reconstructed.birth_date == profile.birth_date
    assert reconstructed.email == profile.email
    assert reconstructed.phone == profile.phone
    assert len(reconstructed.resume_data.education) == 1
    assert reconstructed.resume_data.education[0].institution_name == "Stanford University"
    assert len(reconstructed.applications) == 1
    assert reconstructed.applications[0].status == ApplicationStatus.SUBMITTED
    assert len(reconstructed.cache) == 1
    assert reconstructed.cache[0].hits == 5
