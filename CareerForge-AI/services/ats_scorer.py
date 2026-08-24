def calculate_ats_score(resume):
    """
    Calculate a transparent ATS Compatibility Score out of 100.

    This is a deterministic estimate, not an official ATS score.
    """

    score = 0
    breakdown = {}

    # --------------------------------------------------
    # 1. Name - 5 points
    # --------------------------------------------------

    if resume["name"] and resume["name"] != "Not found":
        score += 5
        breakdown["Name"] = 5
    else:
        breakdown["Name"] = 0

    # --------------------------------------------------
    # 2. Email - 5 points
    # --------------------------------------------------

    if resume["email"] and resume["email"] != "Not found":
        score += 5
        breakdown["Email"] = 5
    else:
        breakdown["Email"] = 0

    # --------------------------------------------------
    # 3. Phone - 5 points
    # --------------------------------------------------

    if resume["phone"] and resume["phone"] != "Not found":
        score += 5
        breakdown["Phone"] = 5
    else:
        breakdown["Phone"] = 0

    # --------------------------------------------------
    # 4. Education - 10 points
    # --------------------------------------------------

    if resume["education"] and resume["education"] != "Not found":
        score += 10
        breakdown["Education"] = 10
    else:
        breakdown["Education"] = 0

    # --------------------------------------------------
    # 5. Experience - 10 points
    # --------------------------------------------------

    if resume["experience"] and resume["experience"] != "Not found":
        score += 10
        breakdown["Experience"] = 10
    else:
        breakdown["Experience"] = 0

    # --------------------------------------------------
    # 6. Projects - 10 points
    # --------------------------------------------------

    if resume["projects"] and resume["projects"] != "Not found":
        score += 10
        breakdown["Projects"] = 10
    else:
        breakdown["Projects"] = 0

    # --------------------------------------------------
    # 7. Skills - 15 points
    # --------------------------------------------------

    skills = resume.get("skills", [])

    if len(skills) >= 10:
        skill_score = 15
    elif len(skills) >= 7:
        skill_score = 12
    elif len(skills) >= 4:
        skill_score = 8
    elif len(skills) >= 1:
        skill_score = 4
    else:
        skill_score = 0

    score += skill_score
    breakdown["Skills"] = skill_score

    # --------------------------------------------------
    # 8. Plain-text extractability - 15 points
    # --------------------------------------------------

    resume_text = resume.get("resume_text", "")

    text_length = len(resume_text.strip())

    if text_length >= 3000:
        text_score = 15
    elif text_length >= 2000:
        text_score = 12
    elif text_length >= 1000:
        text_score = 8
    elif text_length >= 500:
        text_score = 4
    else:
        text_score = 0

    score += text_score
    breakdown["Text Extractability"] = text_score

    # --------------------------------------------------
    # 9. Standard section structure - 20 points
    # --------------------------------------------------

    section_score = 0

    if resume["education"] != "Not found":
        section_score += 5

    if resume["experience"] != "Not found":
        section_score += 5

    if resume["projects"] != "Not found":
        section_score += 5

    if skills:
        section_score += 5

    score += section_score
    breakdown["Standard Sections"] = section_score

    # --------------------------------------------------
    # 10. Professional links - 5 points
    # --------------------------------------------------

    link_score = 0

    if resume.get("github") and resume["github"] != "Not found":
        link_score += 2.5

    if resume.get("linkedin") and resume["linkedin"] != "Not found":
        link_score += 2.5

    score += link_score
    breakdown["Professional Links"] = link_score

    return round(score, 1), breakdown