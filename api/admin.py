import csv
from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Application, CompanyClient, DeveloperCandidate
from .services import parse_resume_pdf, send_automated_status_email


@admin.register(CompanyClient)
class CompanyClientAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_email', 'required_tech', 'max_budget_lps', 'min_experience_years', 'open_matching_portal')
    search_fields = ('company_name', 'required_tech')

    def open_matching_portal(self, obj):
        url = f"/api/match-resources/{obj.id}/"
        return format_html(
            '<a style="'
            'background-color: #2563eb; '
            'color: white; '
            'padding: 6px 14px; '
            'border-radius: 6px; '
            'text-decoration: none; '
            'font-weight: 600; '
            'font-size: 13px; '
            'display: inline-block;" '
            'href="{}" target="_blank">View Matched Candidates 🚀</a>',
            url
        )

    open_matching_portal.short_description = "Portal Link"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    # Company ATS Score column yahan se permanently hata diya gaya hai
    list_display = ('candidate', 'client', 'status', 'created_at')
    list_filter = ('client', 'status')
    search_fields = ('candidate__name', 'client__company_name')


@admin.register(DeveloperCandidate)
class DeveloperCandidateAdmin(admin.ModelAdmin):
    # Photo ke exact 6 columns: NAME, EMAIL, EXPERIENCE, APPLIED COMPANIES, COMPANY STATUSES, ATS SCORES
    list_display = ('name', 'email', 'get_company_experience', 'get_applied_companies', 'get_company_statuses', 'get_company_scores')
    list_filter = ('status', 'qualification', 'experience_years')
    search_fields = ('name', 'email', 'skills')
    readonly_fields = ('ats_score', 'status_history')

    # Column 3: Company-wise Experience (Candidate vs Required)
    def get_company_experience(self, obj):
        apps = obj.applications.all()
        if not apps.exists():
            return f"{obj.experience_years or 0} yrs"
        
        exp_html = []
        for app in apps:
            req_exp = app.client.min_experience_years
            cand_exp = obj.experience_years or 0.0
            exp_html.append(f'<b>{app.client.company_name}:</b> {cand_exp} yrs (Req: {req_exp} yrs)')
        return mark_safe("<br>".join(exp_html))
    get_company_experience.short_description = "EXPERIENCE"

    # Column 4: Applied Companies List
    def get_applied_companies(self, obj):
        apps = obj.applications.all()
        if not apps.exists():
            return "-"
        companies = [app.client.company_name for app in apps]
        return mark_safe("<br>".join(companies))
    get_applied_companies.short_description = "APPLIED COMPANIES"

    # Column 5: Colored Company Status Badges
    def get_company_statuses(self, obj):
        apps = obj.applications.all()
        if not apps.exists():
            return "-"
        
        status_html = []
        for app in apps:
            color = "#10b981" if app.status == 'Selected' else ("#3b82f6" if app.status == 'Shortlisted' else ("#ef4444" if app.status == 'Rejected' else "#f59e0b"))
            status_html.append(f'<span style="background-color: {color}; color: white; padding: 2px 6px; border-radius: 6px; font-size: 11px; font-weight: bold;">{app.client.company_name}: {app.status}</span>')
        return mark_safe("<br>".join(status_html))
    get_company_statuses.short_description = "COMPANY STATUSES"

    # Column 6: Mapped ATS Scores Per Company
    def get_company_scores(self, obj):
        apps = obj.applications.all()
        if not apps.exists():
            return "-"
        
        scores_html = []
        for app in apps:
            client = app.client
            req_skills = [s.strip().lower() for s in client.required_tech.split(',')] if client.required_tech else []
            cand_skills = [s.strip().lower() for s in obj.skills.split(',')] if obj.skills else []
            
            matched = set(req_skills).intersection(set(cand_skills))
            skill_ratio = (len(matched) / len(req_skills)) if req_skills else 1.0
            
            skill_score = skill_ratio * 40
            exp_score = 30 if (obj.experience_years and obj.experience_years >= client.min_experience_years) else 15
            budget_score = 30 if (obj.expected_salary_lps and obj.expected_salary_lps <= client.max_budget_lps) else 10
            
            total_score = round(skill_score + exp_score + budget_score, 1)
            scores_html.append(f'<b>{client.company_name}: {total_score}/100</b>')
            
        return mark_safe("<br>".join(scores_html))
    get_company_scores.short_description = "ATS SCORES"

    # CSV Data Export Feature
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response

    export_as_csv.short_description = "Export Selected Candidates to CSV 📊"
    actions = [export_as_csv]

    def save_model(self, request, obj, form, change):
        if not change:
            if DeveloperCandidate.objects.filter(email=obj.email).exists():
                messages.error(request, f"Duplicate Warning: An application with email {obj.email} already exists!")
                return

        if obj.resume:
            try:
                text, parsed_email, parsed_skills, raw_ats_score = parse_resume_pdf(obj.resume.path)
                if not obj.email and parsed_email:
                    obj.email = parsed_email
                if not obj.skills:
                    obj.skills = parsed_skills
                
                try:
                    obj.ats_score = float(raw_ats_score)
                except (TypeError, ValueError):
                    obj.ats_score = 0.0

            except Exception as e:
                print("Could not parse PDF automatically:", e)
                obj.ats_score = 0.0

        super().save_model(request, obj, form, change)
        send_automated_status_email(obj)