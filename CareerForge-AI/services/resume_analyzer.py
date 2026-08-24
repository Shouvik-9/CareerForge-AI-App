import re
from pypdf import PdfReader
import fitz


SKILL_DATABASE = [
    "Python",
    "Java",
    "C",
    "C++",
    "JavaScript",
    "HTML",
    "CSS",
    "SQL",
    "MySQL",
    "PostgreSQL",
    "MongoDB",
    "Flask",
    "Django",
    "FastAPI",
    "React",
    "Node.js",
    "REST API",
    "Git",
    "GitHub",
    "Docker",
    "AWS",
    "Azure",
    "Google Cloud",
    "Machine Learning",
    "Deep Learning",
    "Artificial Intelligence",
    "AI",
    "NLP",
    "LangChain",
    "RAG",
    "TensorFlow",
    "PyTorch",
]

def extract_pdf_links(file_path):
    """Extract clickable URLs from a PDF using PyMuPDF."""

    links = []

    pdf = fitz.open(file_path)

    for page in pdf:
        page_links = page.get_links()

        for link in page_links:
            url = link.get("uri")

            if url:
                links.append(url)

    pdf.close()

    return links

def clean_text(text):
    """Clean extra spaces and blank lines."""
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_email(text):
    """Find the first email address."""
    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

    match = re.search(pattern, text)

    if match:
        return match.group(0)

    return "Not found"


def extract_phone(text):
    """Find a likely phone number."""
    patterns = [
        r"\+91[-\s]?\d{10}",
        r"\b\d{10}\b",
        r"\+\d{1,3}[-\s]?\d{7,14}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(0)

    return "Not found"


def extract_linkedin(text):
    """Find a LinkedIn profile URL."""
    pattern = r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|pub)/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        url = match.group(0)

        if not url.startswith("http"):
            url = "https://" + url

        return url.rstrip(".,;:)")

    return "Not found"


def extract_github(text):
    """Find a GitHub profile URL."""
    pattern = r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        url = match.group(0)

        if not url.startswith("http"):
            url = "https://" + url

        return url.rstrip(".,;:)")

    return "Not found"


def extract_name(text):
    """
    Try to identify the candidate's name from
    the first few meaningful lines.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    ignored_words = {
        "resume",
        "curriculum vitae",
        "cv",
        "profile",
        "summary",
        "objective",
    }

    for line in lines[:10]:

        lower_line = line.lower()

        if lower_line in ignored_words:
            continue

        if "@" in line:
            continue

        if "linkedin.com" in lower_line:
            continue

        if "github.com" in lower_line:
            continue

        if re.search(r"\d{7,}", line):
            continue

        # Candidate name is usually mostly alphabetic
        if re.fullmatch(r"[A-Za-z][A-Za-z .'-]{2,60}", line):
            words = line.split()

            if 2 <= len(words) <= 5:
                return line

    return "Not found"


def extract_skills(text):
    """Find known skills mentioned in the resume."""

    found_skills = []

    text_lower = text.lower()

    for skill in SKILL_DATABASE:

        skill_lower = skill.lower()

        if skill_lower in text_lower:
            found_skills.append(skill)

    return sorted(found_skills)


def extract_section(text, headings):
    """
    Extract text belonging to a resume section.

    Example:
    headings = ["education", "academic background"]
    """

    lines = text.splitlines()

    start_index = None

    for index, line in enumerate(lines):

        cleaned_line = line.strip().lower()

        if cleaned_line in headings:
            start_index = index + 1
            break

    if start_index is None:
        return "Not found"

    section_lines = []

    common_section_names = {
        "education",
        "experience",
        "work experience",
        "projects",
        "skills",
        "technical skills",
        "certifications",
        "achievements",
        "internships",
        "internship",
    }

    for line in lines[start_index:]:

        cleaned_line = line.strip().lower()

        if cleaned_line in common_section_names:
            break

        if line.strip():
            section_lines.append(line.strip())

    if not section_lines:
        return "Not found"

    return "\n".join(section_lines)


def analyze_resume(text, pdf_links=None):
    """Analyze extracted resume text and PDF hyperlinks."""

    text = clean_text(text)

    linkedin = extract_linkedin(text)
    github = extract_github(text)

    # Check embedded PDF hyperlinks
    if pdf_links:

        for url in pdf_links:

            url_lower = url.lower()

            if "linkedin.com" in url_lower:
                linkedin = url

            elif "github.com" in url_lower:
                # Prefer the main GitHub profile over project links
                if "/preeti47g" in url_lower:
                    github = url

    result = {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "linkedin": linkedin,
        "github": github,
        "skills": extract_skills(text),
        "education": extract_section(
            text,
            {
                "education",
                "academic background",
                "educational qualifications",
            },
        ),
        "experience": extract_section(
            text,
            {
                "experience",
                "work experience",
                "professional experience",
            },
        ),
        "projects": extract_section(
            text,
            {
                "projects",
                "academic projects",
                "personal projects",
            },
        ),
    }

    return result

   