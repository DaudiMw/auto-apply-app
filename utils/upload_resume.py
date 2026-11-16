import io
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


COMMON_SKILLS_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "DynamoDB", "Redis",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Linux", "Git", "CI/CD",
    "React", "Vue", "Angular", "Next.js", "Django", "FastAPI", "Flask", "Streamlit",
    "Node.js", "GraphQL", "REST API", "Microservices", "Playwright", "Selenium",
    "Pandas", "NumPy", "PyTorch", "TensorFlow", "Scikit-Learn", "Machine Learning"
]


def extract_text_from_file(uploaded_file) -> str:
    """Extracts raw text content from uploaded file (TXT, PDF, etc.)."""
    if uploaded_file is None:
        return ""

    try:
        # Check if it has getbuffer or read
        content_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()

        # Try utf-8 decoding for plain text
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            pass

        # If it's a PDF, extract ASCII / text streams safely
        try:
            # Fallback stream extraction for PDF
            text_chunks = re.findall(rb"\((.*?)\)[\r\n\s]*Tj|\[(.*?)\][\r\n\s]*TJ", content_bytes)
            extracted = " ".join(
                [c[0].decode("latin-1", errors="ignore") for c in text_chunks if c[0]]
            )
            if extracted.strip():
                return extracted
        except Exception:
            logger.warning("PDF text stream extraction failed", exc_info=True)

        return content_bytes.decode("latin-1", errors="ignore")

    except Exception:
        logger.error("Failed to read uploaded resume file", exc_info=True)
        return ""


def extract_skills(text: str) -> List[str]:
    """Finds common technical skills mentioned in the resume text."""
    if not text:
        return []

    found_skills: List[str] = []
    text_lower = text.lower()

    for skill in COMMON_SKILLS_KEYWORDS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return sorted(list(set(found_skills)))


def extract_contact_info(text: str) -> Dict[str, str]:
    """Extracts email and phone number from resume text using regex."""
    info = {"email": "", "phone": ""}
    if not text:
        return info

    # Email extraction
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if email_match:
        info["email"] = email_match.group(0)

    # Phone extraction (e.g. +1 (123) 456-7890 or 123-456-7890)
    phone_match = re.search(r"(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text)
    if phone_match:
        info["phone"] = phone_match.group(0)

    return info


def parse_resume_file(uploaded_file) -> Dict[str, Any]:
    """Main parsing entry point for resume files."""
    raw_text = extract_text_from_file(uploaded_file)
    contact = extract_contact_info(raw_text)
    skills = extract_skills(raw_text)

    return {
        "raw_text": raw_text,
        "email": contact.get("email", ""),
        "phone": contact.get("phone", ""),
        "skills": skills,
    }
