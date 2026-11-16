"""Live smoke test: run the real worker against a real Workday job URL.

Default is a DRY RUN: signs in, fills every page, stops on the Review page, never clicks Submit.
Screenshots of every step are saved so you can see exactly what the bot did.

Usage (from repo root, venv active):
    $env:WORKDAY_PASSWORD = "<password of your Workday account for that tenant>"
    python -m scripts.verify_workday --url https://<tenant>.wd5.myworkdayjobs.com/... --profile-json profile.json --resume resume.pdf
    python -m scripts.verify_workday ... --submit      # really submits (asks for confirmation)

Exit code 0 only if the dry run reached Review or the live run saw the submission confirmation.
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from data_types import UserProfile
from utils.logging_config import setup_logging
from worker.apply_worker import AutoApplyWorker, is_workday_url
from worker.workday import Outcome


def _load_profile(args) -> UserProfile:
    if args.profile_json:
        return UserProfile.model_validate_json(Path(args.profile_json).read_text(encoding="utf-8"))
    from utils.db import get_user_profile

    profile = get_user_profile(args.user_id)
    if not profile:
        sys.exit("Profile not found in DynamoDB.")
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="https Workday job URL (*.myworkdayjobs.com)")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--profile-json", help="UserProfile JSON file")
    source.add_argument("--user-id", help="Load profile from DynamoDB")
    parser.add_argument("--resume", help="Resume file to upload")
    parser.add_argument("--submit", action="store_true", help="Actually submit (default: dry run)")
    parser.add_argument("--headless", action="store_true", help="No visible browser (default: visible)")
    parser.add_argument("--slow-mo", type=int, default=250, help="ms delay between browser actions")
    parser.add_argument("--artifacts-dir", default="artifacts/workday")
    args = parser.parse_args()

    if not is_workday_url(args.url):
        sys.exit("URL must be https and on *.myworkdayjobs.com or *.myworkdaysite.com")

    if args.submit and input("This will SUBMIT a real application. Type SUBMIT to continue: ") != "SUBMIT":
        sys.exit("Aborted.")

    setup_logging()
    logging.getLogger().setLevel(logging.WARNING)  # keep the console report readable; steps are printed below

    profile = _load_profile(args)
    worker = AutoApplyWorker(profile, dry_run=not args.submit, resume_path=args.resume, headless=args.headless)
    artifacts = Path(args.artifacts_dir) / datetime.now().strftime("%Y%m%d_%H%M%S")
    result = worker.build_workday_applier(slow_mo_ms=args.slow_mo, artifacts_dir=artifacts).apply(args.url)

    print(f"\nMode:    {'LIVE SUBMIT' if args.submit else 'DRY RUN'}")
    print(f"Outcome: {result.outcome.value}")
    print(f"Detail:  {result.detail}")
    print("Steps:   " + " -> ".join(result.steps))
    print(f"Screenshots: {artifacts} ({len(result.screenshots)} files; contain personal data, do not commit)")

    ok = result.outcome == (Outcome.SUBMITTED if args.submit else Outcome.REVIEW_READY)
    print("RESULT:  " + ("PASS" if ok else "FAIL - inspect the last screenshot, then adjust SEL/TEXT_FIELDS in worker/workday.py"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
