from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta
import random
import os
import uuid
from app.security import hash_password, verify_password
from app.database import SessionLocal
from app.models import User
from app.schemas import UserSignup, Login
from app.email_utils import send_otp_email, load_allowed_emails


# ================= CONFIG =================
ALGORITHM = "HS256"

SECRET_KEY = os.getenv("SECRET_KEY", "auth-secret")
OTP_SECRET_KEY = os.getenv("OTP_SECRET_KEY", "otp-secret")

ACCESS_TOKEN_EXPIRE_MINUTES = 60
OTP_EXPIRE_MINUTES = 10

router = APIRouter(prefix="/auth", tags=["Auth"])
ALLOWED_EMAILS = load_allowed_emails("app/female_emails.csv")


# ================= DB =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================= HELPERS =================
def generate_otp():
    return str(random.randint(100000, 999999))


def create_jwt_token(user_id: int):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "user_id": user_id,
        "exp": expire,
        "type": "access"
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_otp_token(email: str, otp: str, purpose: str):
    expire = datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)

    payload = {
        "sub": email,
        "otp": otp,
        "purpose": purpose,
        "exp": expire
    }

    return jwt.encode(payload, OTP_SECRET_KEY, algorithm=ALGORITHM)


def verify_otp_token(token: str):
    try:
        return jwt.decode(token, OTP_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP token")


# ================= SIGNUP =================
@router.post("/signup")
async def signup(
    user: UserSignup,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    if user.email_id.lower() not in ALLOWED_EMAILS:
        raise HTTPException(status_code=403, detail="Email not allowed")

    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if db.query(User).filter(User.email_id == user.email_id).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        name=user.name,
        email_id=user.email_id,
        phone_no=user.phone_no,
        password=hash_password(user.password),
        college_name=user.college_name,
        is_verified=False
    )

    db.add(new_user)
    db.commit()

    otp = generate_otp()
    otp_token = create_otp_token(user.email_id, otp, "signup")

    background_tasks.add_task(send_otp_email, user.email_id, otp)
    anonymous_id = str(uuid.uuid4())[:5]
    return {
        "message": "Signup successful. OTP sent to email.",
        "otp_token": otp_token,
        "anonymous_id": anonymous_id
    }


# ================= VERIFY SIGNUP OTP =================
@router.post("/verify-otp")
def verify_otp(
    email: str,
    otp: str,
    otp_token: str,
    db: Session = Depends(get_db)
):
    payload = verify_otp_token(otp_token)

    if payload["sub"] != email:
        raise HTTPException(status_code=400, detail="Email mismatch")

    if payload["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if payload["purpose"] != "signup":
        raise HTTPException(status_code=400, detail="Invalid OTP purpose")

    user = db.query(User).filter(User.email_id == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    db.commit()

    return {"message": "Email verified successfully"}


# ================= LOGIN =================
@router.post("/login")
async def login(
    user: Login,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.email_id == user.email_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # If user not verified → send OTP again
    if not db_user.is_verified:
        otp = generate_otp()
        otp_token = create_otp_token(db_user.email_id, otp, "signup")

        background_tasks.add_task(send_otp_email, db_user.email_id, otp)

        return {
            "message": "Email not verified. OTP sent.",
            "otp_token": otp_token,
            "first_login": True
        }

    # Create JWT with user_id
    access_token = create_jwt_token(db_user.user_id)

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "first_login": False
    }


# ================= FORGOT PASSWORD =================
@router.post("/forgot-password")
async def forgot_password(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email_id == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp = generate_otp()
    otp_token = create_otp_token(email, otp, "forgot")

    background_tasks.add_task(send_otp_email, email, otp)

    return {
        "message": "OTP sent to email",
        "otp_token": otp_token
    }


# ================= VERIFY FORGOT OTP =================
@router.post("/verify-forgot-otp")
def verify_forgot_otp(
    email: str,
    otp: str,
    otp_token: str
):
    payload = verify_otp_token(otp_token)

    if payload["sub"] != email:
        raise HTTPException(status_code=400, detail="Email mismatch")

    if payload["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if payload["purpose"] != "forgot":
        raise HTTPException(status_code=400, detail="Invalid OTP purpose")

    return {"message": "OTP verified successfully"}


# ================= RESET PASSWORD =================
@router.post("/reset-password")
def reset_password(
    email: str,
    otp: str,
    otp_token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    payload = verify_otp_token(otp_token)

    if payload["sub"] != email:
        raise HTTPException(status_code=400, detail="Email mismatch")

    if payload["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if payload["purpose"] != "forgot":
        raise HTTPException(status_code=400, detail="Invalid OTP purpose")

    user = db.query(User).filter(User.email_id == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password = hash_password(new_password)
    db.commit()

    return {"message": "Password reset successful"}


# ================= RESEND OTP =================
@router.post("/resend-otp")
async def resend_otp(
    email: str,
    purpose: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email_id == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if purpose not in ["signup", "forgot"]:
        raise HTTPException(status_code=400, detail="Invalid purpose")

    if purpose == "signup" and user.is_verified:
        raise HTTPException(status_code=400, detail="User already verified")

    otp = generate_otp()
    otp_token = create_otp_token(email, otp, purpose)

    background_tasks.add_task(send_otp_email, email, otp)

    return {
        "message": "OTP resent successfully",
        "otp_token": otp_token
    }
