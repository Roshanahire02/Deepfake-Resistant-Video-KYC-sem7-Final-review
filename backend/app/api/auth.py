from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limit
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(limit("register", "RATE_LIMIT_REGISTER_PER_MIN"))])
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(id=str(user.id), email=user.email, full_name=user.full_name, role=user.role.value)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(limit("login", "RATE_LIMIT_LOGIN_PER_MIN"))])
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(subject=str(user.id), role=user.role.value)
    return TokenResponse(access_token=token, role=user.role.value)


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return UserOut(id=str(current.id), email=current.email, full_name=current.full_name, role=current.role.value)
