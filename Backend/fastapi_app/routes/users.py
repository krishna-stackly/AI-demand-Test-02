from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from fastapi_app.db.session import get_db
from fastapi_app.core.dependencies import get_current_user
from fastapi_app.core.permissions import require_permission
from fastapi_app.models.auth_model import User
from fastapi_app.models.role_model import Role
from fastapi_app.schemas.user_schema import UserCreate, UserUpdate, UserManagementOut
from fastapi_app.services.users.user_service import (
    get_user_by_id,
    list_users,
    create_user,
    update_user,
    delete_user,
)

router = APIRouter(prefix="", tags=["Authentication"])


def _check_last_active_super_admin(db: Session, target_user: User, block_deactivation_or_role_change: bool = False) -> None:
    """Helper to prevent deactivating, deleting, or changing the role of the last active super admin."""
    super_admin_role = db.query(Role).filter(Role.name == "super_admin").first()
    if not super_admin_role:
        return

    # Check if the target user has the super_admin role
    if target_user.role_id == super_admin_role.id and target_user.is_active:
        # Count other active super admins
        active_super_admins = db.query(User).filter(
            User.role_id == super_admin_role.id,
            User.is_active == True
        ).count()

        if active_super_admins <= 1:
            action = "deactivate or change the role of" if block_deactivation_or_role_change else "delete"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You cannot {action} the last active super_admin account in the system."
            )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/users
# ─────────────────────────────────────────────────────────────────────────────
@router.get("", response_model=List[UserManagementOut])
def list_users_endpoint(
    search: Optional[str] = Query(None, description="Search by name or email"),
    role_id: Optional[int] = Query(None, description="Filter by role ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "users:read")
    return list_users(db, search=search, role_id=role_id, is_active=is_active, skip=skip, limit=limit)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/users/{user_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{user_id}", response_model=UserManagementOut)
def get_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "users:read")
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return user


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/users
# ─────────────────────────────────────────────────────────────────────────────
@router.post("", response_model=UserManagementOut, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "users:write")
    try:
        return create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/users/{user_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.put("/{user_id}", response_model=UserManagementOut)
def update_user_endpoint(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "users:write")

    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Guard rail: Prevent deactivating oneself or changing own role
    if current_user.id == user_id:
        if payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account."
            )
        if payload.role_id is not None and payload.role_id != current_user.role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own role to prevent self-lockout."
            )

    # Guard rail: Prevent deactivating or changing the role of the last active super admin
    if payload.is_active is False or (payload.role_id is not None and payload.role_id != target_user.role_id):
        _check_last_active_super_admin(db, target_user, block_deactivation_or_role_change=True)

    try:
        updated = update_user(db, user_id, payload)
        return updated
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/users/{user_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "users:delete")

    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Guard rail: Prevent deleting oneself
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account."
        )

    # Guard rail: Prevent deleting the last active super admin
    _check_last_active_super_admin(db, target_user, block_deactivation_or_role_change=False)

    if not delete_user(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    return {"message": "User deleted successfully."}
