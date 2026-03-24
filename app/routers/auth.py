from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    DeactivateResponse,
    RoleUpdate,
    TokenResponse,
    UserListResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.audit_logger import log_action
from app.utils.auth import create_access_token, get_current_user, hash_password, require_role, verify_password

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


# --- Admin user management ---


@router.get("/users", response_model=UserListResponse)
def list_users(
    role: str | None = Query(None, pattern="^(patient|nurse|doctor|admin)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> UserListResponse:
    """List all users with optional role filter. Requires admin role."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    total = query.count()
    users = query.offset(offset).limit(limit).all()
    return UserListResponse(users=[UserResponse.model_validate(u) for u in users], total=total)


@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: str,
    request: RoleUpdate,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> User:
    """Update a user's role. Requires admin role."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    old_role = user.role
    user.role = request.role
    db.commit()
    db.refresh(user)

    log_action(
        db, action="update", resource_type="user", resource_id=user_id,
        detail=f"Role changed: {old_role} -> {request.role} for {user.email}",
        user=current_user,
        ip_address=http_request.client.host if http_request.client else None,
    )

    return user


@router.put("/users/{user_id}/deactivate", response_model=DeactivateResponse)
def deactivate_user(
    user_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> User:
    """Deactivate a user account. Requires admin role."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    user.is_active = False
    db.commit()
    db.refresh(user)

    log_action(
        db, action="deactivate", resource_type="user", resource_id=user_id,
        detail=f"Deactivated user: {user.email}",
        user=current_user,
        ip_address=http_request.client.host if http_request.client else None,
    )

    return user


@router.put("/users/{user_id}/activate", response_model=DeactivateResponse)
def activate_user(
    user_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> User:
    """Reactivate a user account. Requires admin role."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.commit()
    db.refresh(user)

    log_action(
        db, action="activate", resource_type="user", resource_id=user_id,
        detail=f"Activated user: {user.email}",
        user=current_user,
        ip_address=http_request.client.host if http_request.client else None,
    )

    return user
