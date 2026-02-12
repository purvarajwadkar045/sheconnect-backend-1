import csv
import csv
from app.database import SessionLocal
from app.models import User
def import_emails(csv_file_path):
    db = SessionLocal()

    try:
        with open(csv_file_path, newline='', encoding="utf-8") as file:
            reader = csv.DictReader(file)

            count = 0

            for row in reader:
                email = row["email"].strip().lower()

                if not email:
                    continue

                existing = db.query(User).filter(User.email_id == email).first()

                if existing:
                    print(f"Skipping {email} (already exists)")
                    continue

                new_user = User(
                    email_id=email,
                    is_active=False
                )

                db.add(new_user)
                count += 1

            db.commit()
            print(f" {count} emails imported successfully!")

    except Exception as e:
        db.rollback()
        print(" Error occurred:", e)

    finally:
        db.close()


if __name__ == "__main__":
    import_emails("app/female_emails.csv")

