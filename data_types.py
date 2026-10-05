from uuid import uuid4
from pydantic import BaseModel, EmailStr, Field, HttpUrl, PositiveInt, model_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from datetime import date
from enum import StrEnum
from typing import Optional, List, Annotated


class USPhoneNumber(PhoneNumber):
    default_region_code = 'US'

class ApplicationStatus(StrEnum):
    # worker-driven pipeline
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_ON_REPLY = "WAITING_ON_REPLY"
    SUBMITTED = "SUBMITTED"
    NEEDS_MANUAL_COMPLETION = "NEEDS_MANUAL_COMPLETION"
    FAILED = "FAILED"
    # human-tracked outcome, set via the dropdown
    INTERVIEWING = "INTERVIEWING"
    OFFER_RECEIVED = "OFFER_RECEIVED"
    REJECTED_BY_COMPANY = "REJECTED_BY_COMPANY"
    OFFER_DECLINED = "OFFER_DECLINED"
    ACCEPTED = "ACCEPTED"

    @classmethod
    def user_editable(cls) -> list["ApplicationStatus"]:
        return [
            cls.INTERVIEWING,
            cls.OFFER_RECEIVED,
            cls.REJECTED_BY_COMPANY,
            cls.OFFER_DECLINED,
            cls.ACCEPTED,
        ]

class Name(BaseModel):
    first_name: Annotated[str, Field(title="First Name")]
    middle_name: Annotated[Optional[str], Field(title="Middle Name")] = None
    last_name: Annotated[str, Field(title="Last Name")]   

class Address(BaseModel):
    street: Annotated[str, Field(title="Street")]
    apt_number: Annotated[Optional[str], Field(title="Apartment Number")] = None
    city: Annotated[str, Field(title="City")]
    state: Annotated[str, Field(title="State")]
    country: Annotated[str, Field(title="Country")]
    zip_code: Annotated[str, Field(title="Zip Code", pattern=r"^\d{5}(-\d{4})?$")]

class AddressFormData(BaseModel):
    street: Annotated[Optional[str], Field(title="Street")] = None
    apt_number: Annotated[Optional[str], Field(title="Apartment Number")] = None
    city: Annotated[Optional[str], Field(title="City")] = None
    state: Annotated[Optional[str], Field(title="State")] = None
    country: Annotated[Optional[str], Field(title="Country")] = None
    zip_code: Annotated[Optional[str], Field(title="Zip Code")] = None

class Education(BaseModel):
    institution_name: Annotated[str, Field(title="School Name")]
    degree_type: Annotated[str, Field(title="Degree Type")]
    degree_field: Annotated[Optional[str], Field(title="Field of Study")] = None 
    description: Annotated[Optional[str], Field(title="Description", json_schema_extra={"widget":"textarea"})] = None 
    start_date: Annotated[date, Field(title="Start Date")]
    end_date: Annotated[Optional[date], Field(title="End Date")] = None

    @model_validator(mode='after')
    def check_end_after_start(self):
        if self.end_date and self.start_date >= self.end_date:
            raise ValueError("Education start date must be before end date.")
        
        return self

    @model_validator(mode='after')
    def check_end_date_valid(self):
        if self.start_date > date.today():
            raise ValueError("Education start date has to be in the past.")

        return self

class EducationFormData(BaseModel):
    institution_name: Annotated[Optional[str], Field(title="School Name")] = None
    degree_type: Annotated[Optional[str], Field(title="Degree Type")] = None
    degree_field: Annotated[Optional[str], Field(title="Field of Study")] = None 
    description: Annotated[Optional[str], Field(title="Description", json_schema_extra={"widget":"textarea"})] = None 
    start_date: Annotated[Optional[date], Field(title="Start Date")] = None
    end_date: Annotated[Optional[date], Field(title="Start Date")] = None


class Experience(BaseModel):
    employer_name: Annotated[str, Field(title="Employer Name")]
    title: Annotated[str, Field(title="Position")]
    city: Annotated[str, Field(title="City")]
    state: Annotated[Optional[str], Field(title="State")] = None
    country: Annotated[Optional[str], Field(title="Country")] = None
    description: Annotated[str, Field(title="Description", json_schema_extra={"widget":"textarea"})]
    start_date: Annotated[date, Field(title="Start Date")]
    end_date: Annotated[Optional[date], Field(title="End Date")] = None

    @model_validator(mode='after')
    def check_end_after_start(self):
        if self.end_date and self.start_date >= self.end_date:
            raise ValueError("Experience start date must be before end date.")
        return self
    
    @model_validator(mode='after')
    def check_date_valid(self):
        if self.end_date and self.end_date > date.today():
            raise ValueError("Experience date end has to be in the past.")
        
        return self

class ExperienceFormData(BaseModel):
    employer_name: Annotated[Optional[str], Field(title="Employer Name")] = None
    title: Annotated[Optional[str], Field(title="Position")] = None
    city: Annotated[Optional[str], Field(title="City")] = None
    state: Annotated[Optional[str], Field(title="State")] = None
    country: Annotated[Optional[str], Field(title="Country")] = None
    description: Annotated[Optional[str], Field(title="Description", json_schema_extra={"widget":"textarea"})] = None
    start_date: Annotated[Optional[date], Field(title="Start Date")] = None
    end_date: Annotated[Optional[date], Field(title="End Date")] = None

class Project(BaseModel):
    project_name: Annotated[str, Field(title="Project Name")]
    project_link: Annotated[Optional[HttpUrl], Field(title="Link to Project")] = None
    description: Annotated[str, Field(title="Description", json_schema_extra={"widget":"textarea"})]
    start_date: Annotated[date, Field(title="Date")]

    @model_validator(mode='after')
    def check_date_valid(self):
        if self.start_date > date.today():
            raise ValueError("Project date has to be in the past.")
        
        return self

class ProjectFormData(BaseModel):
    project_name: Annotated[Optional[str], Field(title="Project Name")] = None
    project_link: Annotated[Optional[HttpUrl], Field(title="Link to Project")] = None
    description: Annotated[Optional[str], Field(title="Description", json_schema_extra={"widget":"textarea"})] = None
    start_date: Annotated[Optional[date], Field(title="Date")] = None

class ResumeData(BaseModel):
    
    education: List[Education]
    experience: Optional[List[Experience]] = None
    projects: Optional[List[Project]] = None
    skills: Optional[List[str]] = None

    @model_validator(mode='after')
    def proj_or_exp_must_exist(self):
        if not self.experience and not self.projects:
            raise ValueError("You must supply at least one project or experience.")
        return self


class Application(BaseModel):

    application_id: str = Field(default_factory=lambda: str(uuid4()))
    link: HttpUrl
    date_applied: date
    status: ApplicationStatus = ApplicationStatus.QUEUED

    # Optional metadata
    company_name: Optional[str] = None
    title: Optional[str] = None
    pay_hourly: Optional[PositiveInt] = None
    pay_yearly: Optional[PositiveInt] = None
    office_city: Optional[str] = None
    office_state: Optional[str] = None
    office_country: Optional[str] = None
    relo_fund: Optional[bool] = None

    @model_validator(mode='after')
    def check_application_date(self):
        if self.date_applied > date.today():
            raise ValueError("Date applied cannot be a date in the future.")
        return self

class CachedQuestion(BaseModel):

    question: str
    answer: str
    hits: PositiveInt = 1

class UserProfile(BaseModel):

    user_id: str

    name: Name
    birth_date: date
    email: EmailStr
    phone: USPhoneNumber
    address: Address

    resume_data: ResumeData
    cache: List[CachedQuestion] = Field(default_factory=list)
    applications: List[Application] = Field(default_factory=list)


    @model_validator(mode='after')
    def atleast_18(self):
        today = date.today()
        age = today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
        if age < 18:
            raise ValueError("You must be at least 18 years old.")
        return self



    


