from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi_app.db.session import get_db
from fastapi_app.core.dependencies import get_current_super_admin
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.role_schema import RoleOut, PermissionOut
from fastapi_app.services.roles.role_service import (
    get_all_roles,
    get_all_permissions,
)

router = APIRouter(prefix="/api/roles", tags=["Roles & Permissions"])

# All endpoints in this router are super_admin only.


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/roles/roles
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/roles", response_model=List[RoleOut])
def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    return get_all_roles(db, skip=skip, limit=limit)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/roles/permissions   (fixed catalog, read-only)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/permissions", response_model=List[PermissionOut])
def list_permissions(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    return get_all_permissions(db)