from pydantic import BaseModel
from typing import Optional

# TASK 
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    required_hours: float
    location: Optional[str] = None
    task_date: Optional[str] = None


class TaskResponse(TaskCreate):
    id: str

    class Config:
        from_attributes = True


# LOG 
class LogCreate(BaseModel):
    student_id: str
    task_id: str
    hours_rendered: float
    date: str


class LogResponse(LogCreate):
    id: str
    status: str
    documentation_path: Optional[str] = None

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str


# USER 
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    student_id: Optional[str] = None
    department: Optional[str] = None
    year_section: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    role: str
    student_id: Optional[str] = None
    department: Optional[str] = None
    year_section: Optional[str] = None
    temporary_password: Optional[bool] = False

    class Config:
        from_attributes = True


# TOKEN
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# PASS CHANGE
class PasswordChange(BaseModel):
    old_password: str
    new_password: str