import json
import logging
import os
from typing import Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from data_types import Application, ApplicationStatus, CachedQuestion, UserProfile
from utils.logging_config import hash_id

logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "auto_apply_users")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def get_dynamodb_resource():
    """Initializes and returns the boto3 DynamoDB resource."""
    aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY")
    aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

    if aws_access_key and aws_secret_key:
        return boto3.resource(
            "dynamodb",
            region_name=AWS_REGION,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
        )
    return boto3.resource("dynamodb", region_name=AWS_REGION)


def get_table():
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table(TABLE_NAME)


def profile_to_item(profile: UserProfile) -> dict:
    """Serializes a UserProfile Pydantic model into a DynamoDB-compatible dict."""
    data = profile.model_dump(mode="json")
    data["PK"] = profile.user_id
    return data


def item_to_profile(item: dict) -> UserProfile:
    """Deserializes a DynamoDB item dict back into a UserProfile Pydantic model."""
    cleaned = {k: v for k, v in item.items() if k != "PK"}
    return UserProfile.model_validate(cleaned)


def get_user_profile(user_id: str) -> Optional[UserProfile]:
    """Fetches a user profile from DynamoDB by user_id."""
    try:
        table = get_table()
        response = table.get_item(Key={"PK": user_id})
        item = response.get("Item")
        if not item:
            logger.info("No profile found", extra={"user": hash_id(user_id)})
            return None
        logger.debug("Profile loaded", extra={"user": hash_id(user_id)})
        return item_to_profile(item)
    except (ClientError, BotoCoreError):
        logger.error("Error fetching user profile", extra={"user": hash_id(user_id)}, exc_info=True)
        return None


def save_user_profile(profile: UserProfile) -> bool:
    """Saves or updates a user profile in DynamoDB."""
    try:
        table = get_table()
        item = profile_to_item(profile)
        table.put_item(Item=item)
        logger.info("Profile saved", extra={"user": hash_id(profile.user_id)})
        return True
    except (ClientError, BotoCoreError):
        logger.error("Error saving user profile", extra={"user": hash_id(profile.user_id)}, exc_info=True)
        return False


def add_or_update_application(user_id: str, application: Application) -> bool:
    """Adds a new application or updates an existing one for a user."""
    profile = get_user_profile(user_id)
    if not profile:
        logger.warning("add_or_update_application skipped: profile not found", extra={"user": hash_id(user_id)})
        return False

    existing_idx = next(
        (i for i, a in enumerate(profile.applications) if a.application_id == application.application_id),
        None,
    )

    if existing_idx is not None:
        profile.applications[existing_idx] = application
    else:
        profile.applications.append(application)

    return save_user_profile(profile)


def update_application_status(user_id: str, app_id: str, new_status: ApplicationStatus) -> bool:
    """Updates the status of an existing application."""
    profile = get_user_profile(user_id)
    if not profile:
        logger.warning("update_application_status skipped: profile not found", extra={"user": hash_id(user_id)})
        return False

    for app in profile.applications:
        if app.application_id == app_id:
            app.status = new_status
            logger.info(
                "Application status updated",
                extra={"user": hash_id(user_id), "application_id": app_id, "status": new_status.value},
            )
            return save_user_profile(profile)

    logger.warning("Application not found", extra={"user": hash_id(user_id), "application_id": app_id})
    return False


def upsert_cached_question(user_id: str, question: str, answer: str) -> bool:
    """Adds or updates an answer for a screening question."""
    profile = get_user_profile(user_id)
    if not profile:
        logger.warning("upsert_cached_question skipped: profile not found", extra={"user": hash_id(user_id)})
        return False

    norm_q = question.strip().lower()
    for cached in profile.cache:
        if cached.question.strip().lower() == norm_q:
            cached.answer = answer
            cached.hits += 1
            return save_user_profile(profile)

    profile.cache.append(CachedQuestion(question=question.strip(), answer=answer.strip(), hits=1))
    return save_user_profile(profile)
