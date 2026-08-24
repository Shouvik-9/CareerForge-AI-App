import os
import json

from dotenv import load_dotenv
from google import genai


# Load environment variables
load_dotenv()


# Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def get_questions(role, interview_type):
    """
    Generate the first set of possible interview questions.

    These questions are used only to obtain the first question.
    The remaining questions will be generated adaptively.
    """

    prompt = f"""
You are an expert technical interviewer.

Candidate role:
{role}

Interview type:
{interview_type}

Generate 8 possible interview questions that could be used
for this interview.

Requirements:

- Questions must be relevant to the selected role.
- For Technical interviews, focus on technical knowledge,
  programming, databases, frameworks, tools, system concepts,
  and practical problem solving.
- Include a mixture of easy, medium, and difficult questions.
- Do not provide answers.
- Do not ask unrelated questions.
- Return ONLY a JSON array of questions.

Example:

[
    "What is supervised learning?",
    "What is overfitting?",
    "How would you deploy a machine learning model?"
]
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    text = response.text.strip()

    # Remove markdown code fences if Gemini adds them
    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()

    try:

        questions = json.loads(text)

        if isinstance(questions, list):

            return [
                str(question)
                for question in questions
            ]

    except json.JSONDecodeError:
        pass

    # Fallback
    return [
        f"What are the most important technical concepts for a {role}?",
        f"What technologies are commonly used by a {role}?",
        f"Explain an important concept related to {role}.",
        f"Describe a technical problem faced by a {role}.",
        f"How would you solve a difficult problem as a {role}?",
        f"How would you improve a system related to {role}?",
        f"Describe a project relevant to {role}.",
        f"What are common challenges faced by a {role}?"
    ]


def build_resume_context(resume):
    """
    Convert the user's SQLite resume row into
    context that Gemini can understand.
    """

    if resume is None:
        return """
No resume is available.

Generate questions based only on the
selected role and interview type.
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

def get_next_question(
    role,
    interview_type,
    previous_question,
    previous_answer,
    resume_context
):
    """
    Generate the next adaptive interview question.

    Gemini considers:
    - selected role
    - interview type
    - candidate resume
    - previous question
    - previous answer
    """

    prompt = f"""
You are an expert adaptive technical interviewer.

The candidate is applying for:

ROLE:
{role}

INTERVIEW TYPE:
{interview_type}


CANDIDATE RESUME:
{resume_context}


PREVIOUS QUESTION:
{previous_question}


CANDIDATE'S PREVIOUS ANSWER:
{previous_answer}


Your task is to generate ONE next interview question.

IMPORTANT QUESTION STRATEGY:

The interview must use BOTH:

1. Role-based knowledge
2. Resume-based knowledge

Do NOT make the interview only about the resume.

Some questions should test general technical knowledge
required for the selected role.

Some questions should test technologies, projects,
skills, and experience mentioned in the resume.

Rules:

- The question MUST be relevant to the selected role.
- Use the candidate's resume when appropriate.
- Never invent a project, skill, technology, company,
  qualification, or experience that is not present
  in the resume.
- If the candidate's previous answer was weak or incomplete,
  ask a follow-up question that tests the same concept
  more deeply.
- If the previous answer was strong, increase the difficulty
  or move to a related concept.
- Do not repeat the previous question.
- Do not ask generic questions unrelated to the role.
- For technical interviews, prioritize technical knowledge,
  programming, databases, frameworks, tools, system concepts,
  and practical problem solving.
- Make the question realistic for an actual job interview.
- Return ONLY the question.
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    question = response.text.strip()

    # Remove accidental markdown formatting
    question = question.replace("```", "")
    question = question.strip()

    return question
def get_first_question(
    role,
    interview_type,
    resume_context
):
    """
    Generate the first interview question using:
    - selected role
    - interview type
    - candidate resume
    """

    prompt = f"""
You are an expert technical interviewer.

Candidate role:
{role}

Interview type:
{interview_type}

Candidate resume:
{resume_context}

Generate ONE strong opening interview question.

The interview must use BOTH:

1. General knowledge required for the selected role.
2. Information found in the candidate's resume.

Rules:

- The question must be relevant to the selected role.
- It should be suitable as the first question.
- It may be role-based or resume-based.
- Do not make the entire interview dependent on the resume.
- If the resume contains relevant projects or skills, you may ask about them.
- Never invent any project, skill, technology, company, qualification,
  or experience that is not present in the resume.
- For a technical interview, prefer a technical question rather than
  a generic HR question.
- Return ONLY the question.
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    question = response.text.strip()

    question = question.replace("```", "")
    question = question.strip()

    return question