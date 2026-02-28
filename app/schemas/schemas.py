from pydantic import BaseModel, Field
from typing import List, Optional, Annotated
from datetime import datetime
from enum import Enum

class TransportMode(str, Enum):
    CAR = "car"
    BUS = "bus"
    TRAIN = "train"
    UBER_CAB = "uber/cab"
    AUTO_RICKSHAW = "auto-rickshaw"
    METRO = "metro"

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"

class EmergencyContactSchema(BaseModel):
    emergency_name: Annotated[str, Field(min_length=1, max_length=50, strip_whitespace=True)]
    phone_no: Annotated[str, Field(min_length=10, max_length=15, pattern=r'^\+?[0-9]+$')]
    gender: Gender

class EmergencyContactResponse(BaseModel):
    emergency_id: int
    emergency_name: str
    phone_no: str
    gender: str

    class Config:
        from_attributes = True


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


class LocationInput(BaseModel):
    lat: float
    lng: float
    label: str

class TravelCreate(BaseModel):
    start: LocationInput
    end: LocationInput
    start_time: datetime
    time_flex_minutes: int
    transport_mode: TransportMode
    vehicle_no: Optional[str] = None

class TravelResponse(BaseModel):
    travel_id: int
    start_label: str
    end_label: str
    travel_date: datetime
    mode_of_transport: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class TripRequestCreate(BaseModel):
    sender_trip_id: int
    receiver_trip_id: int

class RequestUpdate(BaseModel):
    status: str

class RequestResponse(BaseModel):
    request_id: int
    travel_id: int
    sent_by: int
    sent_to: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatMessageCreate(BaseModel):
    receiverId: int
    message: str = Field(..., min_length=1, max_length=2000, strip_whitespace=True)

class ChatMessageResponse(BaseModel):
    senderId: int
    message: str

    class Config:
        from_attributes = True

class ChatMessageRead(BaseModel):
    chat_ids: List[int]

class BlogCreate(BaseModel):
    title: str
    content: str

class BlogUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class ConnectionActionRequest(BaseModel):
    connection_id: int

class PrivacyShareInfo(BaseModel):
    first_name: bool = True
    college_name: bool = True

class ShareInfoRequest(BaseModel):
    connection_id: int
    share: PrivacyShareInfo

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str
    otp_token: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    otp_token: str
    new_password: str
    confirm_password: str

class ResendOTPRequest(BaseModel):
    email: str
    purpose: str

class ForgotPasswordRequest(BaseModel):
    email: str
