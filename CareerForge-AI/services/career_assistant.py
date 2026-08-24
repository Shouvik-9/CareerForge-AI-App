import os

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
    """
    Convert the SQLite resume row into text for Gemini.
    """

    if resume is None:

        return """
No resume is available.

Give general career guidance based on
the user's question.
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
# FORMAT CONVERSATION HISTORY
# =========================================================

def format_conversation_history(
    conversation_history
):

    if not conversation_history:
        return "No previous conversation."

    history_text = ""

    for message in conversation_history:

        role = message.get(
            "role",
            ""
        )

        content = message.get(
            "content",
            ""
        )

        if not content:
            continue

        if role == "user":

            history_text += (
                f"USER:\n"
                f"{content}\n\n"
            )

        elif role == "assistant":

            history_text += (
                f"CAREERPILOT AI:\n"
                f"{content}\n\n"
            )

    return history_text.strip()


# =========================================================
# DETECT CONVERSATION END INTENT
# =========================================================

def is_exit_intent(text):
    """
    Detect whether the user wants to end
    the Career Assistant conversation.
    """

    if not text:
        return False

    normalized = (
        text.lower()
        .strip()
        .replace(",", " ")
        .replace(".", " ")
        .replace("!", " ")
        .replace("?", " ")
        .replace("'", "")
        .replace('"', "")
    )

    # Normalize repeated spaces
    normalized = " ".join(
        normalized.split()
    )

    exit_phrases = [

        # Thanks / completion
        "thank you thats all",
        "thanks thats all",
        "thank you thats it",
        "thanks thats it",
        "no thank you thats all",
        "no thanks thats all",
        "no thank you",
        "no thanks",

        # Nothing more
        "nothing else",
        "nothing more",
        "i dont need anything else",
        "i dont need anything more",
        "i do not need anything else",
        "i do not need anything more",

        # Explicit ending
        "thats all",
        "thats it",
        "that is all",
        "that is it",
        "im done",
        "i am done",
        "im finished",
        "i am finished",
        "no more questions",

        # Goodbye
        "goodbye",
        "good bye",
        "bye",
        "see you",
        "see you later",

        # End request
        "end conversation",
        "end the conversation",
        "stop the conversation",
        "stop chatting",
        "i want to end",
        "i want to stop",
        "i want to leave"
    ]

    return normalized in exit_phrases


# =========================================================
# CAREER ASSISTANT
# =========================================================

def ask_career_ai(
    question,
    resume_context,
    conversation_history=None
):
    """
    Generate a personalized Career Assistant response.

    Gemini returns ONLY the actual answer.
    The continuation prompt is handled separately
    by the frontend.
    """

    if conversation_history is None:
        conversation_history = []


    # -----------------------------------------------------
    # Previous conversation
    # -----------------------------------------------------

    history_text = format_conversation_history(
        conversation_history
    )


    # -----------------------------------------------------
    # Prompt
    # -----------------------------------------------------

    prompt = f"""
You are CareerPilot AI, a friendly, professional,
and practical career assistant.

You help candidates with:

- Career planning
- Resume improvement
- Interview preparation
- Technical career questions
- Skill development
- Job preparation
- Placement preparation
- Learning plans
- Project ideas
- Career transitions
- Career decisions


=========================================================
CANDIDATE RESUME
=========================================================

{resume_context}


=========================================================
PREVIOUS CONVERSATION
=========================================================

{history_text}


=========================================================
CURRENT USER QUESTION
=========================================================

{question}


=========================================================
INSTRUCTIONS
=========================================================

1. Answer ONLY the user's current question.

2. Use the candidate's resume whenever it is relevant.

3. Personalize the answer using the candidate's actual:
   - skills
   - projects
   - education
   - experience

4. Never invent:
   - skills
   - projects
   - companies
   - qualifications
   - experience
   - achievements

5. Maintain continuity with the previous conversation.

6. Understand references such as:
   "that project"
   "the second one"
   "what you mentioned earlier"
   "what should I learn next"
   "can you explain that"

7. Do not repeat information unnecessarily.

8. Be friendly and conversational.

9. Give practical and actionable advice.

10. For technical questions, explain concepts clearly.

11. Do NOT add:
    "Is there anything else you'd like to know?"
    "Can I help you with anything else?"
    "Would you like help with anything else?"
    or similar closing questions.

12. Do NOT say goodbye.

13. Do NOT end the conversation.

14. The website will provide the continuation prompt
    separately.

15. Return ONLY the actual answer to the user's question.
"""


    # -----------------------------------------------------
    # Gemini request
    # -----------------------------------------------------

    try:

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt
        )

    except Exception as error:

        print(
            "Career Assistant Gemini error:",
            error
        )

        return (
            "I'm sorry, I couldn't process that "
            "right now. Please try again."
        )


    # -----------------------------------------------------
    # Check response
    # -----------------------------------------------------

    if not response or not response.text:

        return (
            "I couldn't generate a response "
            "right now. Please try again."
        )


    return response.text.strip()