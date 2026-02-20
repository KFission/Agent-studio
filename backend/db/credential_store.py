"""
CredentialStore — encrypted storage for LLM provider credentials.
Uses Fernet symmetric encryption for at-rest protection of service account JSON, API keys, etc.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import settings
from backend.db.models import ProviderCredentialModel

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Get the Fernet cipher from the configured encryption key."""
    key = settings.encryption_key
    if not key:
        raise ValueError(
            "ENCRYPTION_KEY not set. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def _encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string and return a base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def _decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext back to plaintext."""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("Failed to decrypt credential — key mismatch or corrupted data")


class CredentialStore:
    """Async CRUD for provider credentials with encryption at rest."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def store(
        self,
        name: str,
        provider: str,
        credential_data: dict,
        display_metadata: Optional[dict] = None,
        created_by: str = "",
    ) -> Dict[str, Any]:
        """
        Encrypt and store a credential.

        Args:
            name: Human-readable name (e.g. "Vertex AI - Production")
            provider: Provider identifier ("google", "anthropic", "openai")
            credential_data: The secret data (service account JSON, API key dict, etc.)
            display_metadata: Non-secret metadata for display (project_id, region, etc.)
            created_by: User who uploaded the credential

        Returns:
            Dict with id, name, provider, display_metadata
        """
        cred_id = f"cred-{uuid.uuid4().hex[:8]}"
        encrypted_blob = _encrypt(json.dumps(credential_data))

        # Extract non-secret display info from service account JSON
        if display_metadata is None:
            display_metadata = {}
        if provider == "google" and "project_id" in credential_data:
            display_metadata["project_id"] = credential_data["project_id"]
            display_metadata["client_email"] = credential_data.get("client_email", "")

        row = ProviderCredentialModel(
            id=cred_id,
            name=name,
            provider=provider,
            credential_blob=encrypted_blob,
            display_metadata=display_metadata,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=created_by,
        )
        self._session.add(row)
        await self._session.flush()
        logger.info(f"Stored credential {cred_id} ({name}) for provider {provider}")

        return {
            "id": cred_id,
            "name": name,
            "provider": provider,
            "display_metadata": display_metadata,
        }

    async def get_decrypted(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt a credential by ID. Returns the raw secret data."""
        result = await self._session.execute(
            select(ProviderCredentialModel).where(ProviderCredentialModel.id == credential_id)
        )
        row = result.scalar_one_or_none()
        if not row or not row.is_active:
            return None
        decrypted = _decrypt(row.credential_blob)
        return json.loads(decrypted)

    async def get_metadata(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """Get credential metadata without decrypting the secret."""
        result = await self._session.execute(
            select(ProviderCredentialModel).where(ProviderCredentialModel.id == credential_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "provider": row.provider,
            "display_metadata": row.display_metadata,
            "is_active": row.is_active,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "created_by": row.created_by,
        }

    async def list_all(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all credentials (metadata only, never secrets)."""
        stmt = select(ProviderCredentialModel).order_by(ProviderCredentialModel.created_at.desc())
        if provider:
            stmt = stmt.where(ProviderCredentialModel.provider == provider)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "provider": r.provider,
                "display_metadata": r.display_metadata,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def deactivate(self, credential_id: str) -> bool:
        """Soft-delete a credential by marking it inactive."""
        result = await self._session.execute(
            select(ProviderCredentialModel).where(ProviderCredentialModel.id == credential_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        row.is_active = False
        row.updated_at = datetime.utcnow()
        await self._session.flush()
        logger.info(f"Deactivated credential {credential_id}")
        return True

    async def hard_delete(self, credential_id: str) -> bool:
        """Permanently delete a credential."""
        result = await self._session.execute(
            delete(ProviderCredentialModel).where(ProviderCredentialModel.id == credential_id)
        )
        return result.rowcount > 0
