from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None
    user_email: str | None
    user_role: str | None
    action: str
    resource_type: str
    resource_id: str | None
    detail: str
    ip_address: str | None
    status_code: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    logs: list[AuditLogResponse]
    total: int
