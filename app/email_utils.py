from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import csv
import os

conf = ConnectionConfig(
    MAIL_USERNAME="sheconnect77@gmail.com",
    MAIL_PASSWORD="kshm xqbr axik ddcb",
    MAIL_FROM="sheconnect77@gmail.com",
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
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

    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        if "email" not in reader.fieldnames:
            print(f"CSV header must have 'email'. Found: {reader.fieldnames}")
            return allowed

        for row in reader:
            allowed.add(row["email"].strip().lower())

    print(f"Loaded {len(allowed)} allowed emails")
    return allowed