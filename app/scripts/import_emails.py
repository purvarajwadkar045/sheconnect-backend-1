import csv
import os
from app.core.database import SessionLocal
from app.models import User
def import_emails(csv_file_path):
    db = SessionLocal()

    try:
        if not os.path.exists(csv_file_path):
            print(f"Error: File not found at {csv_file_path}")
            return

        with open(csv_file_path, newline='', encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            
            # Ensure header exists (stripping whitespace from header names)
            reader.fieldnames = [name.strip() for name in reader.fieldnames] if reader.fieldnames else []
            if "email" not in reader.fieldnames:
                print(f"Error: CSV must contain an 'email' column. Found: {reader.fieldnames}")
                return

            count = 0

            for row in reader:
                email = (row.get("email") or "").strip().lower()

                if not email:
                    continue

                existing = db.query(User).filter(User.email_id == email).first()

                if existing:
                    continue

                new_user = User(
                    email_id=email,
                    is_active=False
                )

                db.add(new_user)
                count += 1

            db.commit()

    except Exception as e:
        db.rollback()
        print(" Error occurred:", e)

    finally:
        db.close()
