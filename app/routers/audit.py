from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.services.audit_logger import get_audit_logs
from app.utils.auth import require_role

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Logs"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    user_id: str | None = Query(None),
    action: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> AuditLogListResponse:
    """View audit logs. Requires admin role."""
    logs, total = get_audit_logs(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
    )
