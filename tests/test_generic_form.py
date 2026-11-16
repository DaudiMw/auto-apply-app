import enum
from typing import Annotated, Optional, List
from pydantic import Field, HttpUrl
from components.generic_form import unwrap_type
from data_types import ApplicationStatus


def test_unwrap_type():
    assert unwrap_type(str) is str
    assert unwrap_type(int) is int
    assert unwrap_type(Optional[str]) is str
    assert unwrap_type(Optional[int]) is int
    assert unwrap_type(Annotated[Optional[str], Field(title="Test")]) is str
    assert unwrap_type(Annotated[Optional[HttpUrl], Field(title="URL")]) is HttpUrl
    assert unwrap_type(Annotated[ApplicationStatus, Field(title="Status")]) is ApplicationStatus
    assert unwrap_type(Annotated[Optional[List[str]], Field(title="Skills")]) == List[str]
