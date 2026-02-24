from pydantic import BaseModel
from typing import List
from datetime import datetime
from typing import Optional
from enum import Enum

class TransportMode(str, Enum):
    CAR = "car"
    BUS = "bus"
    TRAIN = "train"
    UBER_CAB = "uber/cab"
    AUTO_RICKSHAW = "auto-rickshaw"
    METRO = "metro"

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
    trip_id: int

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
    message: str

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

class ConnectionActionRequest(BaseModel):
    connection_id: int

class PrivacyShareInfo(BaseModel):
    first_name: bool = True
    college_name: bool = True

class ShareInfoRequest(BaseModel):
    connection_id: int
    share: PrivacyShareInfo
