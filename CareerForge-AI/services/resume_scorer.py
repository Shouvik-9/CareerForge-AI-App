def calculate_resume_score(resume_data, pdf_links=None):
    """
    Calculate resume completeness score out of 100.

    GitHub and LinkedIn points are based on actual
    detected PDF links when available.
    """

    score = 0
    breakdown = {}

    # 1. Name - 10 points
    if resume_data.get("name") and resume_data["name"] != "Not found":
        score += 10
        breakdown["Name"] = 10
    else:
        breakdown["Name"] = 0

    # 2. Email - 10 points
    if resume_data.get("email") and resume_data["email"] != "Not found":
        score += 10
        breakdown["Email"] = 10
    else:
        breakdown["Email"] = 0

    # 3. Phone - 10 points
    if resume_data.get("phone") and resume_data["phone"] != "Not found":
        score += 10
        breakdown["Phone"] = 10
    else:
        breakdown["Phone"] = 0

    # -------------------------------------------------
    # GitHub - 5 points
    # Check actual detected PDF links
    # -------------------------------------------------

    github_found = False

    if pdf_links:
        github_found = any(
            "github.com" in link.lower()
            for link in pdf_links
        )

    # Fallback to resume_data if needed
    if not github_found:
        github_found = (
            resume_data.get("github")
            and resume_data["github"] != "Not found"
        )

    if github_found:
        score += 5
        breakdown["GitHub"] = 5
    else:
        breakdown["GitHub"] = 0

    # -------------------------------------------------
    # LinkedIn - 5 points
    # Check actual detected PDF links
    # -------------------------------------------------

    linkedin_found = False

    if pdf_links:
        linkedin_found = any(
            "linkedin.com" in link.lower()
            for link in pdf_links
        )

    # Fallback to resume_data if needed
    if not linkedin_found:
        linkedin_found = (
            resume_data.get("linkedin")
            and resume_data["linkedin"] != "Not found"
        )

    if linkedin_found:
        score += 5
        breakdown["LinkedIn"] = 5
    else:
        breakdown["LinkedIn"] = 0

    # 6. Skills - 20 points
    skills = resume_data.get("skills", [])

    if len(skills) >= 8:
        skill_score = 20
    elif len(skills) >= 5:
        skill_score = 15
    elif len(skills) >= 3:
        skill_score = 10
    elif len(skills) >= 1:
        skill_score = 5
    else:
        skill_score = 0

    score += skill_score
    breakdown["Skills"] = skill_score

    # 7. Education - 15 points
    education = resume_data.get("education", "")

    if education and education != "Not found":
        score += 15
        breakdown["Education"] = 15
    else:
        breakdown["Education"] = 0

    # 8. Experience - 10 points
    experience = resume_data.get("experience", "")

    if experience and experience != "Not found":
        score += 10
        breakdown["Experience"] = 10
    else:
        breakdown["Experience"] = 0

    # 9. Projects - 15 points
    projects = resume_data.get("projects", "")

    if projects and projects != "Not found":
        score += 15
        breakdown["Projects"] = 15
    else:
        breakdown["Projects"] = 0

    return score, breakdown