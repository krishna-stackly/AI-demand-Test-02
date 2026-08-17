from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from fastapi_app.models.auth_model import User
from fastapi_app.models.role_model import Role
from fastapi_app.models.permission_model import Permission
from fastapi_app.core.security import hash_password
from fastapi_app.schemas.user_schema import UserCreate, UserUpdate


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Retrieve a user by ID, including inactive users."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email_any(db: Session, email: str) -> Optional[User]:
    """Retrieve a user by email, including inactive users (useful for uniqueness checks)."""
    return db.query(User).filter(User.email.ilike(email)).first()


def _resolve_permissions(db: Session, permission_ids: List[int]) -> List[Permission]:
    """Resolve a list of permission IDs to Permission models. Raises ValueError if any ID is invalid."""
    if not permission_ids:
        return []

    permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
    found_ids = {p.id for p in permissions}
    missing = set(permission_ids) - found_ids
    if missing:
        raise ValueError(f"permission_ids not found: {sorted(missing)}")
    return permissions


def list_users(
    db: Session,
    search: Optional[str] = None,
    role_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[User]:
    """List users with optional search, role filter, active status filter, and pagination."""
    query = db.query(User)

    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    if role_id is not None:
        query = query.filter(User.role_id == role_id)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    return query.order_by(User.id.asc()).offset(skip).limit(limit).all()


def create_user(db: Session, payload: UserCreate) -> User:
    """Create a new user, hashes password, resolves permissions, and checks for uniqueness of email."""
    # Check email uniqueness
    existing_user = get_user_by_email_any(db, payload.email)
    if existing_user:
        raise ValueError("A user with this email address already exists.")

    # Check role exists
    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise ValueError("The selected role does not exist.")

    # Resolve direct user permissions
    permissions = _resolve_permissions(db, payload.permission_ids)

    # Hash the password
    hashed_password = hash_password(payload.password)

    user = User(
        name=payload.name,
        email=payload.email,
        password=hashed_password,
        initial_password_hash=hashed_password,
        role_id=payload.role_id,
        is_active=payload.is_active,
    )
    user.permissions = permissions

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, payload: UserUpdate) -> Optional[User]:
    """Update user information. Hashes password if provided. Resolves direct permissions. Enforces email uniqueness."""
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    update_data = payload.dict(exclude_unset=True)

    # If email is being updated, check for uniqueness
    new_email = update_data.get("email")
    if new_email and new_email.lower() != user.email.lower():
        existing_user = get_user_by_email_any(db, new_email)
        if existing_user:
            raise ValueError("A user with this email address already exists.")

    # If role is being updated, check if it exists
    new_role_id = update_data.get("role_id")
    if new_role_id is not None:
        role = db.query(Role).filter(Role.id == new_role_id).first()
        if not role:
            raise ValueError("The selected role does not exist.")

    # If permissions are being updated, resolve and replace them
    if "permission_ids" in update_data:
        permission_ids = update_data.pop("permission_ids")
        user.permissions = _resolve_permissions(db, permission_ids) if permission_ids is not None else []

    # If password is being updated, hash it
    new_password = update_data.get("password")
    if new_password:
        hashed_password = hash_password(new_password)
        user.password = hashed_password
        update_data.pop("password")

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user. Returns False if they don't exist."""
    user = get_user_by_id(db, user_id)
    if not user:
        return False

    db.delete(user)
    db.commit()
    return True
