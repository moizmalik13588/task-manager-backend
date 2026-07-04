from sqlalchemy import Column, Integer, String, Boolean, ForeignKey,DateTime
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer,primary_key=True ,index=True)
    username = Column(String,index=True)
    password = Column(String)
    role = Column(String, default="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer,primary_key=True ,index=True)
    title = Column(String)
    description = Column(String,index=True)
    is_completed = Column(Boolean, default=False)
    priority = Column(String, default="low")
    deadline = Column(String, default=None)
    owner_id = Column(Integer, ForeignKey("users.id"))

# models.py mein add karo
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime)
    is_revoked = Column(Boolean, default=False)