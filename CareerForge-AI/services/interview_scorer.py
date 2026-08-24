import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def evaluate_answer(answer, question, role):
    """
    Evaluate the candidate's answer using Gemini.
    """

    prompt = f"""
You are an expert technical interviewer and evaluator.

Candidate's target role:
{role}

Interview question:
{question}

Candidate's answer:
{answer}

Evaluate the candidate's answer specifically for the target role.

Consider:

1. Technical correctness
2. Relevance to the question
3. Depth of understanding
4. Practical knowledge
5. Clarity
6. Communication

Give a score from 0 to 10.

Return ONLY valid JSON in this exact format:

{{
    "score": 8,
    "feedback": "Overall evaluation of the answer.",
    "strengths": [
        "Strength 1",
        "Strength 2"
    ],
    "improvements": [
        "Improvement 1",
        "Improvement 2"
    ]
}}
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
        result = json.loads(text)

        return {
            "score": int(result.get("score", 0)),
            "feedback": result.get(
                "feedback",
                "No feedback available."
            ),
            "strengths": result.get(
                "strengths",
                []
            ),
            "improvements": result.get(
                "improvements",
                []
            )
        }

    except (json.JSONDecodeError, ValueError, TypeError):

        return {
            "score": 0,
            "feedback": "Unable to process AI evaluation.",
            "strengths": [],
            "improvements": [
                "Please try answering the question again."
            ]
        }
def generate_final_report(role, interview_type, questions, answers, evaluations):
    """
    Generate an overall AI interview report using Gemini.
    """

    interview_data = []

    for i in range(len(questions)):
        interview_data.append({
            "question": questions[i],
            "answer": answers[i],
            "evaluation": evaluations[i]
        })

    prompt = f"""
You are an expert technical interviewer.

Generate a final interview performance report for this candidate.

Role:
{role}

Interview Type:
{interview_type}

Interview Data:
{json.dumps(interview_data, indent=2)}

Analyze the candidate's complete performance.

Evaluate:

1. Overall performance
2. Technical knowledge
3. Problem-solving ability
4. Communication
5. Strengths
6. Weaknesses
7. Topics that need improvement
8. Hiring recommendation

Give an overall score from 0 to 100.

Return ONLY valid JSON in this exact structure:

{{
    "overall_score": 78,
    "technical_score": 82,
    "problem_solving_score": 76,
    "communication_score": 74,
    "summary": "Overall performance summary.",
    "strengths": [
        "Strength 1",
        "Strength 2",
        "Strength 3"
    ],
    "weaknesses": [
        "Weakness 1",
        "Weakness 2"
    ],
    "topics_to_improve": [
        "Topic 1",
        "Topic 2",
        "Topic 3"
    ],
    "recommendation": "Suitable for an entry-level role, but needs improvement in ..."
}}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    text = response.text.strip()

    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:

        return {
            "overall_score": 0,
            "technical_score": 0,
            "problem_solving_score": 0,
            "communication_score": 0,
            "summary": "AI could not generate the final report.",
            "strengths": [],
            "weaknesses": [],
            "topics_to_improve": [],
            "recommendation": "Please try the interview again."
        }