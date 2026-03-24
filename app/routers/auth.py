from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from app.utils.auth import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: UserRegister, db: Session = Depends(get_db)) -> User:
    """Register a new user account. All new users are assigned the 'patient' role."""
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role="patient",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(request: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate and receive a JWT access token."""
    user = db.query(User).filter(User.email == request.email).first()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(user.id, user.role)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get the current authenticated user's profile."""
    return current_user
