"""
AgentRepository — async CRUD for agents backed by PostgreSQL.
Bridges between the Pydantic AgentDefinition and the SQLAlchemy AgentModel.
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import AgentModel
from backend.agent_service.agent_registry import (
    AgentDefinition, AgentStatus, ModelConfig, RAGConfig,
    MemoryConfig, DBConfig, ToolBinding, AgentEndpoint, AccessControl,
)

logger = logging.getLogger(__name__)


def _definition_to_row(agent: AgentDefinition) -> dict:
    """Convert a Pydantic AgentDefinition to a dict for DB insertion."""
    return {
        "id": agent.agent_id,
        "name": agent.name,
        "description": agent.description,
        "version": agent.version,
        "status": agent.status.value,
        "tags": agent.tags,
        "model_config_json": agent.model_config_.model_dump(mode="json"),
        "context": agent.context,
        "prompt_template_id": agent.prompt_template_id,
        "rag_config_json": agent.rag_config.model_dump(mode="json"),
        "memory_config_json": agent.memory_config.model_dump(mode="json"),
        "db_config_json": agent.db_config.model_dump(mode="json"),
        "tools_json": [t.model_dump(mode="json") for t in agent.tools],
        "endpoint_json": agent.endpoint.model_dump(mode="json"),
        "access_control_json": agent.access_control.model_dump(mode="json"),
        "graph_manifest_id": agent.graph_manifest_id,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
        "created_by": agent.created_by,
        "metadata_json": agent.metadata,
    }


def _row_to_definition(row: AgentModel) -> AgentDefinition:
    """Convert a SQLAlchemy AgentModel row back to a Pydantic AgentDefinition."""
    return AgentDefinition(
        agent_id=row.id,
        name=row.name,
        description=row.description,
        version=row.version,
        status=AgentStatus(row.status),
        tags=row.tags or [],
        model_config=ModelConfig(**(row.model_config_json or {})),
        context=row.context or "",
        prompt_template_id=row.prompt_template_id,
        rag_config=RAGConfig(**(row.rag_config_json or {})),
        memory_config=MemoryConfig(**(row.memory_config_json or {})),
        db_config=DBConfig(**(row.db_config_json or {})),
        tools=[ToolBinding(**t) for t in (row.tools_json or [])],
        endpoint=AgentEndpoint(**(row.endpoint_json or {})),
        access_control=AccessControl(**(row.access_control_json or {})),
        graph_manifest_id=row.graph_manifest_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        metadata=row.metadata_json or {},
    )


class AgentRepository:
    """Async CRUD operations for agents against PostgreSQL."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, agent: AgentDefinition, credential_id: Optional[str] = None) -> AgentDefinition:
        """Insert a new agent into the database."""
        now = datetime.utcnow()
        agent.created_at = now
        agent.updated_at = now
        agent.endpoint.path_prefix = f"/agents/{agent.agent_id}"

        data = _definition_to_row(agent)
        data["credential_id"] = credential_id
        row = AgentModel(**data)
        self._session.add(row)
        await self._session.flush()
        logger.info(f"Created agent {agent.agent_id} ({agent.name})")
        return agent

    async def get(self, agent_id: str) -> Optional[AgentDefinition]:
        """Fetch a single agent by ID."""
        result = await self._session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return _row_to_definition(row)

    async def get_with_credential_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Fetch agent + its credential_id (for LLM invocation)."""
        result = await self._session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "agent": _row_to_definition(row),
            "credential_id": row.credential_id,
        }

    async def list_all(
        self,
        status: Optional[AgentStatus] = None,
        owner_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AgentDefinition]:
        """List agents with optional filters."""
        stmt = select(AgentModel).order_by(AgentModel.updated_at.desc())
        if status:
            stmt = stmt.where(AgentModel.status == status.value)
        if owner_id:
            stmt = stmt.where(
                AgentModel.access_control_json["owner_id"].astext == owner_id
            )
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [_row_to_definition(r) for r in rows]

    async def update(
        self, agent_id: str, updates: Dict[str, Any], credential_id: Optional[str] = None,
    ) -> Optional[AgentDefinition]:
        """Partial update of an agent. Bumps version."""
        result = await self._session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None

        # Convert back to definition, apply updates, convert to row data
        agent = _row_to_definition(row)
        for k, v in updates.items():
            if hasattr(agent, k) and k not in ("agent_id", "created_at"):
                setattr(agent, k, v)
        agent.version += 1
        agent.updated_at = datetime.utcnow()

        data = _definition_to_row(agent)
        for k, v in data.items():
            setattr(row, k, v)
        if credential_id is not None:
            row.credential_id = credential_id
        await self._session.flush()
        logger.info(f"Updated agent {agent_id} to v{agent.version}")
        return agent

    async def delete(self, agent_id: str) -> bool:
        """Delete an agent by ID."""
        result = await self._session.execute(
            delete(AgentModel).where(AgentModel.id == agent_id)
        )
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted agent {agent_id}")
        return deleted

    async def count(self, status: Optional[AgentStatus] = None) -> int:
        """Count agents, optionally filtered by status."""
        stmt = select(func.count(AgentModel.id))
        if status:
            stmt = stmt.where(AgentModel.status == status.value)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_stats(self) -> Dict[str, Any]:
        """Aggregate stats for the agent table."""
        total = await self.count()
        by_status = {}
        for s in AgentStatus:
            by_status[s.value] = await self.count(s)
        return {"total": total, "by_status": by_status}
