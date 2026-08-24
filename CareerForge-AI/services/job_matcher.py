import re


def extract_keywords(text):
    """
    Extract simple keywords from text.

    This first version focuses on technical/career-related words.
    We will improve this later with AI and NLP.
    """

    technical_terms = [
        "python",
        "java",
        "c",
        "c++",
        "javascript",
        "html",
        "css",
        "sql",
        "mysql",
        "postgresql",
        "mongodb",
        "flask",
        "django",
        "fastapi",
        "react",
        "node.js",
        "rest api",
        "git",
        "github",
        "docker",
        "aws",
        "azure",
        "google cloud",
        "machine learning",
        "deep learning",
        "artificial intelligence",
        "ai",
        "nlp",
        "langchain",
        "rag",
        "tensorflow",
        "pytorch",
        "data structures",
        "algorithms",
        "oops",
        "dbms",
        "operating systems",
        "cloud computing",
    ]

    text_lower = text.lower()

    found = []

    for term in technical_terms:
        if term in text_lower:
            found.append(term)

    return sorted(set(found))


def calculate_job_match(resume_data, job_description):
    """
    Compare resume skills with skills found in the job description.
    """

    resume_skills = [
        skill.lower()
        for skill in resume_data.get("skills", [])
    ]

    job_skills = extract_keywords(job_description)

    if not job_skills:
        return {
            "match_percentage": 0,
            "matched_skills": [],
            "missing_skills": [],
            "job_skills": [],
        }

    matched_skills = []
    missing_skills = []

    for skill in job_skills:

        if skill in resume_skills:
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)

    match_percentage = round(
        (len(matched_skills) / len(job_skills)) * 100,
        2
    )

    return {
        "match_percentage": match_percentage,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "job_skills": job_skills,
    }