import smtplib
import os
from dotenv import load_dotenv
from email.message import EmailMessage

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def send_otp_email(to_email: str, otp: str, purpose: str = "verify"):
    msg = EmailMessage()

    if purpose == "reset":
        subject = "AuthAPI Password Reset OTP"
        title = "Password Reset OTP"
        minutes = "15"
    else:
        subject = "AuthAPI Email Verification OTP"
        title = "Email Verification OTP"
        minutes = "10"

    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = to_email

    msg.set_content(f"""
Hello,

Your {title} is:

{otp}

This OTP is valid for {minutes} minutes.

Do not share this OTP with anyone.

Regards,
AuthAPI Team
""")

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)