from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey,Text
from datetime import datetime
from app.database import Base
from sqlalchemy.orm import relationship
'''
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email_id = Column(String, unique=True, index=True, nullable=False)
    phone_no = Column(String)
    password = Column(String, nullable=False)

    college_id = Column(
        Integer,
        ForeignKey("colleges.college_id"),
        nullable=False
    )

    anonymous_id = Column(String)

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    travels = relationship("Travel", back_populates="user")
    blogs = relationship("Blog", back_populates="user")

    college = relationship("College", back_populates="users")
'''
class College(Base):
    __tablename__ = "colleges"

    college_id = Column(Integer, primary_key=True, index=True)
    college_name = Column(String(255), unique=True, nullable=False)

    users = relationship("User", back_populates="college")

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=True)   # changed
    email_id = Column(String, unique=True, index=True, nullable=False)
    phone_no = Column(String, nullable=True)
    password = Column(String, nullable=True)   # changed

    college_id = Column(
        Integer,
        ForeignKey("colleges.college_id"),
        nullable=True   # changed
    )

    anonymous_id = Column(String)

    is_active = Column(Boolean, default=False)  # changed default
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    travels = relationship("Travel", back_populates="user")
    blogs = relationship("Blog", back_populates="user")

    college = relationship("College", back_populates="users")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    emergency_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    emergency_name = Column(String)
    phone_no = Column(String)
    gender = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class Travel(Base):
    __tablename__ = "travels"

    travel_id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    start_location = Column(String, nullable=False)
    end_location = Column(String, nullable=False)

    travel_date = Column(DateTime, nullable=False)
    mode_of_transport = Column(String, nullable=False)

    emergency_name = Column(String, nullable=True)
    emergency_contact = Column(String, nullable=True)

    vehicle_no = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deleted_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True)
    user = relationship("User", back_populates="travels")

class Blog(Base):
    __tablename__ = "blogs"

    blog_id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)

    # Relationship
    user = relationship("User", back_populates="blogs")

class Request(Base):
    __tablename__ = "requests"

    request_id = Column(Integer, primary_key=True, index=True)

    travel_id = Column(Integer, ForeignKey("travels.travel_id"), nullable=False)

    sent_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    sent_to = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    status = Column(String, default="pending")  
    # values: pending / accepted / rejected

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deleted_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    travel = relationship("Travel")
    sender = relationship("User", foreign_keys=[sent_by])
    receiver = relationship("User", foreign_keys=[sent_to])

class Chat(Base):
    __tablename__ = "chats"

    chat_id = Column(Integer, primary_key=True, index=True)

    request_id = Column(Integer, ForeignKey("requests.request_id"), nullable=False)

    sender_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    message = Column(String, nullable=False)

    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    is_active = Column(Boolean, default=True)

    # Relationships
    request = relationship("Request")
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    email = Column(String(150), unique=True, nullable=False, index=True)

    password = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    is_active = Column(Boolean, default=True)

    deleted_at = Column(DateTime, nullable=True)    