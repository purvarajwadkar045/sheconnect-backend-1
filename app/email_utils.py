from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import csv
import os
from app.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_email(email: str, otp: str):
    message = MessageSchema(
        subject="Your OTP",
        recipients=[email],
        body=f"Your OTP is {otp}",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)


def load_allowed_emails(file_path="app/female_emails.csv"):
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