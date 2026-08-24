import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = BASE_DIR / "careerforge.db"


def get_connection():
    """Create a connection to the SQLite database."""

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    """Create the required database tables."""

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        filename TEXT NOT NULL,
        name TEXT,
        email TEXT,
        phone TEXT,
        linkedin TEXT,
        github TEXT,
        skills TEXT,
        education TEXT,
        experience TEXT,
        projects TEXT,
        resume_text TEXT,
        resume_score INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")
    # Add user_id to existing databases if it is missing
    cursor.execute("PRAGMA table_info(resumes)")
    columns = [
       row["name"]
       for row in cursor.fetchall()
   ]
   
    if "user_id" not in columns:
   
       cursor.execute(
           "ALTER TABLE resumes ADD COLUMN user_id INTEGER"
       )
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_id INTEGER NOT NULL,
            job_description TEXT NOT NULL,
            match_percentage REAL,
            matched_skills TEXT,
            missing_skills TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resume_id) REFERENCES resumes(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()

    connection.close()


def save_resume(
    user_id,
    filename,
    resume_data,
    resume_text,
    resume_score
):
    """Save an analyzed resume for a specific user."""

    connection = get_connection()

    cursor = connection.cursor()

    skills = ", ".join(
        resume_data.get("skills", [])
    )

    cursor.execute(
        """
        INSERT INTO resumes (
            user_id,
            filename,
            name,
            email,
            phone,
            linkedin,
            github,
            skills,
            education,
            experience,
            projects,
            resume_text,
            resume_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            filename,
            resume_data.get("name"),
            resume_data.get("email"),
            resume_data.get("phone"),
            resume_data.get("linkedin"),
            resume_data.get("github"),
            skills,
            resume_data.get("education"),
            resume_data.get("experience"),
            resume_data.get("projects"),
            resume_text,
            resume_score,
        )
    )

    connection.commit()

    resume_id = cursor.lastrowid

    connection.close()

    return resume_id

def save_job_match(
    resume_id,
    job_description,
    match_result
):
    """Save a job-match result in the database."""

    connection = get_connection()

    cursor = connection.cursor()

    matched_skills = ", ".join(
        match_result.get("matched_skills", [])
    )

    missing_skills = ", ".join(
        match_result.get("missing_skills", [])
    )

    cursor.execute(
        """
        INSERT INTO job_matches (
            resume_id,
            job_description,
            match_percentage,
            matched_skills,
            missing_skills
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            resume_id,
            job_description,
            match_result.get("match_percentage", 0),
            matched_skills,
            missing_skills,
        )
    )

    connection.commit()

    job_match_id = cursor.lastrowid

    connection.close()

    return job_match_id
def get_latest_job_match(user_id):
    """Get the latest job match belonging to a specific user."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT jm.*
        FROM job_matches jm
        JOIN resumes r
            ON jm.resume_id = r.id
        WHERE r.user_id = ?
        ORDER BY jm.id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    job_match = cursor.fetchone()

    connection.close()

    return job_match

def get_latest_resume(user_id):
    """Return the most recent resume belonging to a user."""

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM resumes
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    resume = cursor.fetchone()

    connection.close()

    return resume
def create_user(name, email, password):
    """Create a new user."""

    connection = get_connection()

    cursor = connection.cursor()

    password_hash = generate_password_hash(password)

    cursor.execute(
        """
        INSERT INTO users (
            name,
            email,
            password_hash
        )
        VALUES (?, ?, ?)
        """,
        (
            name,
            email,
            password_hash,
        )
    )

    connection.commit()

    user_id = cursor.lastrowid

    connection.close()

    return user_id
def get_user_by_email(email):
    """Find a user by email."""

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    )

    user = cursor.fetchone()

    connection.close()

    return user

if __name__ == "__main__":

    initialize_database()

    print("Database initialized successfully.")
