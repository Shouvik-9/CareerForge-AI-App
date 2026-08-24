import os
import json

from dotenv import load_dotenv
from google import genai


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# GEMINI CLIENT
# =========================================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. "
        "Please add it to your .env file."
    )

client = genai.Client(
    api_key=api_key
)


# =========================================================
# BUILD RESUME CONTEXT
# =========================================================

def build_resume_context(resume):

    if resume is None:

        return """
No resume is available.

Create a general roadmap based on the
target career role.
"""

    return f"""
CANDIDATE RESUME

Name:
{resume["name"] or ""}

Email:
{resume["email"] or ""}

Skills:
{resume["skills"] or ""}

Education:
{resume["education"] or ""}

Experience:
{resume["experience"] or ""}

Projects:
{resume["projects"] or ""}

Resume Text:
{resume["resume_text"] or ""}
"""


# =========================================================
# GENERATE CAREER ROADMAP
# =========================================================

def generate_career_roadmap(
    target_role,
    resume_context
):
    """
    Generate a personalized career roadmap using Gemini.
    """

    prompt = f"""
You are an expert career strategist and technical mentor.

Create a personalized career roadmap for a candidate.

TARGET ROLE:
{target_role}

CANDIDATE RESUME:
{resume_context}


IMPORTANT:

The roadmap must use BOTH:

1. The target career role.
2. The candidate's actual resume.

Do not make the roadmap generic if resume information
is available.

Do not invent skills, projects, experience,
qualifications, companies, or achievements.


Generate a practical roadmap covering:

1. Current profile
2. Existing strengths
3. Skill gaps
4. Skills to learn
5. Priority of each skill
6. Recommended learning order
7. Projects to build
8. Tools and technologies to practice
9. Interview preparation
10. A realistic timeline
11. Final preparation checklist


Return ONLY valid JSON.

Use exactly this structure:

{{
    "target_role": "AI Engineer",

    "profile_summary": "Short personalized summary.",

    "strengths": [
        "Strength 1",
        "Strength 2",
        "Strength 3"
    ],

    "skill_gaps": [
        {{
            "skill": "Skill name",
            "priority": "High",
            "reason": "Why this skill is important."
        }}
    ],

    "learning_path": [
        {{
            "phase": "Phase 1",
            "title": "Foundations",
            "duration": "2-3 weeks",
            "topics": [
                "Topic 1",
                "Topic 2",
                "Topic 3"
            ]
        }}
    ],

    "projects": [
        {{
            "title": "Project title",
            "description": "Project description.",
            "skills": [
                "Skill 1",
                "Skill 2"
            ]
        }}
    ],

    "interview_preparation": [
        "Preparation item 1",
        "Preparation item 2",
        "Preparation item 3"
    ],

    "timeline": [
        {{
            "period": "Month 1",
            "goal": "Main goal for this period."
        }}
    ],

    "final_checklist": [
        "Checklist item 1",
        "Checklist item 2",
        "Checklist item 3"
    ]
}}

Make the roadmap realistic for an entry-level candidate.

Prioritize practical skills and projects that improve
job readiness.

Do not include unnecessary filler.
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt
        )

    except Exception as error:

        print(
            "Career Roadmap Gemini error:",
            error
        )

        return None


    if not response or not response.text:

        return None


    text = response.text.strip()

    # Remove markdown code fences
    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    text = text.strip()


    try:

        roadmap = json.loads(text)

    except json.JSONDecodeError:

        print(
            "Gemini returned invalid roadmap JSON."
        )

        return None


    return roadmap