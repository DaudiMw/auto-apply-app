from utils.upload_resume import extract_skills, extract_contact_info


def test_extract_skills():
    sample_text = """
    Senior Python Developer with 5 years experience in FastAPI, PostgreSQL, and AWS.
    Proficient with Docker, Git, and Streamlit. Knowledgeable in Machine Learning.
    """
    skills = extract_skills(sample_text)
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "PostgreSQL" in skills
    assert "AWS" in skills
    assert "Docker" in skills
    assert "Streamlit" in skills
    assert "Machine Learning" in skills
    assert "Java" not in skills


def test_extract_contact_info():
    sample_text = """
    Jane Doe
    Email: jane.doe@example.com
    Phone: (555) 123-4567
    Location: New York, NY
    """
    contact = extract_contact_info(sample_text)
    assert contact["email"] == "jane.doe@example.com"
    assert "555" in contact["phone"]
    assert "123-4567" in contact["phone"]
