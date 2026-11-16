from datetime import date

import pytest

from data_types import (
    Address, Application, ApplicationStatus, CachedQuestion, Education, Name, Project, ResumeData, UserProfile,
)
from mock_workday import (
    AUTH_QUESTION, FREE_TEXT_QUESTION, MOCK_EMAIL, MOCK_JOB_URL, MOCK_PASSWORD, MockWorkday,
)
from worker.apply_worker import AutoApplyWorker, is_workday_url

sync_api = pytest.importorskip("playwright.sync_api")
from worker.workday import Outcome, WorkdayApplier, WorkdayResult  # noqa: E402


def _profile(with_why_answer: bool = True) -> UserProfile:
    cache = [CachedQuestion(question=AUTH_QUESTION, answer="Yes")]
    if with_why_answer:
        cache.append(CachedQuestion(question=FREE_TEXT_QUESTION, answer="I like the mission."))
    return UserProfile(
        user_id="user_test",
        name=Name(first_name="Jane", last_name="Doe"),
        birth_date=date(1995, 1, 1),
        email=MOCK_EMAIL,
        phone="+16175550199",
        address=Address(street="123 Main St", city="Boston", state="MA", country="USA", zip_code="02138"),
        resume_data=ResumeData(
            education=[Education(institution_name="MIT", degree_type="BS", start_date=date(2018, 1, 1), end_date=date(2022, 1, 1))],
            projects=[Project(project_name="App", description="Bot", start_date=date(2023, 1, 1))],
        ),
        cache=cache,
    )


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except sync_api.Error:
            pytest.skip("Chromium not installed (run: python -m playwright install chromium)")
        yield b
        b.close()


@pytest.fixture
def page(browser):
    p = browser.new_page()
    yield p
    p.close()


@pytest.fixture
def resume(tmp_path):
    f = tmp_path / "resume.pdf"
    f.write_bytes(b"%PDF-1.4 test")
    return str(f)


def _applier(profile, resume, dry_run, password=MOCK_PASSWORD) -> WorkdayApplier:
    worker = AutoApplyWorker(profile, dry_run=dry_run, resume_path=resume)
    return WorkdayApplier(
        worker.map_standard_fields(),
        worker.find_cached_answer,
        dry_run=dry_run,
        credentials=(MOCK_EMAIL, password) if password else None,
        resume_path=resume,
    )


def test_is_workday_url():
    assert is_workday_url("https://acme.wd5.myworkdayjobs.com/en-US/External/job/x")
    assert is_workday_url("https://wd1.myworkdaysite.com/recruiting/acme/x")
    assert not is_workday_url("http://acme.wd5.myworkdayjobs.com/x")  # not https
    assert not is_workday_url("https://evil.com/myworkdayjobs.com")  # substring only
    assert not is_workday_url("https://myworkdayjobs.com.evil.com/x")
    assert not is_workday_url("https://boards.greenhouse.io/job/123")


def test_dry_run_reaches_review_without_submitting(page, resume):
    mock = MockWorkday(page)
    result = _applier(_profile(), resume, dry_run=True).run(page, MOCK_JOB_URL)

    assert result.outcome == Outcome.REVIEW_READY, result.detail
    assert mock.submissions == []
    assert result.steps[-1] == "review_ready_dry_run"


def test_live_run_submits_with_profile_data_and_confirmation(page, resume):
    mock = MockWorkday(page)
    result = _applier(_profile(), resume, dry_run=False).run(page, MOCK_JOB_URL)

    assert result.outcome == Outcome.SUBMITTED, result.detail
    assert len(mock.submissions) == 1
    sent = mock.submissions[0]
    assert sent["legalNameSection_firstName"] == "Jane"
    assert sent["legalNameSection_lastName"] == "Doe"
    assert sent["addressSection_city"] == "Boston"
    assert sent["countryDropdown"] == "United States of America"  # "USA" alias resolved
    assert sent["addressSection_countryRegion"] == "Massachusetts"  # "MA" expanded
    assert sent["q_auth"] == "Yes"
    assert sent["q_why"] == "I like the mission."
    assert sent["file-upload-input-ref"].endswith("resume.pdf")


def test_unanswered_required_question_needs_manual_and_does_not_submit(page, resume):
    mock = MockWorkday(page)
    result = _applier(_profile(with_why_answer=False), resume, dry_run=False).run(page, MOCK_JOB_URL)

    assert result.outcome == Outcome.NEEDS_MANUAL
    assert "q_why" in result.detail
    assert mock.submissions == []


def test_wrong_password_needs_manual(page, resume):
    mock = MockWorkday(page)
    result = _applier(_profile(), resume, dry_run=False, password="wrong").run(page, MOCK_JOB_URL)

    assert result.outcome == Outcome.NEEDS_MANUAL
    assert "incorrect" in result.detail
    assert mock.submissions == []


def test_missing_credentials_needs_manual(page, resume):
    MockWorkday(page)
    result = _applier(_profile(), resume, dry_run=False, password=None).run(page, MOCK_JOB_URL)

    assert result.outcome == Outcome.NEEDS_MANUAL
    assert "WORKDAY_PASSWORD" in result.detail


def test_missing_apply_button_fails_with_timeout_not_submitted(page, resume, monkeypatch):
    import worker.workday as wd

    monkeypatch.setattr(wd, "DEFAULT_TIMEOUT_MS", 1_000)
    page.route("https://acme.wd5.myworkdayjobs.com/**", lambda r: r.fulfill(status=200, content_type="text/html", body="<h1>Job closed</h1>"))
    result = _applier(_profile(), resume, dry_run=False).run(page, MOCK_JOB_URL)

    assert result.outcome == Outcome.FAILED
    assert "adventureButton" in result.detail


@pytest.mark.parametrize(
    "outcome,expected",
    [
        (Outcome.SUBMITTED, ApplicationStatus.SUBMITTED),
        (Outcome.REVIEW_READY, ApplicationStatus.SUBMITTED),
        (Outcome.NEEDS_MANUAL, ApplicationStatus.NEEDS_MANUAL_COMPLETION),
        (Outcome.FAILED, ApplicationStatus.FAILED),
    ],
)
def test_worker_routes_workday_links_and_maps_outcomes(monkeypatch, outcome, expected):
    monkeypatch.setattr(WorkdayApplier, "apply", lambda self, url: WorkdayResult(outcome, "x"))
    app = Application(link=MOCK_JOB_URL, date_applied=date.today())

    assert AutoApplyWorker(_profile(), dry_run=True).process_application(app) == expected


def test_worker_marks_failed_when_browser_cannot_start(monkeypatch):
    def boom(self, url):
        raise RuntimeError("no browser")

    monkeypatch.setattr(WorkdayApplier, "apply", boom)
    app = Application(link=MOCK_JOB_URL, date_applied=date.today())

    assert AutoApplyWorker(_profile(), dry_run=False).process_application(app) == ApplicationStatus.FAILED
