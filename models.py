from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, Text

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Confirmation(Base):
    __tablename__ = "confirmations"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False, index=True)
    date_of_birth = Column(Date, nullable=False)
    confirmation_date = Column(Date, nullable=False, index=True)
    church_name = Column(String(200), nullable=False, index=True)
    priest_name = Column(String(200), nullable=False, index=True)
    sponsor_name = Column(String(200), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
