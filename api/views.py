from django.shortcuts import get_object_or_404, render, redirect
from .models import CompanyClient, DeveloperCandidate, Application
from .services import parse_resume_pdf, trigger_email_in_background

def match_resources(request, client_id):
    client = get_object_or_404(CompanyClient, id=client_id)

    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_candidates')
        action = request.POST.get('bulk_action')
        if selected_ids and action:
            candidates_to_update = DeveloperCandidate.objects.filter(id__in=selected_ids)
            for cand in candidates_to_update:
                # Candidate Status DB Update
                Application.objects.update_or_create(
                    candidate=cand,
                    client=client,
                    defaults={'status': action}
                )
                
                # Dynamic status sync for email function
                cand.status = action
                
                # Crash-proof Email Trigger
                try:
                    trigger_email_in_background(cand)
                except Exception as mail_err:
                    print(f"Email Failed for {cand.name}: {mail_err}")

            return redirect(f'/api/match-resources/{client_id}/')

    query = request.GET.get('q')
    if query:
        candidates = DeveloperCandidate.objects.filter(skills__icontains=query) | DeveloperCandidate.objects.filter(name__icontains=query)
    else:
        candidates = DeveloperCandidate.objects.all()

    if client.required_tech:
        req_skills = [s.strip().lower() for s in client.required_tech.replace(',', ' ').split() if s.strip()]
    else:
        req_skills = ['python']

    req_skills_set = set(req_skills)

    results = []
    total_applicants = candidates.count()
    shortlisted_count = 0
    rejected_count = 0
    salary_budget_data = []

    seen_candidates = set()

    for cand in candidates:
        unique_key = (cand.name.strip().lower(), cand.email.strip().lower() if cand.email else cand.id)
        if unique_key in seen_candidates:
            continue
        seen_candidates.add(unique_key)

        # Company-specific status check
        app_obj = Application.objects.filter(candidate=cand, client=client).first()
        cand_status = app_obj.status if app_obj else 'Applied'

        if cand_status == 'Shortlisted':
            shortlisted_count += 1
        elif cand_status == 'Rejected':
            rejected_count += 1

        salary_budget_data.append({
            'name': cand.name,
            'expected': cand.expected_salary_lps,
            'budget': client.max_budget_lps
        })

        cand_skills_raw = getattr(cand, 'skills', '') or ''
        cand_projects = getattr(cand, 'projects_summary', '') or ''
        cand_prev = getattr(cand, 'previous_companies', '') or ''
        cand_full_text = f"{cand_skills_raw} {cand_projects} {cand_prev}".lower()

        matched_skills = set()
        missing_skills = set()

        for req in req_skills_set:
            if req in cand_full_text or req in [s.strip().lower() for s in cand_skills_raw.split(',')]:
                matched_skills.add(req)
            else:
                missing_skills.add(req)

        # 1. Skill Match Score (Max 40 points)
        if len(req_skills_set) > 0:
            skill_score = min(40.0, float(len(matched_skills)) * (40.0 / len(req_skills_set)))
        else:
            skill_score = 40.0

        # 2. Experience Match Score (Max 30 points)
        if cand.experience_years >= client.min_experience_years:
            exp_score = 30
            exp_reason = f"Meets/Exceeds min requirement ({client.min_experience_years} yrs): +30 pts"
        else:
            diff_exp = client.min_experience_years - cand.experience_years
            exp_score = max(0, 30 - (diff_exp * 10))
            exp_reason = f"Short by {diff_exp} yrs experience: Deducted points"

        # 3. Budget Proximity Score (Max 30 points)
        if cand.expected_salary_lps <= client.max_budget_lps:
            budget_score = 30
            budget_reason = f"Within max budget ({client.max_budget_lps} LPA): +30 pts"
        else:
            diff = cand.expected_salary_lps - client.max_budget_lps
            budget_score = max(0, 30 - (diff * 5))
            budget_reason = f"Exceeds budget by ₹{diff} LPA: Deducted points"

        # 4. ATS Score weight (Max 10 points)
        ats_points = float(cand.ats_score or 0) * 0.1 

        raw_total = skill_score + exp_score + budget_score + ats_points
        total_score = round(min(100.0, raw_total), 2)

        if cand.experience_years < 2:
            level = "Beginner"
        elif 2 <= cand.experience_years <= 5:
            level = "Intermediate"
        else:
            level = "Expert"

        training_suggestions = {}
        for skill in missing_skills:
            sc = skill.capitalize()
            training_suggestions[skill] = {
                'course': f"Coursera / Udemy: Professional {sc} Certification Course",
                'video': f"YouTube: Complete {sc} Bootcamp & Masterclass",
                'test': f"HackerRank / LeetCode: Official {sc} Practice Assessment & Quizzes"
            }

        results.append({
            'candidate': cand,
            'status': cand_status,  # Per-company status passed to template
            'total_score': total_score,
            'ats_score': cand.ats_score,
            'skill_score': round(skill_score, 1),
            'exp_score': round(exp_score, 1),
            'budget_score': round(budget_score, 1),
            'exp_reason': exp_reason,
            'budget_reason': budget_reason,
            'matched_skills': [s.capitalize() for s in matched_skills],
            'missing_skills': [s.capitalize() for s in missing_skills],
            'training_suggestions': training_suggestions,
            'level': level,
        })

    results = sorted(results, key=lambda x: x['total_score'], reverse=True)

    context = {
        'client': client,
        'results': results,
        'total_applicants': len(results),
        'shortlisted_count': shortlisted_count,
        'rejected_count': rejected_count,
        'salary_budget_data': salary_budget_data,
    }
    return render(request, 'dashboard.html', context)