"""
RBAC — Role-Based Access Control for JAI Agent OS.
Defines roles, permissions, and policy enforcement for agents, tools,
orchestrators, and platform resources. Integrates with Keycloak roles.
"""

import uuid
from typing import Optional, Dict, List, Set, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Permission(str, Enum):
    """Fine-grained permissions for JAI Agent OS resources."""
    # Agent permissions
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_DEPLOY = "agent:deploy"
    AGENT_EXECUTE = "agent:execute"
    AGENT_CONFIGURE = "agent:configure"

    # Orchestrator permissions
    ORCHESTRATOR_CREATE = "orchestrator:create"
    ORCHESTRATOR_READ = "orchestrator:read"
    ORCHESTRATOR_UPDATE = "orchestrator:update"
    ORCHESTRATOR_DELETE = "orchestrator:delete"
    ORCHESTRATOR_EXECUTE = "orchestrator:execute"

    # Tool permissions
    TOOL_CREATE = "tool:create"
    TOOL_READ = "tool:read"
    TOOL_UPDATE = "tool:update"
    TOOL_DELETE = "tool:delete"
    TOOL_EXECUTE = "tool:execute"

    # Model permissions
    MODEL_READ = "model:read"
    MODEL_CONFIGURE = "model:configure"
    MODEL_TEST = "model:test"

    # Prompt permissions
    PROMPT_CREATE = "prompt:create"
    PROMPT_READ = "prompt:read"
    PROMPT_UPDATE = "prompt:update"
    PROMPT_DELETE = "prompt:delete"

    # RAG permissions
    RAG_COLLECTION_CREATE = "rag:collection:create"
    RAG_COLLECTION_READ = "rag:collection:read"
    RAG_COLLECTION_DELETE = "rag:collection:delete"
    RAG_DOCUMENT_UPLOAD = "rag:document:upload"
    RAG_DOCUMENT_DELETE = "rag:document:delete"

    # Data permissions
    DB_STRUCTURED_READ = "db:structured:read"
    DB_STRUCTURED_WRITE = "db:structured:write"
    DB_UNSTRUCTURED_READ = "db:unstructured:read"
    DB_UNSTRUCTURED_WRITE = "db:unstructured:write"

    # Admin permissions
    USER_MANAGE = "user:manage"
    ROLE_MANAGE = "role:manage"
    PLATFORM_ADMIN = "platform:admin"
    AUDIT_READ = "audit:read"

    # Channel permissions
    CHANNEL_MANAGE = "channel:manage"
    WEBHOOK_MANAGE = "webhook:manage"

    # Observability
    OBSERVABILITY_READ = "observability:read"


class Role(BaseModel):
    """A role with a set of permissions."""
    role_id: str = Field(default_factory=lambda: f"role-{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    permissions: Set[Permission] = Field(default_factory=set)
    is_system: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Built-in Roles ───────────────────────────────────────────────

BUILT_IN_ROLES: Dict[str, Role] = {
    "platform_admin": Role(
        role_id="role-admin",
        name="platform_admin",
        description="Full platform access — all permissions",
        permissions=set(Permission),
        is_system=True,
    ),
    "agent_developer": Role(
        role_id="role-dev",
        name="agent_developer",
        description="Create, configure, and test agents and tools",
        permissions={
            Permission.AGENT_CREATE, Permission.AGENT_READ, Permission.AGENT_UPDATE,
            Permission.AGENT_DELETE, Permission.AGENT_DEPLOY, Permission.AGENT_EXECUTE,
            Permission.AGENT_CONFIGURE,
            Permission.ORCHESTRATOR_CREATE, Permission.ORCHESTRATOR_READ,
            Permission.ORCHESTRATOR_UPDATE, Permission.ORCHESTRATOR_DELETE,
            Permission.ORCHESTRATOR_EXECUTE,
            Permission.TOOL_CREATE, Permission.TOOL_READ, Permission.TOOL_UPDATE,
            Permission.TOOL_DELETE, Permission.TOOL_EXECUTE,
            Permission.MODEL_READ, Permission.MODEL_CONFIGURE, Permission.MODEL_TEST,
            Permission.PROMPT_CREATE, Permission.PROMPT_READ, Permission.PROMPT_UPDATE,
            Permission.PROMPT_DELETE,
            Permission.RAG_COLLECTION_CREATE, Permission.RAG_COLLECTION_READ,
            Permission.RAG_COLLECTION_DELETE, Permission.RAG_DOCUMENT_UPLOAD,
            Permission.RAG_DOCUMENT_DELETE,
            Permission.DB_STRUCTURED_READ, Permission.DB_UNSTRUCTURED_READ,
            Permission.OBSERVABILITY_READ,
        },
        is_system=True,
    ),
    "agent_operator": Role(
        role_id="role-ops",
        name="agent_operator",
        description="Execute agents, view results, manage channels",
        permissions={
            Permission.AGENT_READ, Permission.AGENT_EXECUTE,
            Permission.ORCHESTRATOR_READ, Permission.ORCHESTRATOR_EXECUTE,
            Permission.TOOL_READ, Permission.TOOL_EXECUTE,
            Permission.MODEL_READ,
            Permission.PROMPT_READ,
            Permission.RAG_COLLECTION_READ,
            Permission.DB_STRUCTURED_READ, Permission.DB_UNSTRUCTURED_READ,
            Permission.CHANNEL_MANAGE, Permission.WEBHOOK_MANAGE,
            Permission.OBSERVABILITY_READ,
        },
        is_system=True,
    ),
    "viewer": Role(
        role_id="role-viewer",
        name="viewer",
        description="Read-only access to agents, tools, and observability",
        permissions={
            Permission.AGENT_READ, Permission.ORCHESTRATOR_READ,
            Permission.TOOL_READ, Permission.MODEL_READ,
            Permission.PROMPT_READ, Permission.RAG_COLLECTION_READ,
            Permission.OBSERVABILITY_READ,
        },
        is_system=True,
    ),
}


class ResourceACL(BaseModel):
    """Access control list for a specific resource (agent, tool, etc.)."""
    resource_id: str
    resource_type: str  # agent, tool, orchestrator, collection
    owner_id: str
    allowed_users: Set[str] = Field(default_factory=set)
    allowed_roles: Set[str] = Field(default_factory=set)
    is_public: bool = False


class RBACManager:
    """
    Manages roles, permissions, and resource-level access controls.
    Integrates with Keycloak realm roles for SSO-based authorization.
    """

    def __init__(self):
        self._roles: Dict[str, Role] = dict(BUILT_IN_ROLES)
        self._user_roles: Dict[str, Set[str]] = {}  # user_id -> {role_names}
        self._resource_acls: Dict[str, ResourceACL] = {}  # resource_id -> ACL
        self._audit_log: List[Dict[str, Any]] = []

    # ── Role Management ───────────────────────────────────────────

    def create_role(self, name: str, description: str, permissions: Set[Permission]) -> Role:
        role = Role(name=name, description=description, permissions=permissions)
        self._roles[name] = role
        return role

    def get_role(self, name: str) -> Optional[Role]:
        return self._roles.get(name)

    def list_roles(self) -> List[Role]:
        return list(self._roles.values())

    def delete_role(self, name: str) -> bool:
        role = self._roles.get(name)
        if role and not role.is_system:
            del self._roles[name]
            return True
        return False

    # ── User-Role Assignment ──────────────────────────────────────

    def assign_role(self, user_id: str, role_name: str) -> bool:
        if role_name not in self._roles:
            return False
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        self._user_roles[user_id].add(role_name)
        self._log_audit(user_id, "role_assigned", {"role": role_name})
        return True

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        if user_id in self._user_roles:
            self._user_roles[user_id].discard(role_name)
            self._log_audit(user_id, "role_revoked", {"role": role_name})
            return True
        return False

    def get_user_roles(self, user_id: str) -> List[str]:
        return list(self._user_roles.get(user_id, set()))

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        perms = set()
        for role_name in self._user_roles.get(user_id, set()):
            role = self._roles.get(role_name)
            if role:
                perms.update(role.permissions)
        return perms

    # ── Permission Checking ───────────────────────────────────────

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        return permission in self.get_user_permissions(user_id)

    def check_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        user_perms = self.get_user_permissions(user_id)
        return any(p in user_perms for p in permissions)

    def require_permission(self, user_id: str, permission: Permission) -> None:
        """Raise if user lacks permission."""
        if not self.check_permission(user_id, permission):
            raise PermissionError(
                f"User '{user_id}' lacks permission '{permission.value}'"
            )

    # ── Resource ACLs ─────────────────────────────────────────────

    def set_resource_acl(
        self,
        resource_id: str,
        resource_type: str,
        owner_id: str,
        allowed_users: Optional[Set[str]] = None,
        allowed_roles: Optional[Set[str]] = None,
        is_public: bool = False,
    ) -> ResourceACL:
        acl = ResourceACL(
            resource_id=resource_id,
            resource_type=resource_type,
            owner_id=owner_id,
            allowed_users=allowed_users or set(),
            allowed_roles=allowed_roles or set(),
            is_public=is_public,
        )
        self._resource_acls[resource_id] = acl
        return acl

    def check_resource_access(self, user_id: str, resource_id: str) -> bool:
        acl = self._resource_acls.get(resource_id)
        if not acl:
            return True  # no ACL = open access

        if acl.is_public:
            return True
        if user_id == acl.owner_id:
            return True
        if user_id in acl.allowed_users:
            return True

        user_roles = self._user_roles.get(user_id, set())
        if user_roles & acl.allowed_roles:
            return True

        # Platform admins always have access
        if "platform_admin" in user_roles:
            return True

        return False

    def get_resource_acl(self, resource_id: str) -> Optional[ResourceACL]:
        return self._resource_acls.get(resource_id)

    # ── Audit Log ─────────────────────────────────────────────────

    def _log_audit(self, user_id: str, action: str, details: Dict[str, Any] = None):
        self._audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details or {},
        })

    def get_audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._audit_log[-limit:]
