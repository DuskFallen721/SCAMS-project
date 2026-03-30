from sqlalchemy import Column, String, Float, Boolean
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    role = Column(String, default="student")

    student_id = Column(String, nullable=True)
    department = Column(String, nullable=True)  
    year_section = Column(String, nullable=True)  

    temporary_password = Column(Boolean, default=False)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    required_hours = Column(Float)
    location = Column(String, nullable=True)
    task_date = Column(String, nullable=True)


class HourLog(Base):
    __tablename__ = "hour_logs"

    id = Column(String, primary_key=True, index=True)
    student_id = Column(String)
    task_id = Column(String)
    hours_rendered = Column(Float)
    date = Column(String)
    status = Column(String, default="pending")
    documentation_path = Column(String, nullable=True)