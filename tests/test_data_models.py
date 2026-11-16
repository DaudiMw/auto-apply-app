from datetime import date, timedelta
import pytest
from pydantic import ValidationError
from data_types import (
    Name, Address, Education, Experience, Project,
    ResumeData, Application, ApplicationStatus, UserProfile, CachedQuestion
)


def test_name_validation():
    name = Name(first_name="Jane", last_name="Doe")
    assert name.first_name == "Jane"
    assert name.middle_name is None
    assert name.last_name == "Doe"


def test_address_validation():
    addr = Address(
        street="123 Main St",
        apt_number="4B",
        city="New York",
        state="NY",
        country="USA",
        zip_code="10001",
    )
    assert addr.zip_code == "10001"

    # Zip+4 format
    addr2 = Address(
        street="123 Main St",
        city="New York",
        state="NY",
        country="USA",
        zip_code="10001-1234",
    )
    assert addr2.zip_code == "10001-1234"

    # Invalid zip code
    with pytest.raises(ValidationError):
        Address(
            street="123 Main St",
            city="New York",
            state="NY",
            country="USA",
            zip_code="invalid-zip",
        )


def test_education_validation():
    edu = Education(
        institution_name="MIT",
        degree_type="Bachelor of Science",
        degree_field="Computer Science",
        start_date=date(2018, 9, 1),
        end_date=date(2022, 5, 30),
    )
    assert edu.institution_name == "MIT"

    # Start date in future
    future_date = date.today() + timedelta(days=30)
    with pytest.raises(ValidationError):
        Education(
            institution_name="MIT",
            degree_type="BS",
            start_date=future_date,
        )

    # End date before start date
    with pytest.raises(ValidationError):
        Education(
            institution_name="MIT",
            degree_type="BS",
            start_date=date(2020, 1, 1),
            end_date=date(2019, 1, 1),
        )


def test_experience_validation():
    exp = Experience(
        employer_name="Acme Corp",
        title="Software Engineer",
        city="San Francisco",
        state="CA",
        country="USA",
        description="Built web applications.",
        start_date=date(2022, 6, 1),
    )
    assert exp.employer_name == "Acme Corp"

    # End date before start date
    with pytest.raises(ValidationError):
        Experience(
            employer_name="Acme Corp",
            title="Software Engineer",
            city="San Francisco",
            description="Built web apps.",
            start_date=date(2023, 1, 1),
            end_date=date(2022, 1, 1),
        )


def test_resume_data_requires_exp_or_proj():
    edu = Education(
        institution_name="MIT",
        degree_type="BS",
        start_date=date(2018, 9, 1),
        end_date=date(2022, 5, 30),
    )

    # Fails if neither experience nor projects provided
    with pytest.raises(ValidationError):
        ResumeData(education=[edu])

    # Succeeds with project
    proj = Project(
        project_name="Auto Apply App",
        description="Automated job application tool.",
        start_date=date(2023, 1, 1),
    )
    resume = ResumeData(education=[edu], projects=[proj])
    assert len(resume.projects) == 1


def test_user_profile_at_least_18():
    edu = Education(
        institution_name="MIT",
        degree_type="BS",
        start_date=date(2018, 9, 1),
        end_date=date(2022, 5, 30),
    )
    proj = Project(
        project_name="Auto Apply",
        description="App",
        start_date=date(2023, 1, 1),
    )
    resume = ResumeData(education=[edu], projects=[proj])
    addr = Address(
        street="123 Main St",
        city="NYC",
        state="NY",
        country="USA",
        zip_code="10001",
    )

    # Under 18 fails
    under_18 = date.today() - timedelta(days=17 * 365)
    with pytest.raises(ValidationError):
        UserProfile(
            user_id="user_123",
            name=Name(first_name="John", last_name="Doe"),
            birth_date=under_18,
            email="john.doe@example.com",
            phone="+12025550123",
            address=addr,
            resume_data=resume,
        )

    # 18 or older succeeds
    over_18 = date.today() - timedelta(days=20 * 365 + 10)
    profile = UserProfile(
        user_id="user_123",
        name=Name(first_name="John", last_name="Doe"),
        birth_date=over_18,
        email="john.doe@example.com",
        phone="+12025550123",
        address=addr,
        resume_data=resume,
    )
    assert profile.user_id == "user_123"


def test_project_form_data_empty_link():
    from data_types import ProjectFormData
    form_empty_str = ProjectFormData(project_name="Test", project_link="", description="Desc")
    assert form_empty_str.project_link == ""

    form_none = ProjectFormData(project_name="Test", project_link=None, description="Desc")
    assert form_none.project_link is None
