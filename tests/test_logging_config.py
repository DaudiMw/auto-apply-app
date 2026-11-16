import json
import logging

import pytest

from utils.logging_config import JsonFormatter, hash_id, setup_logging


@pytest.fixture
def clean_root_logger():
    root = logging.getLogger()
    original_handlers, original_level = root.handlers[:], root.level
    yield root
    for h in root.handlers[:]:
        if h not in original_handlers:
            h.close()
            root.removeHandler(h)
    root.setLevel(original_level)


def test_hash_id_is_stable_and_hides_value():
    assert hash_id("user@example.com") == hash_id("user@example.com")
    assert "user" not in hash_id("user@example.com")
    assert hash_id(None) == "anonymous"


def test_json_formatter_includes_extra_fields():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    record.application_id = "abc"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["application_id"] == "abc"


def test_setup_logging_is_idempotent_and_writes_file(tmp_path, monkeypatch, clean_root_logger):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    setup_logging()
    count = len(clean_root_logger.handlers)
    setup_logging()
    assert len(clean_root_logger.handlers) == count

    logging.getLogger("tests.logging").info("file check", extra={"user": "abc"})
    for h in clean_root_logger.handlers:
        h.flush()
    line = (tmp_path / "app.log").read_text(encoding="utf-8").strip().splitlines()[-1]
    assert json.loads(line)["message"] == "file check"


def test_invalid_log_level_falls_back_to_info(tmp_path, monkeypatch, clean_root_logger):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_LEVEL", "bogus")
    setup_logging()
    assert clean_root_logger.level == logging.INFO
