"""
Create the first admin user.

Run inside the backend container:

    docker compose exec backend python -m app.scripts.create_admin

Prompts for name / email / password. Idempotent — refuses if email exists.
"""
import getpass
import sys

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User, UserRole


def main() -> int:
    db = SessionLocal()
    try:
        name = input("Name: ").strip() or "Admin"
        email = input("Email: ").strip().lower()
        if not email:
            print("Email required.")
            return 1
        if db.query(User).filter(User.email == email).first():
            print(f"User with email {email!r} already exists.")
            return 1
        pw = getpass.getpass("Password (min 8 chars): ")
        if len(pw) < 8:
            print("Password too short.")
            return 1
        user = User(
            name=name,
            email=email,
            role=UserRole.ADMIN.value,
            password_hash=hash_password(pw),
        )
        db.add(user)
        db.commit()
        print(f"Created admin user id={user.id} email={user.email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
