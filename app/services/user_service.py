"""Account registration, authentication and profile management."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, CurioError
from app.core.security import dummy_hash, hash_password, needs_rehash, verify_password
from app.models import Collection, Item, User
from app.schemas.user import PasswordChange, ProfileUpdate, UserCreate


@dataclass(frozen=True)
class AccountSummary:
    item_count: int
    collection_count: int
    favourite_count: int


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.username) == username.strip().lower()))


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def register_user(db: Session, data: UserCreate) -> User:
    """Create a new account; raises ``ConflictError`` for duplicate username/email."""
    if get_user_by_username(db, data.username):
        raise ConflictError("That username is already taken.", field="username")
    if get_user_by_email(db, data.email):
        raise ConflictError("An account with that email already exists.", field="email")

    user = User(
        username=data.username,
        email=data.email,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:  # race condition between check and insert
        db.rollback()
        raise ConflictError("That username or email is already registered.") from exc
    db.refresh(user)
    return user


def authenticate(db: Session, identifier: str, password: str) -> User | None:
    """Return the user for a valid username/email + password, else ``None``."""
    identifier = identifier.strip()
    user = get_user_by_email(db, identifier) if "@" in identifier else get_user_by_username(db, identifier)
    if user is None:
        verify_password(password, dummy_hash())  # equalise timing to avoid user enumeration
        return None
    if not verify_password(password, user.password_hash):
        return None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    return user


def update_profile(db: Session, user: User, data: ProfileUpdate) -> User:
    existing = get_user_by_email(db, data.email)
    if existing is not None and existing.id != user.id:
        raise ConflictError("Another account already uses that email.", field="email")
    user.display_name = data.display_name
    user.email = data.email
    user.bio = data.bio
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, data: PasswordChange) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise CurioError("Your current password is incorrect.", field="current_password")
    if data.current_password == data.new_password:
        raise CurioError("Choose a password different from your current one.", field="new_password")
    user.password_hash = hash_password(data.new_password)
    db.commit()


def delete_account(db: Session, user: User, password: str) -> None:
    """Permanently delete the account and all of its items, tags and collections."""
    if not verify_password(password, user.password_hash):
        raise CurioError("Password is incorrect; your account was not deleted.", field="delete_password")
    db.delete(user)
    db.commit()


def account_summary(db: Session, user: User) -> AccountSummary:
    item_count = db.scalar(select(func.count(Item.id)).where(Item.user_id == user.id)) or 0
    favourite_count = (
        db.scalar(select(func.count(Item.id)).where(Item.user_id == user.id, Item.is_favourite.is_(True))) or 0
    )
    collection_count = db.scalar(select(func.count(Collection.id)).where(Collection.user_id == user.id)) or 0
    return AccountSummary(item_count=item_count, collection_count=collection_count, favourite_count=favourite_count)
