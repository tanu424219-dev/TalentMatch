import fitz  # PyMuPDF
import re
from django.core.mail import EmailMessage
from icalendar import Calendar, Event
import datetime

def parse_resume_pdf(file_path):
    """Extracts text, name, email, and skills automatically from PDF Resumes (ATS Feature)"""
    extracted_text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            extracted_text += page.get_text()
    except Exception as e:
        print("PDF Parsing Error:", e)
        return "", "", "", []

    # Simple Regex Extraction logic for Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', extracted_text)
    email = email_match.group(0) if email_match else ""

    # Common Tech Stack Keywords to scan from Resume
    known_skills = ['python', 'django', 'javascript', 'react', 'sql', 'java', 'aws', 'html', 'css', 'c++', 'node.js', 'docker']
    found_skills = [skill.capitalize() for skill in known_skills if re.search(r'\b' + skill + r'\b', extracted_text.lower())]

    # ATS Resume Formatting Score based on keyword density & length
    # Dynamic ATS Scoring Logic
    base_length_score = min(40.0, (len(extracted_text) / 1000.0) * 20)  # Text length up to 40 pts
    skill_score = min(50.0, float(len(found_skills)) * 10)              # 10 pts per skill up to 50 pts
    email_bonus = 10.0 if email_match else 0.0                                 # 10 pts for valid email format

    ats_score = min(100.0, round(base_length_score + skill_score + email_bonus, 1))

    return extracted_text,(email_match.group(0) if email_match else""), ", ".join(found_skills), ats_score

def generate_ics_calendar_invite(candidate_email, interview_date_str):
    """Generates a professional .ics calendar file for interview scheduling"""
    cal = Calendar()
    cal.add('prodid', '-//Enterprise Talent Matrix//HR System//EN')
    cal.add('version', '2.0')

    event = Event()
    event.add('summary', 'Technical Interview - Enterprise Talent Matrix')
    event.add('description', 'Your profile has been shortlisted! Please join the interview using the shared corporate calendar link.')
    
    start_time = datetime.datetime.now() + datetime.timedelta(days=2) # 2 days later default
    event.add('dtstart', start_time)
    event.add('dtend', start_time + datetime.timedelta(hours=1))
    event.add('organizer', 'hr@enterprise.com')
    
    cal.add_component(event)
    return cal.to_ical()

def send_automated_status_email(candidate):
    """Sends automated emails based on Status (Rejection / Shortlisted Interview Invite with Calendar & Link)"""
    if candidate.status == 'Rejected':
        subject = "Update regarding your application at Enterprise"
        body = f"Dear {candidate.name},\n\nThank you for applying. Unfortunately, we are not moving forward with your application at this time.\n\nBest regards,\nHR Team"
        email = EmailMessage(subject, body, 'hr@enterprise.com', [candidate.email])
        email.send(fail_silently=True)

    elif candidate.status == 'Shortlisted':
        subject = "Interview Invitation & Corporate Calendar Link - Enterprise Talent Matrix"
        body = f"Dear {candidate.name},\n\nCongratulations! You have been shortlisted for an interview.\n\nMeeting Link: https://meet.google.com/abc-xyz-def\nPlease find the attached calendar invite (.ics) for schedule details.\n\nBest regards,\nHR Team"
        email = EmailMessage(subject, body, 'hr@enterprise.com', [candidate.email])
        
        # Attach Calendar (.ics) file
        ics_data = generate_ics_calendar_invite(candidate.email, "Upcoming")
        email.attach('interview_invite.ics', ics_data, 'text/calendar')
        email.send(fail_silently=True)