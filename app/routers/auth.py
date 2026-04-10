import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    DeactivateResponse,
    ForgotPasswordRequest,
    RefreshRequest,
    ResetPasswordRequest,
    RoleUpdate,
    TokenResponse,
    UserListResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.audit_logger import log_action
from app.utils.auth import (
    COOKIE_NAME,
    blacklist_token,
    clear_auth_cookie,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    require_role,
    rotate_refresh_token,
    set_auth_cookie,
    verify_password,
)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, body: UserRegister, db: Session = Depends(get_db)) -> User:
    """Register a new user account. All new users are assigned the 'patient' role."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role="patient",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, response: Response, body: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate and receive a JWT access token (also set as httpOnly cookie)."""
    user = db.query(User).filter(User.email == body.email).first()

    # Account lockout check
    if user is not None and user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=423,
            detail="Account is temporarily locked due to too many failed login attempts. Try again later.",
        )

    if user is None or not verify_password(body.password, user.hashed_password):
        # Increment failed attempts when user exists
        if user is not None:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Reset failed login attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    token = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id, db)
    set_auth_cookie(response, token)
    return TokenResponse(
        access_token=token,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
def logout_user(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    """Clear the auth cookie and blacklist the token."""
    token = request.cookies.get(COOKIE_NAME) or request.headers.get("Authorization", "").removeprefix("Bearer ")
    if token:
        blacklist_token(token, db)
    clear_auth_cookie(response)
    return {"detail": "Logged out"}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange a valid refresh token for new access + refresh tokens."""
    result = rotate_refresh_token(body.refresh_token, db)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    access_token, new_refresh, user = result
    set_auth_cookie(response, access_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get the current authenticated user's profile."""
    return current_user


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    """Request a password reset token. Always returns 200 to avoid revealing if the email exists."""
    user = db.query(User).filter(User.email == body.email).first()
    if user is not None:
        token = secrets.token_urlsafe()
        user.password_reset_token = token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.commit()
    return {"detail": "If that email exists, a reset link has been sent"}


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    """Reset a password using a valid reset token."""
    user = (
        db.query(User)
        .filter(
            User.password_reset_token == body.token,
            User.reset_token_expires.isnot(None),
        )
        .first()
    )
    if user is None or user.reset_token_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(body.new_password)
    user.password_reset_token = None
    user.reset_token_expires = None
    db.commit()
    return {"detail": "Password has been reset successfully"}


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
        db,
        action="update",
        resource_type="user",
        resource_id=user_id,
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
    # Blacklist a fresh token for the deactivated user so any existing
    # sessions are effectively invalidated on next request (the is_active
    # check in get_current_user also guards this, but blacklisting is
    # belt-and-suspenders).
    revoke_token = create_access_token(user.id, user.role)
    blacklist_token(revoke_token)
    db.commit()
    db.refresh(user)

    log_action(
        db,
        action="deactivate",
        resource_type="user",
        resource_id=user_id,
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
        db,
        action="activate",
        resource_type="user",
        resource_id=user_id,
        detail=f"Activated user: {user.email}",
        user=current_user,
        ip_address=http_request.client.host if http_request.client else None,
    )

    return user
