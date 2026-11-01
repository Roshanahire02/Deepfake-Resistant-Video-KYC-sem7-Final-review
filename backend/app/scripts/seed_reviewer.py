"""
Create or promote a user to REVIEWER/ADMIN role for local demo/testing.

The public /api/auth/register endpoint always creates a USER-role
account (as it should -- nobody should be able to self-promote to
reviewer over the API). Reviewer/admin accounts are provisioned
out-of-band, exactly like this script, which is the standard pattern
for an academic prototype without a full admin UI.

Usage (from backend/, with the venv active):
    python -m app.scripts.seed_reviewer reviewer@example.com "Reviewer One" reviewerpass123 --role REVIEWER
    python -m app.scripts.seed_reviewer admin@example.com "Admin One" adminpass123 --role ADMIN

If the email already exists, its role is updated instead of creating
a duplicate account.
"""
from __future__ import annotations

import argparse
import uuid

# Import every model module so SQLAlchemy's mapper configuration can
# resolve all relationships (mirrors what app.main does at startup).
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import document, kyc_case, results, user  # noqa: F401
from app.models.user import User, UserRole


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    parser.add_argument("full_name")
    parser.add_argument("password")
    parser.add_argument("--role", choices=["REVIEWER", "ADMIN"], default="REVIEWER")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email).first()
        if existing:
            existing.role = UserRole(args.role)
            existing.password_hash = hash_password(args.password)
            db.commit()
            print(f"Updated existing user {args.email} -> role {args.role}")
        else:
            u = User(
                id=uuid.uuid4(),
                email=args.email,
                full_name=args.full_name,
                password_hash=hash_password(args.password),
                role=UserRole(args.role),
            )
            db.add(u)
            db.commit()
            print(f"Created user {args.email} with role {args.role}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
