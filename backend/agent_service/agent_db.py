"""
Agent DB Connector — Per-agent database access for structured (Snowflake/Postgres)
and unstructured (Pinecone) data sources. Manages connection pools, query execution,
and access control per agent.
"""

import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class DBType(str, Enum):
    POSTGRES = "postgres"
    SNOWFLAKE = "snowflake"
    PINECONE = "pinecone"
    CHROMADB = "chromadb"


class DBConnection(BaseModel):
    """A registered database connection."""
    connection_id: str = Field(default_factory=lambda: f"db-{uuid.uuid4().hex[:8]}")
    name: str
    db_type: DBType
    host: str = ""
    port: int = 5432
    database: str = ""
    schema_name: str = "public"
    username: str = ""
    # password stored as reference to secret manager, never in plain text
    password_secret_ref: str = ""
    extra_params: Dict[str, str] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryResult(BaseModel):
    """Result of a database query."""
    success: bool = False
    connection_id: str = ""
    query: str = ""
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    error: Optional[str] = None


class AgentDBConnector:
    """
    Manages database connections and query execution for agents.
    Phase 1: in-memory mock. Phase 2: real connection pools.
    """

    def __init__(self):
        self._connections: Dict[str, DBConnection] = {}
        self._agent_bindings: Dict[str, List[str]] = {}  # agent_id -> [connection_ids]
        self._query_log: List[Dict[str, Any]] = []

    # ── Connection Management ─────────────────────────────────────

    def register_connection(self, conn: DBConnection) -> DBConnection:
        self._connections[conn.connection_id] = conn
        return conn

    def get_connection(self, connection_id: str) -> Optional[DBConnection]:
        return self._connections.get(connection_id)

    def list_connections(self, db_type: Optional[DBType] = None) -> List[DBConnection]:
        conns = list(self._connections.values())
        if db_type:
            conns = [c for c in conns if c.db_type == db_type]
        return conns

    def delete_connection(self, connection_id: str) -> bool:
        removed = self._connections.pop(connection_id, None)
        if removed:
            for bindings in self._agent_bindings.values():
                if connection_id in bindings:
                    bindings.remove(connection_id)
        return removed is not None

    def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """Test a database connection (placeholder — real impl uses actual driver)."""
        conn = self._connections.get(connection_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}
        # Phase 2: actual connection test
        return {
            "success": True,
            "connection_id": connection_id,
            "db_type": conn.db_type.value,
            "message": f"Connection '{conn.name}' is reachable (simulated)",
        }

    # ── Agent Bindings ────────────────────────────────────────────

    def bind_to_agent(self, agent_id: str, connection_id: str) -> bool:
        if connection_id not in self._connections:
            return False
        if agent_id not in self._agent_bindings:
            self._agent_bindings[agent_id] = []
        if connection_id not in self._agent_bindings[agent_id]:
            self._agent_bindings[agent_id].append(connection_id)
        return True

    def unbind_from_agent(self, agent_id: str, connection_id: str) -> bool:
        bindings = self._agent_bindings.get(agent_id, [])
        if connection_id in bindings:
            bindings.remove(connection_id)
            return True
        return False

    def get_agent_connections(self, agent_id: str) -> List[DBConnection]:
        conn_ids = self._agent_bindings.get(agent_id, [])
        return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    # ── Query Execution ───────────────────────────────────────────

    def execute_query(
        self, connection_id: str, query: str,
        parameters: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        read_only: bool = True,
    ) -> QueryResult:
        """
        Execute a query against a database connection.
        Phase 1: returns mock data. Phase 2: real execution via asyncpg/snowflake-connector.
        """
        conn = self._connections.get(connection_id)
        if not conn:
            return QueryResult(success=False, error="Connection not found")

        if not conn.is_active:
            return QueryResult(success=False, error="Connection is inactive")

        # Check agent binding
        if agent_id:
            agent_conns = self._agent_bindings.get(agent_id, [])
            if connection_id not in agent_conns:
                return QueryResult(success=False, error=f"Agent '{agent_id}' not bound to connection '{connection_id}'")

        # Read-only enforcement
        if read_only:
            q_upper = query.strip().upper()
            if any(q_upper.startswith(kw) for kw in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"]):
                return QueryResult(success=False, query=query, error="Write operations not allowed (read_only=True)")

        # Log the query
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "connection_id": connection_id,
            "agent_id": agent_id,
            "query": query[:200],
            "read_only": read_only,
        }
        self._query_log.append(log_entry)

        # Phase 1: mock result
        result = QueryResult(
            success=True,
            connection_id=connection_id,
            query=query,
            columns=["id", "name", "value"],
            rows=[
                {"id": 1, "name": "sample_row_1", "value": "mock_data"},
                {"id": 2, "name": "sample_row_2", "value": "mock_data"},
            ],
            row_count=2,
            execution_time_ms=12.5,
        )
        return result

    def get_query_log(self, agent_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        log = self._query_log
        if agent_id:
            log = [e for e in log if e.get("agent_id") == agent_id]
        return log[-limit:]

    # ── Schema Discovery ──────────────────────────────────────────

    def get_tables(self, connection_id: str) -> List[Dict[str, str]]:
        """List tables in a connection (mock for Phase 1)."""
        conn = self._connections.get(connection_id)
        if not conn:
            return []
        # Phase 2: real schema introspection
        return [
            {"table_name": "suppliers", "schema": conn.schema_name, "type": "TABLE"},
            {"table_name": "purchase_orders", "schema": conn.schema_name, "type": "TABLE"},
            {"table_name": "invoices", "schema": conn.schema_name, "type": "TABLE"},
            {"table_name": "contracts", "schema": conn.schema_name, "type": "TABLE"},
        ]

    def get_columns(self, connection_id: str, table_name: str) -> List[Dict[str, str]]:
        """List columns in a table (mock for Phase 1)."""
        return [
            {"column_name": "id", "data_type": "integer", "nullable": "NO"},
            {"column_name": "name", "data_type": "varchar", "nullable": "NO"},
            {"column_name": "created_at", "data_type": "timestamp", "nullable": "YES"},
            {"column_name": "status", "data_type": "varchar", "nullable": "YES"},
        ]

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        conns = list(self._connections.values())
        by_type: Dict[str, int] = {}
        for c in conns:
            by_type[c.db_type.value] = by_type.get(c.db_type.value, 0) + 1
        return {
            "total_connections": len(conns),
            "active_connections": sum(1 for c in conns if c.is_active),
            "by_type": by_type,
            "total_queries": len(self._query_log),
            "agent_bindings": len(self._agent_bindings),
        }
