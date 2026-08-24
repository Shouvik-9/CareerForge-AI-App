import os
from functools import wraps
import webbrowser
from io import BytesIO

from dotenv import load_dotenv

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file,
)

from flask_session import Session

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

from werkzeug.utils import secure_filename

from pypdf import PdfReader

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from services.resume_analyzer import (
    analyze_resume,
    extract_pdf_links,
)

from services.ats_scorer import (
    calculate_ats_score,
)

from services.resume_scorer import (
    calculate_resume_score,
)

from services.job_matcher import (
    calculate_job_match,
)

from services.skill_gap import (
    generate_skill_gap,
)

from database.database import (
    initialize_database,
    save_resume,
    get_latest_resume,
    save_job_match,
    get_latest_job_match,
    create_user,
    get_user_by_email,
)

from services.interview_ai import (
    get_questions,
    get_first_question,
    get_next_question,
    build_resume_context as build_interview_resume_context,
)

from services.career_assistant import (
    ask_career_ai,
    build_resume_context as build_assistant_resume_context,
    is_exit_intent,
)

from services.career_roadmap import (
    generate_career_roadmap,
)

from services.interview_scorer import (
    evaluate_answer,
    generate_final_report,
)


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)


# =========================================================
# SECRET KEY
# =========================================================

app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY is missing. Please add it to your .env file."
    )


# =========================================================
# FLASK SESSION CONFIGURATION
# =========================================================

app.config["SESSION_TYPE"] = "filesystem"

app.config["SESSION_FILE_DIR"] = os.path.join(
    app.root_path,
    "flask_session",
)

app.config["SESSION_PERMANENT"] = False

app.config["SESSION_USE_SIGNER"] = True

Session(app)


# =========================================================
# APPLICATION CONFIGURATION
# =========================================================

UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "uploads",
)

ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================================================
# INITIALIZE DATABASE
# =========================================================

initialize_database()


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login or create an account to use this tool."
            )

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return decorated_function


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def allowed_file(filename):
    """Check whether the uploaded file is a PDF."""

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def extract_pdf_text(file_path):
    """Extract all readable text from a PDF."""

    reader = PdfReader(file_path)

    pages_text = []

    for page in reader.pages:

        text = page.extract_text()

        if text:
            pages_text.append(text)

    return "\n\n".join(pages_text)


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# CAREER ASSISTANT
# =========================================================

@app.route(
    "/career-assistant",
    methods=["GET", "POST"],
)
@login_required
def career_assistant():

    # -----------------------------------------------------
    # Load conversation history
    # -----------------------------------------------------

    conversation = session.get(
        "career_assistant_conversation",
        [],
    )

    conversation_ended = session.get(
        "career_assistant_ended",
        False,
    )

    # -----------------------------------------------------
    # Handle user message
    # -----------------------------------------------------

    if request.method == "POST":

        question = request.form.get(
            "question",
            "",
        ).strip()

        # -------------------------------------------------
        # Validate question
        # -------------------------------------------------

        if not question:

            flash(
                "Please enter a question."
            )

            return redirect(
                url_for("career_assistant")
            )

        # -------------------------------------------------
        # If conversation has already ended
        # -------------------------------------------------

        if conversation_ended:

            return redirect(
                url_for("career_assistant")
            )

        # =================================================
        # CHECK WHETHER USER WANTS TO END CONVERSATION
        # =================================================

        if is_exit_intent(question):

            # ---------------------------------------------
            # Save user's final message
            # ---------------------------------------------

            conversation.append({
                "role": "user",
                "content": question,
            })

            # ---------------------------------------------
            # Add final friendly AI message
            # ---------------------------------------------

            final_message = (
                "You're very welcome! "
                "I'm glad I could help. "
                "Have a great day and all the best "
                "with your career journey!"
            )

            conversation.append({
                "role": "assistant",
                "content": final_message,
            })

            # ---------------------------------------------
            # Save ended state
            # ---------------------------------------------

            session[
                "career_assistant_conversation"
            ] = conversation

            session[
                "career_assistant_ended"
            ] = True

            session.modified = True

            # ---------------------------------------------
            # Show ended conversation
            # ---------------------------------------------

            return render_template(
                "career_assistant.html",
                conversation=conversation,
                conversation_ended=True,
            )

        # =================================================
        # NORMAL CAREER QUESTION
        # =================================================

        # -------------------------------------------------
        # Get latest resume
        # -------------------------------------------------

        resume = get_latest_resume(
            session["user_id"]
        )

        # -------------------------------------------------
        # Build resume context
        # -------------------------------------------------

        resume_context = build_assistant_resume_context(
            resume
        )

        # -------------------------------------------------
        # Ask Gemini
        # -------------------------------------------------

        answer = ask_career_ai(
            question,
            resume_context,
            conversation,
        )

        # -------------------------------------------------
        # Save user message
        # -------------------------------------------------

        conversation.append({
            "role": "user",
            "content": question,
        })

        # -------------------------------------------------
        # Save AI response
        # -------------------------------------------------

        conversation.append({
            "role": "assistant",
            "content": answer,
        })

        # -------------------------------------------------
        # Save conversation
        # -------------------------------------------------

        session[
            "career_assistant_conversation"
        ] = conversation

        session[
            "career_assistant_ended"
        ] = False

        session.modified = True

    # -----------------------------------------------------
    # Render page
    # -----------------------------------------------------

    return render_template(
        "career_assistant.html",
        conversation=conversation,
        conversation_ended=conversation_ended,
    )


# =========================================================
# EXIT CAREER ASSISTANT
# =========================================================

@app.route(
    "/career-assistant/exit",
    methods=["POST"],
)
@login_required
def exit_career_assistant():

    session.pop(
        "career_assistant_conversation",
        None,
    )

    session.pop(
        "career_assistant_ended",
        None,
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# CAREER ROADMAP
# =========================================================

@app.route(
    "/career-roadmap",
    methods=["GET", "POST"],
)
@login_required
def career_roadmap():

    roadmap = None

    if request.method == "POST":

        target_role = request.form.get(
            "target_role",
            "",
        ).strip()

        if not target_role:

            flash(
                "Please enter your target career role."
            )

            return redirect(
                url_for("career_roadmap")
            )

        # -------------------------------------------------
        # Get latest resume
        # -------------------------------------------------

        resume = get_latest_resume(
            session["user_id"]
        )

        # -------------------------------------------------
        # Build resume context
        # -------------------------------------------------

        resume_context = (
            build_assistant_resume_context(
                resume
            )
        )

        # -------------------------------------------------
        # Generate roadmap
        # -------------------------------------------------

        roadmap = generate_career_roadmap(
            target_role,
            resume_context,
        )

        if not roadmap:

            flash(
                "Unable to generate the roadmap. "
                "Please try again."
            )

            return redirect(
                url_for("career_roadmap")
            )

        # -------------------------------------------------
        # Save roadmap in server-side session
        # -------------------------------------------------

        session[
            "career_roadmap"
        ] = roadmap

        session[
            "career_roadmap_role"
        ] = target_role

        session.modified = True

    else:

        # -------------------------------------------------
        # Load existing roadmap if available
        # -------------------------------------------------

        roadmap = session.get(
            "career_roadmap"
        )

    return render_template(
        "career_roadmap.html",
        roadmap=roadmap,
    )


# =========================================================
# DOWNLOAD CAREER ROADMAP PDF
# =========================================================

@app.route(
    "/career-roadmap/download-pdf",
    methods=["GET"],
)
@login_required
def download_career_roadmap_pdf():

    roadmap = session.get(
        "career_roadmap"
    )

    if not roadmap:

        flash(
            "Please generate a career roadmap first."
        )

        return redirect(
            url_for("career_roadmap")
        )

    # -----------------------------------------------------
    # Create PDF in memory
    # -----------------------------------------------------

    pdf_buffer = BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "RoadmapTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=22,
        spaceAfter=20,
    )

    heading_style = ParagraphStyle(
        "RoadmapHeading",
        parent=styles["Heading2"],
        fontSize=15,
        spaceBefore=15,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "RoadmapBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        spaceAfter=7,
    )

    small_style = ParagraphStyle(
        "RoadmapSmall",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        spaceAfter=5,
    )

    story = []

    # -----------------------------------------------------
    # Title
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "CareerForge AI - Career Roadmap",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"Target Role: "
            f"{roadmap.get('target_role', '')}",
            body_style,
        )
    )

    story.append(
        Spacer(1, 10)
    )

    # -----------------------------------------------------
    # Profile
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Current Profile",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            roadmap.get(
                "profile_summary",
                "",
            ),
            body_style,
        )
    )

    # -----------------------------------------------------
    # Strengths
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Strengths",
            heading_style,
        )
    )

    for strength in roadmap.get(
        "strengths",
        [],
    ):

        story.append(
            Paragraph(
                f"- {strength}",
                body_style,
            )
        )

    # -----------------------------------------------------
    # Skill gaps
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Skill Gaps",
            heading_style,
        )
    )

    skill_gap_data = [
        [
            "Skill",
            "Priority",
            "Reason",
        ]
    ]

    for gap in roadmap.get(
        "skill_gaps",
        [],
    ):

        skill_gap_data.append([
            gap.get(
                "skill",
                "",
            ),
            gap.get(
                "priority",
                "",
            ),
            gap.get(
                "reason",
                "",
            ),
        ])

    if len(skill_gap_data) > 1:

        table = Table(
            skill_gap_data,
            colWidths=[
                110,
                70,
                310,
            ],
            repeatRows=1,
        )

        table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.black,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ])
        )

        story.append(table)

    # -----------------------------------------------------
    # Learning path
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Learning Path",
            heading_style,
        )
    )

    for phase in roadmap.get(
        "learning_path",
        [],
    ):

        story.append(
            Paragraph(
                (
                    f"<b>{phase.get('phase', '')} - "
                    f"{phase.get('title', '')}</b>"
                ),
                body_style,
            )
        )

        story.append(
            Paragraph(
                (
                    f"Duration: "
                    f"{phase.get('duration', '')}"
                ),
                small_style,
            )
        )

        for topic in phase.get(
            "topics",
            [],
        ):

            story.append(
                Paragraph(
                    f"- {topic}",
                    small_style,
                )
            )

    # -----------------------------------------------------
    # Projects
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Projects to Build",
            heading_style,
        )
    )

    for project in roadmap.get(
        "projects",
        [],
    ):

        story.append(
            Paragraph(
                f"<b>{project.get('title', '')}</b>",
                body_style,
            )
        )

        story.append(
            Paragraph(
                project.get(
                    "description",
                    "",
                ),
                small_style,
            )
        )

        skills = ", ".join(
            project.get(
                "skills",
                [],
            )
        )

        story.append(
            Paragraph(
                f"Skills: {skills}",
                small_style,
            )
        )

    # -----------------------------------------------------
    # Interview preparation
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Interview Preparation",
            heading_style,
        )
    )

    for item in roadmap.get(
        "interview_preparation",
        [],
    ):

        story.append(
            Paragraph(
                f"- {item}",
                body_style,
            )
        )

    # -----------------------------------------------------
    # Timeline
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Recommended Timeline",
            heading_style,
        )
    )

    for item in roadmap.get(
        "timeline",
        [],
    ):

        story.append(
            Paragraph(
                (
                    f"<b>{item.get('period', '')}</b>: "
                    f"{item.get('goal', '')}"
                ),
                body_style,
            )
        )

    # -----------------------------------------------------
    # Final checklist
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Final Job-Readiness Checklist",
            heading_style,
        )
    )

    for item in roadmap.get(
        "final_checklist",
        [],
    ):

        story.append(
            Paragraph(
                f"- {item}",
                body_style,
            )
        )

    # -----------------------------------------------------
    # Build PDF
    # -----------------------------------------------------

    document.build(
        story
    )

    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="CareerForge_AI_Career_Roadmap.pdf",
    )


# =========================================================
# RESUME UPLOAD
# =========================================================

@app.route(
    "/upload-resume",
    methods=["POST"],
)
@login_required
def upload_resume():
    """Upload, read and analyze a resume PDF."""

    # -----------------------------------------------------
    # Check whether a file was submitted
    # -----------------------------------------------------

    if "resume" not in request.files:

        flash(
            "Please select a resume PDF."
        )

        return redirect(
            url_for("home")
        )

    file = request.files["resume"]

    # -----------------------------------------------------
    # Check whether the user selected a file
    # -----------------------------------------------------

    if file.filename == "":

        flash(
            "Please select a resume PDF."
        )

        return redirect(
            url_for("home")
        )

    # -----------------------------------------------------
    # Check file type
    # -----------------------------------------------------

    if not allowed_file(file.filename):

        flash(
            "Only PDF files are allowed."
        )

        return redirect(
            url_for("home")
        )

    # -----------------------------------------------------
    # Create a safe filename
    # -----------------------------------------------------

    filename = secure_filename(
        file.filename
    )

    # -----------------------------------------------------
    # Make sure uploads folder exists
    # -----------------------------------------------------

    os.makedirs(
        app.config["UPLOAD_FOLDER"],
        exist_ok=True,
    )

    # -----------------------------------------------------
    # Create complete file path
    # -----------------------------------------------------

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename,
    )

    # -----------------------------------------------------
    # Save uploaded PDF
    # -----------------------------------------------------

    file.save(file_path)

    # -----------------------------------------------------
    # Extract text from PDF
    # -----------------------------------------------------

    resume_text = extract_pdf_text(
        file_path
    )

    # -----------------------------------------------------
    # Check whether text was extracted
    # -----------------------------------------------------

    if not resume_text.strip():

        flash(
            "The PDF was uploaded, but no readable text was found. "
            "Try a text-based PDF rather than a scanned image."
        )

        return redirect(
            url_for("home")
        )

    # -----------------------------------------------------
    # Extract clickable PDF links
    # -----------------------------------------------------

    pdf_links = extract_pdf_links(
        file_path
    )

    # -----------------------------------------------------
    # Analyze resume
    # -----------------------------------------------------

    resume_data = analyze_resume(
        resume_text,
        pdf_links,
    )

    # -----------------------------------------------------
    # Calculate resume score
    # -----------------------------------------------------

    resume_score, score_breakdown = (
        calculate_resume_score(
            resume_data,
            pdf_links,
        )
    )

    # -----------------------------------------------------
    # Save resume in database
    # -----------------------------------------------------

    resume_id = save_resume(
        session["user_id"],
        filename,
        resume_data,
        resume_text,
        resume_score,
    )

    # -----------------------------------------------------
    # Save extracted text temporarily
    # -----------------------------------------------------

    with open(
        os.path.join(
            app.root_path,
            "resume_text.txt",
        ),
        "w",
        encoding="utf-8",
    ) as text_file:

        text_file.write(
            resume_text
        )

    # -----------------------------------------------------
    # Display resume analysis
    # -----------------------------------------------------

    return render_template(
        "resume_result.html",
        filename=filename,
        resume_text=resume_text,
        resume_data=resume_data,
        pdf_links=pdf_links,
        resume_score=resume_score,
        score_breakdown=score_breakdown,
    )


# =========================================================
# JOB MATCHER
# =========================================================

@app.route(
    "/job-match",
    methods=["GET", "POST"],
)
@login_required
def job_match():
    """Compare the latest uploaded resume with a job description."""

    if request.method == "GET":

        return render_template(
            "job_match.html"
        )

    job_description = request.form.get(
        "job_description",
        "",
    ).strip()

    if not job_description:

        flash(
            "Please enter a job description."
        )

        return redirect(
            url_for("job_match")
        )

    # -----------------------------------------------------
    # Get latest uploaded resume
    # -----------------------------------------------------

    resume = get_latest_resume(
        session["user_id"]
    )

    if resume is None:

        flash(
            "Please upload a resume before using Job Matcher."
        )

        return redirect(
            url_for("home")
        )

    # -----------------------------------------------------
    # Convert database row into resume_data
    # -----------------------------------------------------

    resume_data = {
        "name": resume["name"],
        "email": resume["email"],
        "phone": resume["phone"],
        "linkedin": resume["linkedin"],
        "github": resume["github"],
        "skills": [
            skill.strip()
            for skill in (
                resume["skills"] or ""
            ).split(",")
            if skill.strip()
        ],
        "education": resume["education"],
        "experience": resume["experience"],
        "projects": resume["projects"],
    }

    # -----------------------------------------------------
    # Compare resume with job description
    # -----------------------------------------------------

    match_result = calculate_job_match(
        resume_data,
        job_description,
    )

    # -----------------------------------------------------
    # Generate skill-gap report
    # -----------------------------------------------------

    skill_gap = generate_skill_gap(
        match_result
    )

    # -----------------------------------------------------
    # Save job-match result
    # -----------------------------------------------------

    save_job_match(
        resume["id"],
        job_description,
        match_result,
    )

    return render_template(
        "job_match_result.html",
        match_result=match_result,
        skill_gap=skill_gap,
    )


# =========================================================
# INTERVIEW
# =========================================================

@app.route(
    "/interview",
    methods=["GET", "POST"],
)
@login_required
def interview():

    # -----------------------------------------------------
    # Start a new interview
    # -----------------------------------------------------

    if request.method == "POST":

        role = request.form.get(
            "role",
            "",
        ).strip()

        interview_type = request.form.get(
            "interview_type",
            "",
        ).strip()

        # -------------------------------------------------
        # Check required fields
        # -------------------------------------------------

        if not role or not interview_type:

            flash(
                "Please select a role and interview type."
            )

            return redirect(
                url_for("interview")
            )

        # -------------------------------------------------
        # Get user's latest uploaded resume
        # -------------------------------------------------

        resume = get_latest_resume(
            session["user_id"]
        )

        # -------------------------------------------------
        # Convert resume into context for Gemini
        # -------------------------------------------------

        resume_context = (
            build_interview_resume_context(
                resume
            )
        )

        # -------------------------------------------------
        # Generate first personalized question
        # -------------------------------------------------

        first_question = get_first_question(
            role,
            interview_type,
            resume_context,
        )

        # -------------------------------------------------
        # Make sure first question was generated
        # -------------------------------------------------

        if not first_question:

            flash(
                "Unable to generate the first interview "
                "question. Please try again."
            )

            return redirect(
                url_for("interview")
            )

        # -------------------------------------------------
        # Save interview information
        # -------------------------------------------------

        session["interview_role"] = role

        session["interview_type"] = (
            interview_type
        )

        session["interview_resume_context"] = (
            resume_context
        )

        # -------------------------------------------------
        # Store Question 1
        # -------------------------------------------------

        session["interview_questions"] = [
            first_question
        ]

        session["interview_question_numbers"] = [
            1
        ]

        # -------------------------------------------------
        # Candidate answers
        # -------------------------------------------------

        session["interview_answers"] = []

        # -------------------------------------------------
        # AI evaluations
        # -------------------------------------------------

        session["interview_evaluations"] = []

        # -------------------------------------------------
        # Current logical question number
        # -------------------------------------------------

        session["interview_current_number"] = 1

        # -------------------------------------------------
        # Skip counter
        # -------------------------------------------------

        session["interview_skip_attempts"] = 0

        # -------------------------------------------------
        # Show Question 1
        # -------------------------------------------------

        return render_template(
            "interview_question.html",
            role=role,
            interview_type=interview_type,
            question=first_question,
            question_number=1,
            total_questions=8,
            skip_attempts=0,
        )

    # -----------------------------------------------------
    # Show interview start page
    # -----------------------------------------------------

    return render_template(
        "interview.html"
    )


# =========================================================
# INTERVIEW ANSWER
# =========================================================

@app.route(
    "/interview/answer",
    methods=["POST"],
)
@login_required
def interview_answer():

    role = session.get(
        "interview_role"
    )

    interview_type = session.get(
        "interview_type"
    )

    questions = session.get(
        "interview_questions",
        [],
    )

    question_numbers = session.get(
        "interview_question_numbers",
        [],
    )

    answers = session.get(
        "interview_answers",
        [],
    )

    evaluations = session.get(
        "interview_evaluations",
        [],
    )

    current_number = session.get(
        "interview_current_number",
        1,
    )

    # -----------------------------------------------------
    # Get resume context
    # -----------------------------------------------------

    resume_context = session.get(
        "interview_resume_context",
        "No resume information is available.",
    )

    answer = request.form.get(
        "answer",
        "",
    ).strip()

    # -----------------------------------------------------
    # Validate interview
    # -----------------------------------------------------

    if (
        not role
        or not interview_type
        or not questions
    ):

        flash(
            "Please start the interview first."
        )

        return redirect(
            url_for("interview")
        )

    # -----------------------------------------------------
    # Validate answer
    # -----------------------------------------------------

    if not answer:

        flash(
            "Please provide an answer."
        )

        return redirect(
            url_for("interview")
        )

    # -----------------------------------------------------
    # Find current question
    # -----------------------------------------------------

    current_index = len(answers)

    if current_index >= len(questions):

        flash(
            "Interview question not found."
        )

        return redirect(
            url_for("interview")
        )

    current_question = questions[
        current_index
    ]

    # -----------------------------------------------------
    # Save candidate answer
    # -----------------------------------------------------

    answers.append(
        answer
    )

    session["interview_answers"] = (
        answers
    )

    # -----------------------------------------------------
    # Evaluate answer using Gemini
    # -----------------------------------------------------

    evaluation = evaluate_answer(
        answer,
        current_question,
        role,
    )

    evaluations.append(
        evaluation
    )

    session["interview_evaluations"] = (
        evaluations
    )

    # -----------------------------------------------------
    # Reset skip counter
    # -----------------------------------------------------

    session["interview_skip_attempts"] = 0

    # -----------------------------------------------------
    # If Question 8 is answered
    # -----------------------------------------------------

    if current_number >= 8:

        final_report = generate_final_report(
            role,
            interview_type,
            questions,
            answers,
            evaluations,
        )

        return render_template(
            "interview_complete.html",
            role=role,
            interview_type=interview_type,
            questions=questions,
            question_numbers=question_numbers,
            answers=answers,
            evaluations=evaluations,
            final_report=final_report,
        )

    # -----------------------------------------------------
    # Move to next question
    # -----------------------------------------------------

    next_number = (
        current_number + 1
    )

    # -----------------------------------------------------
    # Generate next adaptive question
    # -----------------------------------------------------

    next_question = get_next_question(
        role,
        interview_type,
        current_question,
        answer,
        resume_context,
    )

    # -----------------------------------------------------
    # Store next question
    # -----------------------------------------------------

    questions.append(
        next_question
    )

    question_numbers.append(
        next_number
    )

    session["interview_questions"] = (
        questions
    )

    session["interview_question_numbers"] = (
        question_numbers
    )

    session["interview_current_number"] = (
        next_number
    )

    # -----------------------------------------------------
    # Show next question
    # -----------------------------------------------------

    return render_template(
        "interview_question.html",
        role=role,
        interview_type=interview_type,
        question=next_question,
        question_number=next_number,
        total_questions=8,
        skip_attempts=0,
    )


# =========================================================
# INTERVIEW SKIP
# =========================================================

@app.route(
    "/interview/skip",
    methods=["POST"],
)
@login_required
def interview_skip():

    role = session.get(
        "interview_role"
    )

    interview_type = session.get(
        "interview_type"
    )

    questions = session.get(
        "interview_questions",
        [],
    )

    question_numbers = session.get(
        "interview_question_numbers",
        [],
    )

    answers = session.get(
        "interview_answers",
        [],
    )

    evaluations = session.get(
        "interview_evaluations",
        [],
    )

    current_number = session.get(
        "interview_current_number",
        1,
    )

    skip_attempts = session.get(
        "interview_skip_attempts",
        0,
    )

    # -----------------------------------------------------
    # Get resume context
    # -----------------------------------------------------

    resume_context = session.get(
        "interview_resume_context",
        "No resume information is available.",
    )

    # -----------------------------------------------------
    # Validate interview
    # -----------------------------------------------------

    if (
        not role
        or not interview_type
        or not questions
    ):

        flash(
            "Please start the interview first."
        )

        return redirect(
            url_for("interview")
        )

    # -----------------------------------------------------
    # Find current question
    # -----------------------------------------------------

    current_index = len(answers)

    if current_index >= len(questions):

        flash(
            "Interview question not found."
        )

        return redirect(
            url_for("interview")
        )

    current_question = questions[
        current_index
    ]

    # -----------------------------------------------------
    # Increase skip counter
    # -----------------------------------------------------

    skip_attempts += 1

    session["interview_skip_attempts"] = (
        skip_attempts
    )

    # -----------------------------------------------------
    # Record skipped question
    # -----------------------------------------------------

    skipped_answer = (
        "[Candidate skipped this question.]"
    )

    answers.append(
        skipped_answer
    )

    session["interview_answers"] = (
        answers
    )

    # -----------------------------------------------------
    # Add evaluation for skipped question
    # -----------------------------------------------------

    evaluations.append({
        "score": 0,
        "feedback": (
            "The candidate skipped this question."
        ),
        "strengths": [],
        "improvements": [
            "Review the concepts related "
            "to this question."
        ],
    })

    session["interview_evaluations"] = (
        evaluations
    )

    # -----------------------------------------------------
    # First or second skip
    # -----------------------------------------------------

    if skip_attempts < 3:

        next_question = get_next_question(
            role,
            interview_type,
            current_question,
            skipped_answer,
            resume_context,
        )

        questions.append(
            next_question
        )

        question_numbers.append(
            current_number
        )

        session["interview_questions"] = (
            questions
        )

        session["interview_question_numbers"] = (
            question_numbers
        )

        return render_template(
            "interview_question.html",
            role=role,
            interview_type=interview_type,
            question=next_question,
            question_number=current_number,
            total_questions=8,
            skip_attempts=skip_attempts,
        )

    # -----------------------------------------------------
    # Third skip reached
    # -----------------------------------------------------

    if current_number >= 8:

        final_report = generate_final_report(
            role,
            interview_type,
            questions,
            answers,
            evaluations,
        )

        return render_template(
            "interview_complete.html",
            role=role,
            interview_type=interview_type,
            questions=questions,
            question_numbers=question_numbers,
            answers=answers,
            evaluations=evaluations,
            final_report=final_report,
        )

    # -----------------------------------------------------
    # Move to next logical question
    # -----------------------------------------------------

    next_number = (
        current_number + 1
    )

    # -----------------------------------------------------
    # Generate next adaptive question
    # -----------------------------------------------------

    next_question = get_next_question(
        role,
        interview_type,
        current_question,
        skipped_answer,
        resume_context,
    )

    # -----------------------------------------------------
    # Store next question
    # -----------------------------------------------------

    questions.append(
        next_question
    )

    question_numbers.append(
        next_number
    )

    session["interview_questions"] = (
        questions
    )

    session["interview_question_numbers"] = (
        question_numbers
    )

    session["interview_current_number"] = (
        next_number
    )

    # -----------------------------------------------------
    # Reset skip counter for new question
    # -----------------------------------------------------

    session["interview_skip_attempts"] = 0

    # -----------------------------------------------------
    # Show next question
    # -----------------------------------------------------

    return render_template(
        "interview_question.html",
        role=role,
        interview_type=interview_type,
        question=next_question,
        question_number=next_number,
        total_questions=8,
        skip_attempts=0,
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"],
)
def register():

    if request.method == "GET":

        return render_template(
            "register.html"
        )

    name = request.form.get(
        "name",
        "",
    ).strip()

    email = request.form.get(
        "email",
        "",
    ).strip().lower()

    password = request.form.get(
        "password",
        "",
    )

    # -----------------------------------------------------
    # Check required fields
    # -----------------------------------------------------

    if not name or not email or not password:

        flash(
            "Please fill in all fields.",
            "error",
        )

        return redirect(
            url_for("register")
        )

    # -----------------------------------------------------
    # Check whether account already exists
    # -----------------------------------------------------

    existing_user = get_user_by_email(
        email
    )

    if existing_user:

        flash(
            "An account with this email already exists. "
            "Please login.",
            "error",
        )

        return redirect(
            url_for("login")
        )

    # -----------------------------------------------------
    # Create new account
    # -----------------------------------------------------

    user_id = create_user(
        name,
        email,
        password,
    )

    # -----------------------------------------------------
    # Create login session immediately
    # -----------------------------------------------------

    session["user_id"] = user_id

    session["user_name"] = name

    session["user_email"] = email

    session["user_first_name"] = (
        name.split()[0]
    )

    flash(
        "Account created successfully!",
        "success",
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"],
)
def login():

    if request.method == "GET":

        return render_template(
            "login.html"
        )

    email = request.form.get(
        "email",
        "",
    ).strip().lower()

    password = request.form.get(
        "password",
        "",
    )

    user = get_user_by_email(
        email
    )

    # -----------------------------------------------------
    # Account does not exist
    # -----------------------------------------------------

    if user is None:

        flash(
            "No account found with this email. "
            "Please create an account.",
            "error",
        )

        return redirect(
            url_for("register")
        )

    # -----------------------------------------------------
    # Incorrect password
    # -----------------------------------------------------

    if not check_password_hash(
        user["password_hash"],
        password,
    ):

        flash(
            "Incorrect password. Please try again.",
            "error",
        )

        return redirect(
            url_for("login")
        )

    # -----------------------------------------------------
    # Create session
    # -----------------------------------------------------

    session["user_id"] = user["id"]

    session["user_name"] = user["name"]

    session["user_email"] = user["email"]

    session["user_first_name"] = (
        user["name"].split()[0]
    )

    flash(
        "Logged in successfully!",
        "success",
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# ATS SCORE
# =========================================================

@app.route(
    "/ats-score"
)
@login_required
def ats_score():

    # -----------------------------------------------------
    # Get latest uploaded resume
    # -----------------------------------------------------

    resume = get_latest_resume(
        session["user_id"]
    )

    if resume is None:

        flash(
            "Please upload your resume before checking ATS Score."
        )

        return redirect(
            url_for("home")
        )

    # -----------------------------------------------------
    # Reconstruct resume information
    # -----------------------------------------------------

    resume_data = {
        "name": resume["name"],
        "email": resume["email"],
        "phone": resume["phone"],
        "linkedin": resume["linkedin"],
        "github": resume["github"],
        "skills": [
            skill.strip()
            for skill in (
                resume["skills"] or ""
            ).split(",")
            if skill.strip()
        ],
        "education": resume["education"],
        "experience": resume["experience"],
        "projects": resume["projects"],
        "resume_text": resume["resume_text"],
    }

    # -----------------------------------------------------
    # Calculate ATS score
    # -----------------------------------------------------

    ats_score_value, score_breakdown = (
        calculate_ats_score(
            resume_data
        )
    )

    # -----------------------------------------------------
    # Show ATS score result
    # -----------------------------------------------------

    return render_template(
        "ats_score.html",
        ats_score=ats_score_value,
        score_breakdown=score_breakdown,
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route(
    "/logout"
)
def logout():

    session.clear()

    flash(
        "Logged out successfully!",
        "success",
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    webbrowser.open(
        "http://127.0.0.1:5000"
    )

    app.run(
        debug=True,
        use_reloader=False,
    )