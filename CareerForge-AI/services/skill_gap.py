def generate_skill_gap(match_result):
    """
    Generate a basic skill-gap report from job-match results.
    """

    missing_skills = match_result.get("missing_skills", [])
    matched_skills = match_result.get("matched_skills", [])
    match_percentage = match_result.get("match_percentage", 0)

    recommendations = []

    for skill in missing_skills:
        recommendations.append({
            "skill": skill,
            "priority": "High",
            "recommendation": (
                f"Learn {skill} and build a practical project "
                f"that demonstrates this skill."
            )
        })

    return {
        "match_percentage": match_percentage,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "recommendations": recommendations
    }