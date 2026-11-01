"""ADMIN-only user management (list users, change a user's role)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.models.kyc_case import KYCCase
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin_only = require_role(UserRole.ADMIN)


class RoleChange(BaseModel):
    role: str  # USER | REVIEWER | ADMIN


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    counts = {}
    for (uid,) in db.query(KYCCase.user_id).all():
        counts[uid] = counts.get(uid, 0) + 1
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "case_count": counts.get(u.id, 0),
        }
        for u in users
    ]


@router.put("/users/{user_id}/role")
def change_role(user_id: str, payload: RoleChange, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if payload.role not in UserRole.__members__:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="role must be USER, REVIEWER or ADMIN.")
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id.")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own role.")
    user.role = UserRole(payload.role)
    db.commit()
    return {"id": str(user.id), "email": user.email, "role": user.role.value}
