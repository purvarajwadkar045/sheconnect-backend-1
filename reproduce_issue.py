
try:
    from app.auth import ALLOWED_EMAILS
    print("Successfully loaded ALLOWED_EMAILS:", len(ALLOWED_EMAILS))
except Exception as e:
    print(f"Error loading ALLOWED_EMAILS: {e}")
