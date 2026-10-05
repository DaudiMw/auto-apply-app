# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A Streamlit app for automatically applying to jobs. Currently very early-stage: the only working piece is a resume-information intake form (`app.py`). `pages/` and `utils/upload_resume.py` are empty placeholders for planned multi-page structure and resume upload handling.

## Setup and running

```bash
# activate the existing venv (Windows/Git Bash)
source venv/Scripts/activate

pip install -r requirements.txt

streamlit run app.py
```

Note: `requirements.txt` is saved as UTF-16LE with CRLF — editors/tools that assume UTF-8 will render it as garbled text. If editing it, preserve the encoding or explicitly convert (e.g. `iconv -f UTF-8 -t UTF-16LE`) so pip can still read it.

There is no build step, linter, or test suite configured in this repo yet.

## Configuration and secrets

- `.env` holds AWS credentials (`AWS_ACCESS_KEY`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`) for `boto3` — used for the planned "unstructured database on aws" resume storage referenced in `app.py`. `.env` is gitignored.
- `.streamlit/secrets.toml` holds an `[auth]` section (`redirect_uri`, `cookie_secret`, `client_id`, `client_secret`, `server_metadata_url`) for Streamlit's native Google OAuth (`st.login` / `st.logout` / `st.user`). This file is **not** in `.gitignore` — be careful not to commit it or echo its contents.

Never print or log the contents of `.env` or `.streamlit/secrets.toml`.

## Architecture notes

- `app.py` is the Streamlit entry point. Login/logout via `st.user.is_logged_in`, `st.login`, `st.logout` is stubbed out (commented) pending OAuth wiring.
- Resume data is intended to be fetched from and saved to an AWS-backed store keyed by `st.user.get('user_id')` (see the commented `unstructured_database_aws.get(...)` call in `app.py`) — this integration does not exist yet.
- `validate_address(address: dict) -> bool` in `app.py` is currently a stub that always returns `False`; it's meant to validate the address fields collected in the resume form (street/apt/city/state/zip) before persisting.
- Streamlit's multi-page app convention applies: files dropped into `pages/` become additional pages automatically. `pages/` is currently empty.
