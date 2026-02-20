"""
User Manager — PostgreSQL-backed with in-memory fallback.
Manages user profiles, preferences, API keys, and tenant membership.
"""

import uuid
import hashlib
import secrets
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class UserProfile(BaseModel):
    """User profile in JAI Agent OS."""
    user_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    username: str
    email: str
    first_name: str = ""
    last_name: str = ""
    display_name: str = ""
    avatar_url: str = ""
    tenant_id: str = "default"
    roles: List[str] = Field(default_factory=lambda: ["viewer"])
    is_active: bool = True
    is_keycloak_synced: bool = False
    keycloak_id: Optional[str] = None
    api_keys: List[Dict[str, str]] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _user_from_row(row) -> UserProfile:
    """Convert a UserModel ORM row to a UserProfile Pydantic model."""
    return UserProfile(
        user_id=row.id,
        username=row.username,
        email=row.email,
        first_name=row.first_name or "",
        last_name=row.last_name or "",
        display_name=row.display_name or row.username,
        avatar_url=row.avatar_url or "",
        tenant_id=row.tenant_id or "default",
        roles=row.roles if isinstance(row.roles, list) else [],
        is_active=row.is_active if row.is_active is not None else True,
        preferences=row.preferences if isinstance(row.preferences, dict) else {},
        created_at=row.created_at or datetime.utcnow(),
        last_login=row.last_login,
        metadata=row.metadata_json if isinstance(row.metadata_json, dict) else {},
    )


class UserManager:
    """
    Manages user profiles, API keys, and preferences.
    PostgreSQL-backed with in-memory fallback when DB is unavailable.
    """

    def __init__(self):
        self._users: Dict[str, UserProfile] = {}
        self._email_index: Dict[str, str] = {}  # email -> user_id
        self._username_index: Dict[str, str] = {}  # username -> user_id
        self._api_key_index: Dict[str, str] = {}  # api_key_hash -> user_id
        self._db_available = False

    def _sf(self):
        from backend.db.sync_bridge import get_session_factory
        return get_session_factory()

    # ── Async DB helpers ──────────────────────────────────────────

    async def _db_create(self, username, email, first_name, last_name,
                         roles, tenant_id, display_name) -> Optional[UserProfile]:
        factory = self._sf()
        if not factory:
            return None
        from backend.db.models import UserModel
        uid = uuid.uuid4().hex[:16]
        async with factory() as session:
            row = UserModel(
                id=uid, username=username, email=email,
                first_name=first_name, last_name=last_name,
                display_name=display_name, tenant_id=tenant_id,
                roles=roles, is_active=True,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _user_from_row(row)

    async def _db_get(self, user_id) -> Optional[UserProfile]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import UserModel
        async with factory() as session:
            row = (await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )).scalar_one_or_none()
            return _user_from_row(row) if row else None

    async def _db_get_by_email(self, email) -> Optional[UserProfile]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import UserModel
        async with factory() as session:
            row = (await session.execute(
                select(UserModel).where(UserModel.email == email)
            )).scalar_one_or_none()
            return _user_from_row(row) if row else None

    async def _db_get_by_username(self, username) -> Optional[UserProfile]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import UserModel
        async with factory() as session:
            row = (await session.execute(
                select(UserModel).where(UserModel.username == username)
            )).scalar_one_or_none()
            return _user_from_row(row) if row else None

    async def _db_update(self, user_id, **kwargs) -> Optional[UserProfile]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import UserModel
        async with factory() as session:
            row = (await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )).scalar_one_or_none()
            if not row:
                return None
            for k, v in kwargs.items():
                col = k
                if k == "metadata":
                    col = "metadata_json"
                if hasattr(row, col) and col not in ("id", "created_at"):
                    setattr(row, col, v)
            await session.commit()
            await session.refresh(row)
            return _user_from_row(row)

    async def _db_delete(self, user_id) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import UserModel
        async with factory() as session:
            row = (await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def _db_list(self, tenant_id=None) -> List[UserProfile]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import UserModel
        async with factory() as session:
            q = select(UserModel)
            if tenant_id:
                q = q.where(UserModel.tenant_id == tenant_id)
            q = q.order_by(UserModel.created_at.desc())
            rows = (await session.execute(q)).scalars().all()
            return [_user_from_row(r) for r in rows]

    async def _db_search(self, query) -> List[UserProfile]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select, or_
        from backend.db.models import UserModel
        async with factory() as session:
            q = select(UserModel).where(or_(
                UserModel.username.ilike(f"%{query}%"),
                UserModel.email.ilike(f"%{query}%"),
                UserModel.display_name.ilike(f"%{query}%"),
            ))
            rows = (await session.execute(q)).scalars().all()
            return [_user_from_row(r) for r in rows]

    async def _db_record_login(self, user_id):
        factory = self._sf()
        if not factory:
            return
        from sqlalchemy import select
        from backend.db.models import UserModel
        async with factory() as session:
            row = (await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )).scalar_one_or_none()
            if row:
                row.last_login = datetime.utcnow()
                await session.commit()

    async def _db_stats(self) -> Dict[str, Any]:
        factory = self._sf()
        if not factory:
            return {}
        from sqlalchemy import select, func
        from backend.db.models import UserModel
        async with factory() as session:
            total = (await session.execute(select(func.count(UserModel.id)))).scalar() or 0
            active = (await session.execute(
                select(func.count(UserModel.id)).where(UserModel.is_active == True)
            )).scalar() or 0
            return {
                "total_users": total,
                "active_users": active,
                "persistence": "postgresql",
            }

    # ── Public sync API ───────────────────────────────────────────

    def create_user(self, username, email, first_name="", last_name="",
                    roles=None, tenant_id="default") -> UserProfile:
        display_name = f"{first_name} {last_name}".strip() or username
        r = roles or ["viewer"]
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_create(
                    username, email, first_name, last_name, r, tenant_id, display_name
                ))
                if result:
                    return result
            except Exception as e:
                logger.warning(f"DB create_user failed, falling back: {e}")
        # In-memory fallback
        if email in self._email_index:
            raise ValueError(f"Email '{email}' already registered")
        if username in self._username_index:
            raise ValueError(f"Username '{username}' already taken")
        user = UserProfile(
            username=username, email=email, first_name=first_name,
            last_name=last_name, display_name=display_name,
            roles=r, tenant_id=tenant_id,
        )
        self._users[user.user_id] = user
        self._email_index[email] = user.user_id
        self._username_index[username] = user.user_id
        return user

    def get_user(self, user_id) -> Optional[UserProfile]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_get(user_id))
            except Exception:
                pass
        return self._users.get(user_id)

    def get_by_email(self, email) -> Optional[UserProfile]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_get_by_email(email))
            except Exception:
                pass
        uid = self._email_index.get(email)
        return self._users.get(uid) if uid else None

    def get_by_username(self, username) -> Optional[UserProfile]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_get_by_username(username))
            except Exception:
                pass
        uid = self._username_index.get(username)
        return self._users.get(uid) if uid else None

    def update_user(self, user_id, **kwargs) -> Optional[UserProfile]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_update(user_id, **kwargs))
                if result:
                    return result
            except Exception:
                pass
        user = self._users.get(user_id)
        if not user:
            return None
        for k, v in kwargs.items():
            if hasattr(user, k) and k not in ("user_id", "created_at"):
                setattr(user, k, v)
        return user

    def delete_user(self, user_id) -> bool:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_delete(user_id))
            except Exception:
                pass
        user = self._users.pop(user_id, None)
        if user:
            self._email_index.pop(user.email, None)
            self._username_index.pop(user.username, None)
            for ak in user.api_keys:
                h = hashlib.sha256(ak["key"].encode()).hexdigest()
                self._api_key_index.pop(h, None)
            return True
        return False

    def list_users(self, tenant_id=None) -> List[UserProfile]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_list(tenant_id))
            except Exception:
                pass
        users = list(self._users.values())
        if tenant_id:
            users = [u for u in users if u.tenant_id == tenant_id]
        return sorted(users, key=lambda u: u.created_at, reverse=True)

    def search_users(self, query) -> List[UserProfile]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_search(query))
            except Exception:
                pass
        q = query.lower()
        return [
            u for u in self._users.values()
            if q in u.username.lower() or q in u.email.lower() or q in u.display_name.lower()
        ]

    # ── API Keys ──────────────────────────────────────────────────

    def generate_api_key(self, user_id, name="default") -> Optional[Dict[str, str]]:
        user = self.get_user(user_id)
        if not user:
            return None
        key = f"jai-{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_entry = {
            "name": name, "key": key, "key_prefix": key[:12] + "...",
            "created_at": datetime.utcnow().isoformat(),
        }
        # Store in user metadata (DB or in-memory)
        api_keys = list(user.api_keys) + [key_entry]
        self.update_user(user.user_id, metadata={**(user.metadata or {}), "api_keys": api_keys})
        self._api_key_index[key_hash] = user_id
        return key_entry

    def validate_api_key(self, key) -> Optional[UserProfile]:
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        user_id = self._api_key_index.get(key_hash)
        return self.get_user(user_id) if user_id else None

    def revoke_api_key(self, user_id, key_name) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        for ak in user.api_keys:
            if ak["name"] == key_name:
                h = hashlib.sha256(ak["key"].encode()).hexdigest()
                self._api_key_index.pop(h, None)
                user.api_keys.remove(ak)
                return True
        return False

    # ── Login tracking ────────────────────────────────────────────

    def record_login(self, user_id):
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_record_login(user_id))
                return
            except Exception:
                pass
        user = self._users.get(user_id)
        if user:
            user.last_login = datetime.utcnow()

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_stats())
                if result:
                    return result
            except Exception:
                pass
        users = list(self._users.values())
        return {
            "total_users": len(users),
            "active_users": sum(1 for u in users if u.is_active),
            "by_role": self._count_by_role(users),
            "by_tenant": self._count_by_tenant(users),
            "persistence": "in-memory",
        }

    def _count_by_role(self, users):
        counts = {}
        for u in users:
            for r in u.roles:
                counts[r] = counts.get(r, 0) + 1
        return counts

    def _count_by_tenant(self, users):
        counts = {}
        for u in users:
            counts[u.tenant_id] = counts.get(u.tenant_id, 0) + 1
        return counts
