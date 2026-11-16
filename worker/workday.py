"""Playwright automation for Workday (myworkdayjobs.com / myworkdaysite.com) application flows.

Design rules:
- Never report SUBMITTED unless the post-submit confirmation message is actually seen.
- Anything unexpected (CAPTCHA, email verification, unanswered required question, validation
  error) stops the run with NEEDS_MANUAL so a human can finish it.
- Workday markup differs slightly per tenant; selectors live in SEL so they are easy to adjust
  after running scripts/verify_workday.py against a real tenant.
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from playwright.sync_api import Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_MS = 20_000
PAGE_ADVANCE_TIMEOUT_MS = 15_000
CONFIRMATION_TIMEOUT_MS = 30_000
MAX_FLOW_PAGES = 10


def _aid(automation_id: str) -> str:
    return f'[data-automation-id="{automation_id}"]'


SEL = {
    "apply": _aid("adventureButton"),
    "apply_manually": _aid("applyManually"),
    "sign_in_email": _aid("email"),
    "sign_in_password": _aid("password"),
    "sign_in_submit": _aid("signInSubmitButton"),
    "flow_marker": _aid("legalNameSection_firstName"),
    "next": f'{_aid("pageFooterNextButton")}, {_aid("bottom-navigation-next-button")}',
    "errors": f'{_aid("errorMessage")}, {_aid("errorBanner")}',
    "active_step": _aid("progressBarActiveStep"),
    "resume_input": _aid("file-upload-input-ref"),
    "question_field": '[data-automation-id^="formField-"]',
    "dropdown": 'button[aria-haspopup="listbox"]',
    "option": '[role="option"]',
}

CONFIRMATION_RE = re.compile(r"application submitted|thank you for applying|successfully submitted", re.I)

# Workday automation id -> key in AutoApplyWorker.map_standard_fields()
TEXT_FIELDS: Dict[str, str] = {
    "legalNameSection_firstName": "first_name",
    "legalNameSection_lastName": "last_name",
    "addressSection_addressLine1": "street",
    "addressSection_city": "city",
    "addressSection_postalCode": "zip",
    "phone-number": "phone",
}
DROPDOWN_FIELDS: Dict[str, str] = {
    "countryDropdown": "country",
    "addressSection_countryRegion": "state",
}

_COUNTRY_ALIASES = {"us": "United States of America", "usa": "United States of America", "united states": "United States of America"}
_US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


class Outcome(StrEnum):
    SUBMITTED = "SUBMITTED"            # confirmation message seen after clicking Submit
    REVIEW_READY = "REVIEW_READY"      # dry run: reached the final Review page, did NOT submit
    NEEDS_MANUAL = "NEEDS_MANUAL"
    FAILED = "FAILED"


class NeedsManual(Exception):
    """Raised when a human has to take over (credentials, validation errors, unconfirmed submit)."""


@dataclass
class WorkdayResult:
    outcome: Outcome
    detail: str
    steps: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)


class WorkdayApplier:
    def __init__(
        self,
        field_map: Dict[str, str],
        answer_lookup: Callable[[str], Optional[str]],
        *,
        dry_run: bool = True,
        credentials: Optional[Tuple[str, str]] = None,
        resume_path: Optional[str] = None,
        headless: bool = True,
        slow_mo_ms: int = 0,
        artifacts_dir: Optional[Path] = None,
    ):
        if resume_path and not Path(resume_path).is_file():
            raise ValueError("resume_path does not point to an existing file")
        self.fields = field_map
        self.lookup = answer_lookup
        self.dry_run = dry_run
        self.credentials = credentials
        self.resume_path = resume_path
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.artifacts_dir = artifacts_dir
        self._reset()

    def _reset(self) -> None:
        self.steps: List[str] = []
        self.screenshots: List[str] = []
        self._resume_uploaded = False

    # ---- public API -------------------------------------------------------------------------

    def apply(self, url: str) -> WorkdayResult:
        """Launches a browser, runs the flow, and always closes the browser."""
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless, slow_mo=self.slow_mo_ms)
            try:
                return self.run(browser.new_context().new_page(), url)
            finally:
                browser.close()

    def run(self, page: Page, url: str) -> WorkdayResult:
        """Runs the flow on an existing page (lets tests inject routes/mocks)."""
        self._reset()
        page.set_default_timeout(DEFAULT_TIMEOUT_MS)
        try:
            page.goto(url, wait_until="domcontentloaded")
            self._step(page, "opened_job_page")
            self._start_application(page)
            self._sign_in(page)
            return self._complete_pages(page)
        except NeedsManual as exc:
            self._step(page, "needs_manual")
            return self._result(Outcome.NEEDS_MANUAL, str(exc))
        except PlaywrightTimeout as exc:
            self._step(page, "timeout")
            logger.error("Workday step timed out", exc_info=True)
            # First lines of Playwright's message name the action and the selector that was never found.
            summary = " ".join(line.strip() for line in str(exc).splitlines()[:3])
            return self._result(Outcome.FAILED, f"Timed out: {summary}")
        except Exception:
            self._step(page, "error")
            logger.error("Unexpected Workday error", exc_info=True)
            return self._result(Outcome.FAILED, "Unexpected error (see logs)")

    # ---- flow -------------------------------------------------------------------------------

    def _start_application(self, page: Page) -> None:
        page.locator(SEL["apply"]).first.click()
        try:  # not every tenant shows the "Apply Manually" chooser
            page.locator(SEL["apply_manually"]).first.click(timeout=5_000)
        except PlaywrightTimeout:
            pass
        self._step(page, "clicked_apply")

    def _sign_in(self, page: Page) -> None:
        page.locator(f'{SEL["sign_in_email"]}, {SEL["flow_marker"]}').first.wait_for()
        if not page.locator(SEL["sign_in_email"]).first.is_visible():
            return  # already inside the application flow
        if not self.credentials:
            raise NeedsManual("Workday sign-in required but WORKDAY_PASSWORD is not set")
        email, password = self.credentials
        page.locator(SEL["sign_in_email"]).first.fill(email)
        page.locator(SEL["sign_in_password"]).first.fill(password)
        page.locator(SEL["sign_in_submit"]).first.click(force=True)
        page.locator(f'{SEL["flow_marker"]}, {SEL["errors"]}').first.wait_for()
        if not page.locator(SEL["flow_marker"]).first.is_visible():
            raise NeedsManual(f"Workday sign-in rejected: {self._error_text(page)}")
        self._step(page, "signed_in")

    def _complete_pages(self, page: Page) -> WorkdayResult:
        for _ in range(MAX_FLOW_PAGES):
            title = self._active_step(page)
            self._fill_page(page)
            self._step(page, f"filled_{title or 'page'}")
            next_btn = page.locator(SEL["next"]).first
            if re.search(r"submit", next_btn.inner_text(), re.I):
                if self.dry_run:
                    self._step(page, "review_ready_dry_run")
                    return self._result(Outcome.REVIEW_READY, "Reached Review page; not submitted (dry run)")
                next_btn.click(force=True)
                self._wait_for_confirmation(page)
                self._step(page, "submitted")
                return self._result(Outcome.SUBMITTED, "Submission confirmation displayed")
            next_btn.click(force=True)
            self._wait_for_advance(page, title)
        raise NeedsManual(f"Flow exceeded {MAX_FLOW_PAGES} pages without reaching Review")

    def _wait_for_advance(self, page: Page, previous_title: str) -> None:
        for _ in range(PAGE_ADVANCE_TIMEOUT_MS // 250):
            if page.locator(SEL["errors"]).first.is_visible():
                raise NeedsManual(f"Validation errors on '{previous_title}': {self._error_text(page)}")
            if self._active_step(page) != previous_title:
                return
            page.wait_for_timeout(250)
        raise NeedsManual(f"Page '{previous_title}' did not advance")

    def _wait_for_confirmation(self, page: Page) -> None:
        confirmation = page.get_by_text(CONFIRMATION_RE).first
        for _ in range(CONFIRMATION_TIMEOUT_MS // 250):
            if confirmation.is_visible():
                return
            if page.locator(SEL["errors"]).first.is_visible():
                raise NeedsManual(f"Submit rejected: {self._error_text(page)}")
            page.wait_for_timeout(250)
        raise NeedsManual("Clicked Submit but saw no confirmation; check the application manually")

    # ---- page filling -----------------------------------------------------------------------

    def _fill_page(self, page: Page) -> None:
        for automation_id, key in TEXT_FIELDS.items():
            value, loc = self.fields.get(key), page.locator(_aid(automation_id)).first
            if value and loc.count() and not loc.input_value():
                loc.fill(value)

        for automation_id, key in DROPDOWN_FIELDS.items():
            value, loc = self.fields.get(key), page.locator(_aid(automation_id)).first
            if value and loc.count() and re.search(r"select", loc.inner_text(), re.I):
                self._select_option(page, loc, self._dropdown_alias(key, value))

        resume = page.locator(SEL["resume_input"]).first
        if self.resume_path and not self._resume_uploaded and resume.count():
            resume.set_input_files(self.resume_path)
            self._resume_uploaded = True

        self._answer_questions(page)

    def _answer_questions(self, page: Page) -> None:
        for question in page.locator(SEL["question_field"]).all():
            label = question.locator("label").first
            answer = self.lookup(label.inner_text()) if label.count() else None
            if not answer:
                continue
            textbox = question.locator("input[type=text], textarea").first
            if textbox.count():
                if not textbox.input_value():
                    textbox.fill(answer)
                continue
            dropdown = question.locator(SEL["dropdown"]).first
            if dropdown.count() and re.search(r"select", dropdown.inner_text(), re.I):
                self._select_option(page, dropdown, answer)

    def _select_option(self, page: Page, dropdown: Locator, value: str) -> None:
        dropdown.click()
        option = page.locator(SEL["option"]).filter(has_text=re.compile(rf"^\s*{re.escape(value)}\s*$", re.I)).first
        try:
            option.click(timeout=3_000)
        except PlaywrightTimeout:
            logger.warning("No matching dropdown option", extra={"value_length": len(value)})
            page.keyboard.press("Escape")

    @staticmethod
    def _dropdown_alias(key: str, value: str) -> str:
        if key == "country":
            return _COUNTRY_ALIASES.get(value.strip().lower(), value)
        if key == "state":
            return _US_STATES.get(value.strip().upper(), value)
        return value

    # ---- helpers ----------------------------------------------------------------------------

    @staticmethod
    def _active_step(page: Page) -> str:
        loc = page.locator(SEL["active_step"]).first
        return loc.inner_text().strip() if loc.count() else ""

    @staticmethod
    def _error_text(page: Page) -> str:
        return " | ".join(t.strip() for t in page.locator(SEL["errors"]).all_inner_texts() if t.strip())[:300]

    def _step(self, page: Page, name: str) -> None:
        self.steps.append(name)
        logger.info("Workday step", extra={"step": name})
        if not self.artifacts_dir:
            return
        try:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            path = self.artifacts_dir / f"{len(self.steps):02d}_{name}_{datetime.now():%H%M%S}.png"
            page.screenshot(path=str(path), full_page=True)
            self.screenshots.append(str(path))
        except Exception:
            logger.debug("Screenshot failed", exc_info=True)

    def _result(self, outcome: Outcome, detail: str) -> WorkdayResult:
        return WorkdayResult(outcome, detail, list(self.steps), list(self.screenshots))
