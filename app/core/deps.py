from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session
from ..config import settings
from ..database import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
        
    # Lazy import to avoid circular dependency
    from ..models.user import User
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise credentials_exception

    # Auto-heal federation_id link for federation admins if not set on the user record
    if user and user.role == "federation_admin" and not user.federation_id:
        from ..models.federation import Federation
        fed = db.query(Federation).filter(Federation.admin_id == user.id).first()
        if fed:
            user.federation_id = fed.id
            db.commit()
            db.refresh(user)
        
    # Check if the user is approved (required for Player, Coach, Sponsor, Scorer roles)
    # Super admins, Department admins do not need approval, or we can handle it globally.
    if user.role != "super_admin" and user.role != "department_admin" and not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is pending approval by the Department admin."
        )
        
    return user
