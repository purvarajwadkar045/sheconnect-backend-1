from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, Text
from datetime import datetime
from app.core.database import Base
from sqlalchemy.orm import relationship


class Blog(Base):
    __tablename__ = "blogs"

    blog_id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="blogs")
