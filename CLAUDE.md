# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A Streamlit application for automating job applications for small groups (~10 users).
Uses AWS DynamoDB for semi-structured profile & application storage, Google OAuth for authentication, and a Playwright-based worker foundation for ATS submissions.

## Setup and running

```bash
# activate the existing venv (Windows/PowerShell)
.\venv\Scripts\Activate.ps1

# install dependencies
pip install -r requirements.txt

# run tests
pytest

# run the Streamlit app
streamlit run app.py
```

## Architecture

- `app.py`: Streamlit entrypoint and authentication dashboard.
- `data_types.py`: Pydantic data models for `UserProfile`, `ResumeData`, `Education`, `Experience`, `Project`, `Application`, `CachedQuestion`.
- `components/generic_form.py`: Meta-programming form generator that inspects Pydantic `model_fields` to render Streamlit widgets dynamically.
- `components/resume_form.py`: Profile, education, experience, and project intake form.
- `utils/db.py`: Semi-structured AWS DynamoDB CRUD operations with Pydantic serialization/deserialization.
- `utils/validation.py`: Address and field validation utilities.
- `utils/upload_resume.py`: Resume text, contact, and skill extraction.
- `worker/apply_worker.py`: Auto-apply automation engine and field mapping for ATS systems. Workday URLs (`*.myworkdayjobs.com`) are routed to `worker/workday.py`; other ATS types are still stubs.
- `worker/workday.py`: Playwright Workday adapter. Returns `SUBMITTED` only after the confirmation message is seen; anything unexpected becomes `NEEDS_MANUAL`/`FAILED`. Selectors are in `SEL`/`TEXT_FIELDS`.
- `scripts/verify_workday.py`: live smoke test against a real Workday job (dry run by default, `--submit` to really submit).
- `pages/`: Multi-page UI:
  - `1_Profile.py`: Profile, experience, and resume management.
  - `2_Applications.py`: Application queue, status tracking, and outcomes.
  - `3_Question_Cache.py`: Saved answers for screening questions.
- `tests/`: Pytest suite for data models, YOE calculations, generic form type unwrapping, DB serialization, and workers.

## Configuration and secrets

- `.env` holds AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `DYNAMODB_TABLE_NAME`).
- `.streamlit/secrets.toml` holds the `[auth]` section for Google OAuth.
- Never log, echo, or commit `.env` or `.streamlit/secrets.toml`.
- Workday sign-in: `WORKDAY_PASSWORD` (required) and `WORKDAY_EMAIL` (optional, defaults to profile email) env vars. The Workday account must already exist and be verified for that tenant; account creation is not automated.

## Verifying the Workday worker

```bash
# one-time: python -m playwright install chromium
pytest tests/test_workday.py   # mock tenant: proves the logic, dry-run vs submit, failure handling
python -m scripts.verify_workday --url <real job url> --profile-json profile.json --resume resume.pdf   # dry run, visible browser
python -m scripts.verify_workday ... --submit                                                         # real submission
```
`artifacts/` (screenshots with personal data) and `profile.json` are gitignored.
