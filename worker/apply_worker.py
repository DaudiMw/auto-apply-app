import logging
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from data_types import Application, ApplicationStatus, UserProfile
from utils.db import update_application_status, upsert_cached_question
from utils.logging_config import hash_id

logger = logging.getLogger(__name__)

WORKDAY_HOST_SUFFIXES = (".myworkdayjobs.com", ".myworkdaysite.com")


def is_workday_url(url: str) -> bool:
    """True for https URLs whose hostname is a Workday tenant (not just a substring match)."""
    parsed = urlparse(url)
    return parsed.scheme == "https" and (parsed.hostname or "").lower().endswith(WORKDAY_HOST_SUFFIXES)


class AutoApplyWorker:
    """Automates job applications for candidate profiles using headless browser / ATS detection."""

    def __init__(
        self,
        profile: UserProfile,
        dry_run: bool = True,
        resume_path: Optional[str] = None,
        headless: bool = True,
    ):
        self.profile = profile
        self.dry_run = dry_run
        self.resume_path = resume_path
        self.headless = headless

    def find_cached_answer(self, question_text: str) -> Optional[str]:
        """Looks up the question text in the candidate's cached question answers."""
        norm_target = question_text.strip().lower()
        for item in self.profile.cache:
            if item.question.strip().lower() in norm_target or norm_target in item.question.strip().lower():
                return item.answer
        return None

    def map_standard_fields(self) -> Dict[str, str]:
        """Provides mapping for common ATS input fields."""
        return {
            "first_name": self.profile.name.first_name,
            "last_name": self.profile.name.last_name,
            "full_name": f"{self.profile.name.first_name} {self.profile.name.last_name}",
            "email": str(self.profile.email),
            "phone": str(self.profile.phone),
            "street": self.profile.address.street,
            "city": self.profile.address.city,
            "state": self.profile.address.state,
            "zip": self.profile.address.zip_code,
            "country": self.profile.address.country,
        }

    def build_workday_applier(self, slow_mo_ms: int = 0, artifacts_dir: Optional[Path] = None):
        """Creates a WorkdayApplier. Sign-in password comes from WORKDAY_PASSWORD (never stored/logged);
        the login email defaults to the profile email and can be overridden with WORKDAY_EMAIL."""
        from worker.workday import WorkdayApplier  # lazy: Playwright is only needed for Workday jobs

        password = os.environ.get("WORKDAY_PASSWORD")
        email = os.environ.get("WORKDAY_EMAIL") or str(self.profile.email)
        return WorkdayApplier(
            self.map_standard_fields(),
            self.find_cached_answer,
            dry_run=self.dry_run,
            credentials=(email, password) if password else None,
            resume_path=self.resume_path,
            headless=self.headless,
            slow_mo_ms=slow_mo_ms,
            artifacts_dir=artifacts_dir,
        )

    def _process_workday(self, application: Application) -> ApplicationStatus:
        from worker.workday import Outcome

        try:
            result = self.build_workday_applier().apply(str(application.link))
        except Exception:
            logger.error("Workday run could not start", extra={"application_id": application.application_id}, exc_info=True)
            return ApplicationStatus.FAILED

        logger.info(
            "Workday run finished",
            extra={"application_id": application.application_id, "outcome": result.outcome.value, "detail": result.detail},
        )
        if result.outcome in (Outcome.SUBMITTED, Outcome.REVIEW_READY):
            return ApplicationStatus.SUBMITTED  # REVIEW_READY only occurs in dry runs (existing dry-run contract)
        if result.outcome == Outcome.NEEDS_MANUAL:
            return ApplicationStatus.NEEDS_MANUAL_COMPLETION
        return ApplicationStatus.FAILED

    def process_application(self, application: Application) -> ApplicationStatus:
        """Processes a single job application link."""
        url = str(application.link)
        logger.info(
            "Processing application",
            extra={"user": hash_id(self.profile.user_id), "application_id": application.application_id, "dry_run": self.dry_run},
        )

        if is_workday_url(url):
            return self._process_workday(application)

        # Check supported board types
        if "greenhouse.io" in url or "lever.co" in url or "jobs." in url or "careers." in url:
            if self.dry_run:
                logger.info("Dry run: mapped fields for ATS application", extra={"application_id": application.application_id})
                return ApplicationStatus.SUBMITTED
            else:
                # Playwright execution logic would run here
                return ApplicationStatus.SUBMITTED

        logger.warning("Unrecognized or custom ATS form", extra={"application_id": application.application_id})
        return ApplicationStatus.NEEDS_MANUAL_COMPLETION


def run_worker_cycle(profile: UserProfile, dry_run: bool = True) -> Dict[str, Any]:
    """Processes all QUEUED applications for a user profile."""
    worker = AutoApplyWorker(profile=profile, dry_run=dry_run)
    results = {"processed": 0, "submitted": 0, "needs_manual": 0, "failed": 0}

    for app in profile.applications:
        if app.status == ApplicationStatus.QUEUED:
            results["processed"] += 1
            new_status = worker.process_application(app)
            app.status = new_status
            if new_status == ApplicationStatus.SUBMITTED:
                results["submitted"] += 1
            elif new_status == ApplicationStatus.NEEDS_MANUAL_COMPLETION:
                results["needs_manual"] += 1
            else:
                results["failed"] += 1

            update_application_status(profile.user_id, app.application_id, new_status)

    logger.info("Worker cycle complete", extra={"user": hash_id(profile.user_id), **results})
    return results
