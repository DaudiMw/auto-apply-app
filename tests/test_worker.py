from datetime import date
from data_types import (
    Name, Address, Education, Experience, Project,
    ResumeData, Application, ApplicationStatus, UserProfile, CachedQuestion
)
from worker.apply_worker import AutoApplyWorker, run_worker_cycle


def test_auto_apply_worker_mapping_and_caching():
    edu = Education(
        institution_name="MIT",
        degree_type="BS",
        start_date=date(2018, 1, 1),
        end_date=date(2022, 1, 1),
    )
    proj = Project(
        project_name="App",
        description="Bot",
        start_date=date(2023, 1, 1),
    )
    addr = Address(
        street="123 Main St",
        city="Boston",
        state="MA",
        country="USA",
        zip_code="02138",
    )
    cache_q = CachedQuestion(
        question="Are you authorized to work in the US?",
        answer="Yes",
    )
    app1 = Application(
        link="https://boards.greenhouse.io/job/123",
        date_applied=date.today(),
        status=ApplicationStatus.QUEUED,
    )
    profile = UserProfile(
        user_id="user_test",
        name=Name(first_name="Jane", last_name="Doe"),
        birth_date=date(1995, 1, 1),
        email="jane.doe@example.com",
        phone="+16175550199",
        address=addr,
        resume_data=ResumeData(education=[edu], projects=[proj]),
        cache=[cache_q],
        applications=[app1],
    )

    worker = AutoApplyWorker(profile=profile, dry_run=True)
    field_map = worker.map_standard_fields()
    assert field_map["first_name"] == "Jane"
    assert field_map["last_name"] == "Doe"
    assert field_map["email"] == "jane.doe@example.com"
    assert field_map["city"] == "Boston"

    # Cached question lookup
    ans = worker.find_cached_answer("Please confirm: Are you authorized to work in the US?")
    assert ans == "Yes"

    # Process queued apps
    results = run_worker_cycle(profile, dry_run=True)
    assert results["processed"] == 1
    assert results["submitted"] == 1
    assert profile.applications[0].status == ApplicationStatus.SUBMITTED
