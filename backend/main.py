import os
from fastapi import FastAPI, Depends, HTTPException, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from uuid import uuid4

from database import engine, get_db
from models import Base, User, Task, HourLog
from auth import hash_password, verify_password, create_access_token, verify_token
from schemas import PasswordChange, UserCreate, StatusUpdate, TaskCreate

app = FastAPI(title="SCAMS API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

security = HTTPBearer()


# auth hlprs
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def get_superadmin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return current_user


# default supad
def create_default_superadmin():
    db = next(get_db())
    SUPERADMIN_EMAIL = "superadmin@scams.local"
    SUPERADMIN_PASSWORD = "superadmin123"
    existing = db.query(User).filter(User.role == "superadmin").first()
    if existing:
        print("Superadmin already exists.")
        return
    superadmin = User(
        id=str(uuid4()),
        name="System Superadmin",
        email=SUPERADMIN_EMAIL,
        password_hash=hash_password(SUPERADMIN_PASSWORD),
        role="superadmin",
        department="Information Technology",
        year_section=None,
        student_id=None,
        temporary_password=False,
    )
    try:
        db.add(superadmin)
        db.commit()
        print("Superadmin created. Email:", SUPERADMIN_EMAIL, "| Password:", SUPERADMIN_PASSWORD)
    except IntegrityError:
        db.rollback()
        print("Superadmin creation failed (IntegrityError).")


create_default_superadmin()


# AUTH ROUTES 
@app.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "student_id": user.student_id,
            "department": user.department,
            "year_section": user.year_section,
            "temporary_password": user.temporary_password,
        },
    }


@app.post("/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    new_user = User(
        id=str(uuid4()),
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role="student",
        student_id=user_data.student_id,
        department=user_data.department,
        year_section=user_data.year_section,
        temporary_password=False,
    )
    db.add(new_user)
    db.commit()
    return {"message": "Account created successfully"}


# don't u dare touch this one.
@app.patch("/users/{user_id}/password")
def change_password(
    user_id: str,
    change: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only change your own password")
    if not verify_password(change.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Old password incorrect")
    user.password_hash = hash_password(change.new_password)
    user.temporary_password = False
    db.commit()
    return {"message": "Password updated successfully"}


# Task
@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Task).all()


@app.post("/tasks")
def create_task(task: TaskCreate, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    new_task = Task(
        id=str(uuid4()),
        title=task.title,
        description=task.description,
        required_hours=task.required_hours,
        location=task.location,
        task_date=task.task_date,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.patch("/tasks/{task_id}")
def update_task(
    task_id: str,
    task: TaskCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.title = task.title
    db_task.description = task.description
    db_task.required_hours = task.required_hours
    db_task.location = task.location
    db_task.task_date = task.task_date
    db.commit()
    db.refresh(db_task)
    return db_task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}


# Hour logs
@app.get("/logs")
def get_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "student":
        return db.query(HourLog).filter(HourLog.student_id == current_user.student_id).all()
    return db.query(HourLog).all()


@app.post("/logs")
async def create_log(
    student_id: str = Form(...),
    task_id: str = Form(...),
    hours_rendered: float = Form(...),
    date: str = Form(...),
    documentation: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(documentation.filename)[-1]
    filename = f"{uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(await documentation.read())

    new_log = HourLog(
        id=str(uuid4()),
        student_id=student_id,
        task_id=task_id,
        hours_rendered=hours_rendered,
        date=date,
        status="pending",
        documentation_path=filename,
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log


@app.patch("/logs/{log_id}/status")
def update_log_status(
    log_id: str,
    update: StatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    log = db.query(HourLog).filter(HourLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    if update.status not in ("approved", "rejected", "pending"):
        raise HTTPException(status_code=400, detail="Invalid status")
    log.status = update.status
    db.commit()
    return log


# don't u dare touch this either.
@app.get("/students")
def get_students(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    students = db.query(User).filter(User.role == "student").all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "email": s.email,
            "student_id": s.student_id,
            "department": s.department,
            "year_section": s.year_section,
        }
        for s in students
    ]


# SUPAD UM
@app.get("/superadmin/users")
def list_all_users(db: Session = Depends(get_db), superadmin: User = Depends(get_superadmin_user)):
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "department": u.department,
            "year_section": u.year_section,
            "student_id": u.student_id,
            "temporary_password": u.temporary_password,
        }
        for u in db.query(User).all()
    ]


@app.post("/superadmin/admins")
def create_admin(
    name: str = Form(...),
    email: str = Form(...),
    department: str = Form(...),
    year_section: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    superadmin: User = Depends(get_superadmin_user),
):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    temp_password = str(uuid4())[:8]
    new_admin = User(
        id=str(uuid4()),
        name=name,
        email=email,
        password_hash=hash_password(temp_password),
        role="admin",
        department=department,
        year_section=None,   
        student_id=None,
        temporary_password=True,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return {
        "message": "Admin account created",
        "email": new_admin.email,
        "temporary_password": temp_password,
    }


@app.delete("/superadmin/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    superadmin: User = Depends(get_superadmin_user),
):
    if user_id == superadmin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": f"User '{user.name}' deleted"}