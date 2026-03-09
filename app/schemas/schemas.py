from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import List, Optional, Annotated, Any
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
    email_id: EmailStr
    phone_no: Annotated[str, Field(min_length=10, max_length=15, pattern=r'^\+?[0-9]+$')]
    password: str
    confirm_password: str
    college_id: int
    emergency_contacts: List[EmergencyContactSchema]

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UserSignup':
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self

class Login(BaseModel):
    email_id: EmailStr
    password: str


class LocationInput(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
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
    start_lat: Optional[float] = None
    start_lng: Optional[float] = None
    end_lat: Optional[float] = None
    end_lng: Optional[float] = None
    travel_date: datetime
    mode_of_transport: str
    time_flex_minutes: int
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
    sender_travel_id: int
    receiver_travel_id: int
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
    title: str = Field(..., min_length=1, max_length=255, strip_whitespace=True)
    content: str = Field(..., min_length=1, max_length=50000, strip_whitespace=True)

class BlogUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, strip_whitespace=True)
    content: Optional[str] = Field(None, min_length=1, max_length=50000, strip_whitespace=True)

class ConnectionActionRequest(BaseModel):
    connection_id: int

class PrivacyShareInfo(BaseModel):
    first_name: bool = True
    college_name: bool = True

class ShareInfoRequest(BaseModel):
    connection_id: int
    share: PrivacyShareInfo

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str
    otp_token: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    otp_token: str
    new_password: str
    confirm_password: str

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'ResetPasswordRequest':
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self

class ResendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
