"""
Keycloak IDP Integration — Authentication provider for JAI Agent OS.
Supports OIDC token validation, user info retrieval, role mapping,
and service account operations. Follows the OAP AuthProvider pattern.
"""

import time
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

import httpx


class TokenInfo(BaseModel):
    """Decoded/validated token information."""
    sub: str  # user ID
    email: Optional[str] = None
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    realm_access: Dict[str, List[str]] = Field(default_factory=dict)
    resource_access: Dict[str, Any] = Field(default_factory=dict)
    exp: Optional[int] = None
    iat: Optional[int] = None
    scope: str = ""
    tenant_id: Optional[str] = None


class AuthResult(BaseModel):
    """Result of an authentication operation."""
    success: bool = False
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_info: Optional[TokenInfo] = None
    error: Optional[str] = None


class KeycloakProvider:
    """
    Keycloak IDP provider for JAI Agent OS.
    Handles OIDC authentication, token validation, and user management.
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8180",
        realm: str = "jai-agent-os",
        client_id: str = "jai-agent-os-api",
        client_secret: str = "",
        admin_username: str = "admin",
        admin_password: str = "admin",
    ):
        self._server_url = server_url.rstrip("/")
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret
        self._admin_username = admin_username
        self._admin_password = admin_password
        self._admin_token: Optional[str] = None
        self._admin_token_exp: float = 0
        self._token_cache: Dict[str, TokenInfo] = {}

    @property
    def _base_url(self) -> str:
        return f"{self._server_url}/realms/{self._realm}"

    @property
    def _admin_url(self) -> str:
        return f"{self._server_url}/admin/realms/{self._realm}"

    @property
    def _token_url(self) -> str:
        return f"{self._base_url}/protocol/openid-connect/token"

    @property
    def _userinfo_url(self) -> str:
        return f"{self._base_url}/protocol/openid-connect/userinfo"

    @property
    def _introspect_url(self) -> str:
        return f"{self._base_url}/protocol/openid-connect/token/introspect"

    def is_configured(self) -> bool:
        return bool(self._server_url and self._realm and self._client_id)

    # ── Token Operations ──────────────────────────────────────────

    async def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate user with username/password via Keycloak."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._token_url,
                    data={
                        "grant_type": "password",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "username": username,
                        "password": password,
                        "scope": "openid profile email",
                    },
                )
                if response.status_code != 200:
                    return AuthResult(success=False, error=f"Authentication failed: {response.text}")

                data = response.json()
                token_info = await self.validate_token(data["access_token"])

                return AuthResult(
                    success=True,
                    user_id=token_info.sub if token_info else None,
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_in=data.get("expires_in"),
                    token_info=token_info,
                )
        except Exception as e:
            return AuthResult(success=False, error=str(e))

    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """Refresh an access token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._token_url,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "refresh_token": refresh_token,
                    },
                )
                if response.status_code != 200:
                    return AuthResult(success=False, error="Token refresh failed")

                data = response.json()
                return AuthResult(
                    success=True,
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_in=data.get("expires_in"),
                )
        except Exception as e:
            return AuthResult(success=False, error=str(e))

    async def validate_token(self, token: str) -> Optional[TokenInfo]:
        """Validate and decode an access token via introspection."""
        if token in self._token_cache:
            cached = self._token_cache[token]
            if cached.exp and cached.exp > time.time():
                return cached

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._introspect_url,
                    data={
                        "token": token,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                    },
                )
                if response.status_code != 200:
                    return None

                data = response.json()
                if not data.get("active"):
                    return None

                info = TokenInfo(
                    sub=data.get("sub", ""),
                    email=data.get("email"),
                    name=data.get("name"),
                    preferred_username=data.get("preferred_username"),
                    realm_access=data.get("realm_access", {}),
                    resource_access=data.get("resource_access", {}),
                    exp=data.get("exp"),
                    iat=data.get("iat"),
                    scope=data.get("scope", ""),
                    tenant_id=data.get("tenant_id"),
                )
                self._token_cache[token] = info
                return info
        except Exception:
            return None

    async def get_userinfo(self, token: str) -> Optional[Dict[str, Any]]:
        """Get user info from Keycloak userinfo endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._userinfo_url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        return None

    # ── Admin Operations ──────────────────────────────────────────

    async def _get_admin_token(self) -> Optional[str]:
        """Get admin access token for Keycloak admin API."""
        if self._admin_token and self._admin_token_exp > time.time():
            return self._admin_token

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._server_url}/realms/master/protocol/openid-connect/token",
                    data={
                        "grant_type": "password",
                        "client_id": "admin-cli",
                        "username": self._admin_username,
                        "password": self._admin_password,
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    self._admin_token = data["access_token"]
                    self._admin_token_exp = time.time() + data.get("expires_in", 300) - 30
                    return self._admin_token
        except Exception:
            pass
        return None

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        roles: Optional[List[str]] = None,
        attributes: Optional[Dict[str, List[str]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a user in Keycloak."""
        admin_token = await self._get_admin_token()
        if not admin_token:
            return None

        user_data = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "emailVerified": True,
            "credentials": [{"type": "password", "value": password, "temporary": False}],
            "attributes": attributes or {},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._admin_url}/users",
                    json=user_data,
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
                if response.status_code == 201:
                    location = response.headers.get("Location", "")
                    user_id = location.split("/")[-1] if location else ""

                    if roles and user_id:
                        await self._assign_roles(admin_token, user_id, roles)

                    return {"user_id": user_id, "username": username, "email": email}
        except Exception:
            pass
        return None

    async def _assign_roles(self, admin_token: str, user_id: str, role_names: List[str]):
        """Assign realm roles to a user."""
        try:
            async with httpx.AsyncClient() as client:
                roles_response = await client.get(
                    f"{self._admin_url}/roles",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
                if roles_response.status_code != 200:
                    return

                all_roles = roles_response.json()
                roles_to_assign = [r for r in all_roles if r["name"] in role_names]

                if roles_to_assign:
                    await client.post(
                        f"{self._admin_url}/users/{user_id}/role-mappings/realm",
                        json=roles_to_assign,
                        headers={"Authorization": f"Bearer {admin_token}"},
                    )
        except Exception:
            pass

    async def list_users(self, search: str = "", max_results: int = 100) -> List[Dict[str, Any]]:
        """List users from Keycloak."""
        admin_token = await self._get_admin_token()
        if not admin_token:
            return []

        try:
            async with httpx.AsyncClient() as client:
                params = {"max": max_results}
                if search:
                    params["search"] = search
                response = await client.get(
                    f"{self._admin_url}/users",
                    params=params,
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        return []

    async def get_user_roles(self, user_id: str) -> List[str]:
        """Get roles assigned to a user."""
        admin_token = await self._get_admin_token()
        if not admin_token:
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._admin_url}/users/{user_id}/role-mappings/realm",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
                if response.status_code == 200:
                    return [r["name"] for r in response.json()]
        except Exception:
            pass
        return []

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user from Keycloak."""
        admin_token = await self._get_admin_token()
        if not admin_token:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self._admin_url}/users/{user_id}",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
                return response.status_code == 204
        except Exception:
            return False

    # ── Fallback (no Keycloak) ────────────────────────────────────

    def create_local_session(self, username: str, roles: List[str] = None) -> AuthResult:
        """Create a local session when Keycloak is not available (dev mode)."""
        user_id = uuid.uuid4().hex[:16]
        token = f"local-{user_id}-{int(time.time())}"
        info = TokenInfo(
            sub=user_id,
            email=f"{username}@local",
            name=username,
            preferred_username=username,
            realm_access={"roles": roles or ["user"]},
            exp=int(time.time()) + 86400,
        )
        self._token_cache[token] = info
        return AuthResult(
            success=True,
            user_id=user_id,
            access_token=token,
            expires_in=86400,
            token_info=info,
        )
