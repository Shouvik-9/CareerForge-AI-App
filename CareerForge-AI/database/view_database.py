from database import get_connection


connection = get_connection()

cursor = connection.cursor()

cursor.execute("""
    SELECT
        id,
        filename,
        name,
        email,
        resume_score,
        created_at
    FROM resumes
    ORDER BY id DESC
""")

rows = cursor.fetchall()

if not rows:
    print("No resumes found in the database.")

else:
    print("\nStored Resumes")
    print("-" * 80)

    for row in rows:

        print(f"ID: {row['id']}")
        print(f"File: {row['filename']}")
        print(f"Name: {row['name']}")
        print(f"Email: {row['email']}")
        print(f"Resume Score: {row['resume_score']}")
        print(f"Created: {row['created_at']}")
        print("-" * 80)


connection.close()