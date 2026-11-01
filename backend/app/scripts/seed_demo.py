"""
Creates three LOCAL-DEMO accounts so you can show every role immediately.

    python -m app.scripts.seed_demo

These passwords are public (they are printed below and in the setup guide):
use this ONLY on your own laptop for the demonstration, never on a shared or
deployed server. Safe to re-run: existing accounts are reset to these values.
"""
from __future__ import annotations

import uuid

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import document, kyc_case, results, user  # noqa: F401  (register all tables)
from app.models.user import User, UserRole

DEMO_ACCOUNTS = [
    ("demo.user@example.com", "Demo Applicant", "DemoUser#2026", UserRole.USER),
    ("demo.reviewer@example.com", "Demo Reviewer", "DemoReviewer#2026", UserRole.REVIEWER),
    ("demo.admin@example.com", "Demo Admin", "DemoAdmin#2026", UserRole.ADMIN),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for email, name, password, role in DEMO_ACCOUNTS:
            u = db.query(User).filter(User.email == email).first()
            if u:
                u.full_name, u.password_hash, u.role = name, hash_password(password), role
            else:
                db.add(User(id=uuid.uuid4(), email=email, full_name=name, password_hash=hash_password(password), role=role))
        db.commit()
    finally:
        db.close()
    print("Demo accounts ready (LOCAL DEMO ONLY):")
    for email, _, password, role in DEMO_ACCOUNTS:
        print(f"  {role.value:9s} {email:30s} password: {password}")


if __name__ == "__main__":
    main()
