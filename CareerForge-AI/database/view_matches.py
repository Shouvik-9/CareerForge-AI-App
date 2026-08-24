from database import get_connection


connection = get_connection()

cursor = connection.cursor()

cursor.execute("""
    SELECT
        id,
        resume_id,
        match_percentage,
        matched_skills,
        missing_skills,
        created_at
    FROM job_matches
    ORDER BY id DESC
""")

rows = cursor.fetchall()

if not rows:

    print("No job matches found.")

else:

    print("\nSaved Job Matches")
    print("-" * 80)

    for row in rows:

        print(f"ID: {row['id']}")
        print(f"Resume ID: {row['resume_id']}")
        print(f"Match: {row['match_percentage']}%")
        print(f"Matched: {row['matched_skills']}")
        print(f"Missing: {row['missing_skills']}")
        print(f"Created: {row['created_at']}")
        print("-" * 80)


connection.close()