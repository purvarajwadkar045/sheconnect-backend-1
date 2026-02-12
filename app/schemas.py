from pydantic import BaseModel
from typing import List
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
class EmergencyContactSchema(BaseModel):
    emergency_name: str
    phone_no: str
    gender: str


class UserSignup(BaseModel):
    name: str
    email_id: str
    phone_no: str
    password: str
    confirm_password: str
    college_id: int
    emergency_contacts: List[EmergencyContactSchema]

class Login(BaseModel):
    email_id: str
    password: str


class ForgotPasswordEmail(BaseModel):
    email: str


class VerifyOTP(BaseModel):
    email: str
    otp: str


class ResetPassword(BaseModel):
    email: str
    new_password: str
    confirm_password: str


class TravelCreate(BaseModel):
    start_location: str
    end_location: str
    travel_date: datetime
    mode_of_transport: str
    vehicle_no: Optional[str] = None    
