from django.db import models
from django.utils import timezone

class CompanyClient(models.Model):
    company_name = models.CharField(max_length=100)
    contact_email = models.EmailField(unique=True)
    required_tech = models.CharField(max_length=255, help_text="Comma-separated required skills")
    max_budget_lps = models.FloatField(default=0.0)
    min_experience_years = models.FloatField(default=0.0)

    def __str__(self):
        return self.company_name

class DeveloperCandidate(models.Model):
    STATUS_CHOICES = [
        ('Applied', 'Applied'),
        ('Shortlisted', 'Shortlisted'),
        ('On-Hold', 'On-Hold'),
        ('Rejected', 'Rejected'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, help_text="Used for duplicate check & automated emails")
    resume = models.FileField(upload_to='resumes/', help_text="Mandatory PDF Resume")
    skills = models.TextField(help_text="Auto-extracted or manual skills (Comma-separated)")
    experience_years = models.FloatField(default=0.0)
    expected_salary_lps = models.FloatField(default=0.0)
    qualification = models.CharField(max_length=150, default="B.Tech / Graduate")
    previous_companies = models.TextField(blank=True, help_text="Extracted/Comma-separated company names")
    projects_summary = models.TextField(blank=True, help_text="Brief about projects")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Applied')
    ats_score = models.FloatField(default=0.0, help_text="Automated ATS Resume Score")
    
    # Audit Trail / History Log
    status_history = models.TextField(blank=True, default="", help_text="Audit logs of status changes")

    def save(self, *args, **kwargs):
        # Auto-track status changes for Audit Trail
        if self.pk:
            old_obj = DeveloperCandidate.objects.get(pk=self.pk)
            if old_obj.status != self.status:
                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M')
                log_entry = f"[{timestamp}] Status changed from '{old_obj.status}' to '{self.status}'\n"
                self.status_history = log_entry + self.status_history
        else:
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M')
            self.status_history = f"[{timestamp}] Application created with status 'Applied'\n"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Application(models.Model):
    STATUS_CHOICES = [
        ('Applied', 'Applied'),
        ('Shortlisted', 'Shortlisted'),
        ('Rejected', 'Rejected'),
        ('Selected', 'Selected'),
    ]
    candidate = models.ForeignKey(DeveloperCandidate, on_delete=models.CASCADE, related_name='applications')
    client = models.ForeignKey(CompanyClient, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Applied')
    company_ats_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('candidate', 'client')

    def __str__(self):
        return f"{self.candidate.name} - {self.client.company_name} ({self.status})"