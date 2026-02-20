"""
JAI Agent OS — Workato Connector Registry
Manages enterprise system connectors via Workato integration platform.
Provides a unified interface for agents to connect to SAP, Salesforce,
ServiceNow, Oracle, NetSuite, Slack, Teams, Jira, DocuSign, SharePoint, etc.
"""

import uuid
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from backend.seed.seed_templates import WORKATO_CONNECTORS


class ConnectorStatus(str, Enum):
    AVAILABLE = "available"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConnectorConnection(BaseModel):
    """A configured connection instance for a Workato connector."""
    connection_id: str = Field(default_factory=lambda: f"conn-{uuid.uuid4().hex[:8]}")
    connector_id: str
    name: str
    tenant_id: str = "tenant-default"
    status: ConnectorStatus = ConnectorStatus.DISCONNECTED
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    workato_connection_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_tested_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WorkatoRecipe(BaseModel):
    """A Workato recipe (automation) linking a connector to an agent action."""
    recipe_id: str = Field(default_factory=lambda: f"recipe-{uuid.uuid4().hex[:8]}")
    name: str
    connector_id: str
    connection_id: str
    trigger_event: Optional[str] = None
    action_name: Optional[str] = None
    agent_id: Optional[str] = None
    is_active: bool = False
    workato_recipe_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkatoConnectorRegistry:
    """
    Registry for Workato enterprise connectors.
    Manages connector catalog, connections, and recipe automation.
    """

    def __init__(self, workato_base_url: str = "", workato_api_token: str = ""):
        self.workato_base_url = workato_base_url
        self.workato_api_token = workato_api_token
        # Connector catalog (from seed templates)
        self._connectors: Dict[str, dict] = {c["connector_id"]: c for c in WORKATO_CONNECTORS}
        # Active connections
        self._connections: Dict[str, ConnectorConnection] = {}
        # Recipes
        self._recipes: Dict[str, WorkatoRecipe] = {}

    # ── Connector Catalog ─────────────────────────────────────────────────

    def list_connectors(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        """List available connectors, optionally filtered by category or search."""
        results = list(self._connectors.values())
        if category:
            results = [c for c in results if c.get("category") == category]
        if search:
            q = search.lower()
            results = [c for c in results if q in c["name"].lower() or q in c.get("description", "").lower()
                       or any(q in t for t in c.get("tags", []))]
        return results

    def get_connector(self, connector_id: str) -> Optional[dict]:
        """Get a connector by ID."""
        return self._connectors.get(connector_id)

    def get_connector_categories(self) -> List[dict]:
        """Get unique connector categories with counts."""
        cats: Dict[str, int] = {}
        for c in self._connectors.values():
            cat = c.get("category", "other")
            cats[cat] = cats.get(cat, 0) + 1
        return [{"category": k, "count": v} for k, v in sorted(cats.items())]

    # ── Connections ───────────────────────────────────────────────────────

    def create_connection(
        self,
        connector_id: str,
        name: str,
        tenant_id: str = "tenant-default",
        auth_config: Optional[Dict[str, Any]] = None,
    ) -> ConnectorConnection:
        """Create a new connection for a connector."""
        if connector_id not in self._connectors:
            raise ValueError(f"Unknown connector: {connector_id}")

        conn = ConnectorConnection(
            connector_id=connector_id,
            name=name,
            tenant_id=tenant_id,
            auth_config=auth_config or {},
            status=ConnectorStatus.DISCONNECTED,
        )
        self._connections[conn.connection_id] = conn
        return conn

    def list_connections(self, tenant_id: Optional[str] = None) -> List[ConnectorConnection]:
        """List all connections, optionally filtered by tenant."""
        conns = list(self._connections.values())
        if tenant_id:
            conns = [c for c in conns if c.tenant_id == tenant_id]
        return conns

    def get_connection(self, connection_id: str) -> Optional[ConnectorConnection]:
        """Get a connection by ID."""
        return self._connections.get(connection_id)

    def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """Test a connection (simulated in Phase 1, real via Workato API in production)."""
        conn = self._connections.get(connection_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}

        connector = self._connectors.get(conn.connector_id)
        conn.last_tested_at = datetime.utcnow()

        # In production, this would call Workato API to test the connection
        # For now, simulate success if auth_config has required fields
        if conn.auth_config:
            conn.status = ConnectorStatus.CONNECTED
            conn.error_message = None
            return {
                "success": True,
                "connector": connector["name"] if connector else conn.connector_id,
                "latency_ms": 120,
                "message": "Connection successful",
            }
        else:
            conn.status = ConnectorStatus.ERROR
            conn.error_message = "Missing authentication configuration"
            return {
                "success": False,
                "error": "Missing authentication configuration. Please provide auth_config.",
            }

    def delete_connection(self, connection_id: str) -> bool:
        """Delete a connection."""
        if connection_id in self._connections:
            # Also delete associated recipes
            recipe_ids = [r.recipe_id for r in self._recipes.values() if r.connection_id == connection_id]
            for rid in recipe_ids:
                del self._recipes[rid]
            del self._connections[connection_id]
            return True
        return False

    # ── Recipes (Automations) ─────────────────────────────────────────────

    def create_recipe(
        self,
        name: str,
        connector_id: str,
        connection_id: str,
        trigger_event: Optional[str] = None,
        action_name: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> WorkatoRecipe:
        """Create a Workato recipe linking a connector action to an agent."""
        recipe = WorkatoRecipe(
            name=name,
            connector_id=connector_id,
            connection_id=connection_id,
            trigger_event=trigger_event,
            action_name=action_name,
            agent_id=agent_id,
        )
        self._recipes[recipe.recipe_id] = recipe
        return recipe

    def list_recipes(self, connector_id: Optional[str] = None) -> List[WorkatoRecipe]:
        """List recipes, optionally filtered by connector."""
        recipes = list(self._recipes.values())
        if connector_id:
            recipes = [r for r in recipes if r.connector_id == connector_id]
        return recipes

    def toggle_recipe(self, recipe_id: str) -> Optional[WorkatoRecipe]:
        """Activate or deactivate a recipe."""
        recipe = self._recipes.get(recipe_id)
        if recipe:
            recipe.is_active = not recipe.is_active
        return recipe

    # ── Execute Connector Action ──────────────────────────────────────────

    async def execute_action(
        self,
        connection_id: str,
        action_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a connector action via Workato API.
        In Phase 1, returns simulated response. In production, calls Workato.
        """
        conn = self._connections.get(connection_id)
        if not conn:
            return {"success": False, "error": "Connection not found"}

        connector = self._connectors.get(conn.connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}

        # Find the action definition
        action_def = None
        for a in connector.get("actions", []):
            if a["name"] == action_name:
                action_def = a
                break

        if not action_def:
            return {"success": False, "error": f"Action '{action_name}' not found in {connector['name']}"}

        # In production: call Workato API
        # For Phase 1: return simulated success
        return {
            "success": True,
            "connector": connector["name"],
            "action": action_name,
            "method": action_def["method"],
            "path": action_def["path"],
            "params": params,
            "response": {
                "status": 200,
                "message": f"Simulated {action_name} via {connector['name']}",
                "data": {"id": f"sim-{uuid.uuid4().hex[:8]}"},
            },
            "executed_at": datetime.utcnow().isoformat(),
        }

    # ── Stats ─────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get connector registry statistics."""
        return {
            "total_connectors": len(self._connectors),
            "categories": len(set(c.get("category", "") for c in self._connectors.values())),
            "total_connections": len(self._connections),
            "active_connections": sum(1 for c in self._connections.values() if c.status == ConnectorStatus.CONNECTED),
            "total_recipes": len(self._recipes),
            "active_recipes": sum(1 for r in self._recipes.values() if r.is_active),
            "by_category": {cat["category"]: cat["count"] for cat in self.get_connector_categories()},
        }
