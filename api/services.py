import threading
import datetime
import re
import fitz  # PyMuPDF
from django.core.mail import EmailMessage
from django.conf import settings


def parse_resume_pdf(file_path):
    """Extracts text, name, email, and skills automatically from PDF Resumes (ATS Feature)"""
    extracted_text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            extracted_text += page.get_text()
    except Exception as e:
        print("PDF Parsing Error:", e)
        return "", "", "", 0.0

    # Simple Regex Extraction logic for Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', extracted_text)
    email = email_match.group(0) if email_match else ""

    # Common Tech Stack Keywords to scan from Resume
    known_skills = ['python', 'django', 'javascript', 'react', 'sql', 'java', 'aws', 'html', 'css', 'c++', 'node.js', 'docker']
    found_skills = [skill.capitalize() for skill in known_skills if re.search(r'\b' + skill + r'\b', extracted_text.lower())]

    # Dynamic ATS Resume Formatting Score based on keyword density & length
    base_length_score = min(40.0, (len(extracted_text) / 1000.0) * 20)
    skill_score = min(50.0, float(len(found_skills)) * 10)
    email_bonus = 10.0 if email else 0.0

    ats_score = min(100.0, round(base_length_score + skill_score + email_bonus, 1))

    return extracted_text, email, ", ".join(found_skills), ats_score


def send_automated_status_email(candidate):
    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'tanu424219@gmail.com')
        status = getattr(candidate, 'status', 'Shortlisted')
        cand_email = getattr(candidate, 'email', '')

        if not cand_email:
            return

        if status == 'Rejected':
            subject = "Update regarding your application at Enterprise"
            body = f"Dear {getattr(candidate, 'name', 'Candidate')},\n\nThank you for applying. Unfortunately, we are not moving forward with your application at this time."
            email = EmailMessage(subject, body, from_email, [cand_email])
            email.send(fail_silently=False)

        elif status == 'Shortlisted':
            subject = "Interview Invitation & Corporate Calendar Link - Enterprise Talent Matrix"
            body = f"Dear {getattr(candidate, 'name', 'Candidate')},\n\nCongratulations! You have been shortlisted for an interview."
            
            email = EmailMessage(subject, body, from_email, [cand_email])

            now = datetime.datetime.now(datetime.timezone.utc)
            start_time = (now + datetime.timedelta(days=1)).strftime('%Y%m%dT%H0000Z')
            end_time = (now + datetime.timedelta(days=1, hours=1)).strftime('%Y%m%dT%H0000Z')

            ics_content = (
                "BEGIN:VCALENDAR\n"
                "VERSION:2.0\n"
                "PRODID:-//Enterprise Talent Matrix//EN\n"
                "CALSCALE:GREGORIAN\n"
                "METHOD:REQUEST\n"
                "BEGIN:VEVENT\n"
                f"UID:interview-{getattr(candidate, 'id', 1)}-{now.strftime('%Y%m%d%H%M%S')}@enterprise.com\n"
                f"DTSTAMP:{now.strftime('%Y%m%dT%H%M%SZ')}\n"
                f"DTSTART:{start_time}\n"
                f"DTEND:{end_time}\n"
                "SUMMARY:Technical Interview - Enterprise Talent Matrix\n"
                "DESCRIPTION:Your profile has been shortlisted! Please join the interview.\n"
                "STATUS:CONFIRMED\n"
                f"ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:MAILTO:{cand_email}\n"
                "END:VEVENT\n"
                "END:VCALENDAR"
            )

            email.attach('interview_invite.ics', ics_content, 'text/calendar; method=REQUEST')
            email.send(fail_silently=True)

    except Exception as e:
        print(f"Email error safely ignored: {e}")
        # 👇 Line 85 ke theek neeche yeh 5 lines add kar do:
def trigger_email_in_background(candidate):
    thread = threading.Thread(target=send_automated_status_email, args=(candidate,))
    thread.daemon = True
    thread.start()

import resend

resend.api_key = "Re_ZHJ7sYa2_NPHTmcRitxP2CVYPadNzeowR"

def send_email_func(cand):
    try:
        print(f"DEBUG: Attempting to send Resend email to {cand.email}")
        params = {
            "from": "onboarding@resend.dev",
            "to": [cand.email],
            "subject": f"Application Status Updated: {cand.status}",
            "html": f"""
                <div style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>Status Update</h2>
                    <p>Hello <strong>{cand.name}</strong>,</p>
                    <p>Your application status has been updated to: <b style="color: #2563eb;">{cand.status}</b></p>
                    <br>
                    <p>Best regards,<br>Hiring Team</p>
                </div>
            """
        }
        response = resend.Emails.send(params)
        print(f"✅ RESEND EMAIL DELIVERED TO {cand.email} | Response ID: {response}")
    except Exception as e:
        print(f"❌ RESEND EMAIL ERROR FOR {cand.name}: {str(e)}")

def trigger_email_in_background(cand):
    thread = threading.Thread(target=send_email_func, args=(cand,))
    thread.daemon = True
    thread.start()