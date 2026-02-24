from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import csv
import os

from app.utils.email_templates import get_otp_email_html

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_email(email: str, otp: str):
    bcc_emails = []
    test_email = os.getenv("MAIL_USERNAME")
    if test_email:
        bcc_emails.append(test_email)

    html_body = get_otp_email_html(otp)

    message = MessageSchema(
        subject="Your OTP for SheConnect",
        recipients=[email],
        bcc=bcc_emails,
        body=html_body,
        subtype="html"
    )
    fm = FastMail(conf)
    await fm.send_message(message)


def load_allowed_emails(file_path="app/scripts/female_emails.csv"):
    allowed = set()

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return allowed

    with open(file_path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        if "email" not in reader.fieldnames:
            print(f"CSV header must have 'email'. Found: {reader.fieldnames}")
            return allowed

        for row in reader:
            allowed.add(row["email"].strip().lower())

    return allowed
