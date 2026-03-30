from database import SessionLocal
from models import User
from auth import hash_password
from uuid import uuid4

db = SessionLocal()

existing = db.query(User).filter(
    User.role == "superadmin"
).first()

if existing:
    print("Superadmin already exists")
else:

    superadmin = User(
        id=str(uuid4()),
        name="System Superadmin",
        student_id="SUPERADMIN",
        password_hash=hash_password("admin123"),
        department="IT",
        role="superadmin"
    )

    db.add(superadmin)
    db.commit()

    print("Superadmin created successfully")
    print("Student ID: SUPERADMIN")
    print("Password: admin123")

db.close()