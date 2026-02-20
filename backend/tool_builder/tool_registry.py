"""
Tool Builder — Create, configure, and manage custom tools.
Three tool types:
  1. Code Tool      — Run JavaScript or Python code
  2. REST API Tool  — Make HTTP requests (Postman-style)
  3. MCP Connector  — Call Model Context Protocol servers
Tools are bound to agents via the Agent Registry.
"""

import uuid
import copy
import time
import json
import subprocess
import tempfile
import os
import traceback
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS & SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class ToolType(str, Enum):
    CODE = "code"            # JavaScript or Python code
    REST_API = "rest_api"    # HTTP request (Postman-style)
    MCP = "mcp"              # Model Context Protocol connector


class CodeLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"


class BodyType(str, Enum):
    NONE = "none"
    JSON = "json"
    FORM = "form"
    RAW = "raw"


class ToolParameter(BaseModel):
    """Input/output parameter definition for a tool."""
    name: str
    param_type: str = "string"  # string, integer, float, boolean, object, array
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    enum_values: List[str] = Field(default_factory=list)


# ── Type-specific configs ─────────────────────────────────────────────────

class CodeToolConfig(BaseModel):
    """Configuration for Code tools (Python or JavaScript)."""
    language: CodeLanguage = CodeLanguage.PYTHON
    code: str = ""
    # For Python: function must be named `run(params: dict) -> dict`
    # For JS: must export default function run(params) { return {...} }
    timeout_seconds: int = 30
    packages: List[str] = Field(default_factory=list)  # pip/npm packages


class KeyValuePair(BaseModel):
    """A key-value pair with optional enable toggle."""
    key: str = ""
    value: str = ""
    description: str = ""
    enabled: bool = True


class RestApiToolConfig(BaseModel):
    """Configuration for REST API tools (Postman-style)."""
    method: HttpMethod = HttpMethod.GET
    url: str = ""
    # Headers, Query Params, Body — Postman-style
    headers: List[KeyValuePair] = Field(default_factory=list)
    query_params: List[KeyValuePair] = Field(default_factory=list)
    # Auth
    auth_type: AuthType = AuthType.NONE
    auth_config: Dict[str, str] = Field(default_factory=dict)
    # Body
    body_type: BodyType = BodyType.NONE
    body_raw: str = ""  # raw JSON/text body
    body_form: List[KeyValuePair] = Field(default_factory=list)
    # Settings
    timeout_seconds: int = 30
    follow_redirects: bool = True
    verify_ssl: bool = True


class McpToolConfig(BaseModel):
    """Configuration for MCP Connector tools."""
    server_url: str = ""  # MCP server endpoint
    tool_name: str = ""   # specific tool name on the MCP server
    # Auth for MCP server
    auth_type: AuthType = AuthType.NONE
    auth_config: Dict[str, str] = Field(default_factory=dict)
    # Headers to send to MCP server
    headers: List[KeyValuePair] = Field(default_factory=list)
    timeout_seconds: int = 30
    # Discovered schema (populated after connecting)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    description_from_server: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITION
# ══════════════════════════════════════════════════════════════════════════════

class ToolDefinition(BaseModel):
    """
    Complete tool definition — a reusable, configurable tool unit.
    Supports 3 types: Code, REST API, MCP.
    """
    tool_id: str = Field(default_factory=lambda: f"tool-{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    tool_type: ToolType = ToolType.REST_API
    version: int = 1
    status: str = "active"  # draft, active, deprecated, archived
    tags: List[str] = Field(default_factory=list)

    # Parameters (for agent binding / schema exposure)
    input_params: List[ToolParameter] = Field(default_factory=list)
    output_params: List[ToolParameter] = Field(default_factory=list)

    # Type-specific config (only one populated based on tool_type)
    code_config: Optional[CodeToolConfig] = None
    rest_api_config: Optional[RestApiToolConfig] = None
    mcp_config: Optional[McpToolConfig] = None

    # Access control
    owner_id: str = ""
    is_public: bool = True
    allowed_agent_ids: List[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    execution_count: int = 0
    last_execution: Optional[datetime] = None
    avg_latency_ms: float = 0.0
    success_rate: float = 100.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    """Result of executing a tool."""
    success: bool = False
    tool_id: str = ""
    tool_name: str = ""
    tool_type: str = ""
    output: Any = None
    status_code: Optional[int] = None  # HTTP status for REST API
    headers: Optional[Dict[str, str]] = None  # response headers for REST API
    latency_ms: float = 0.0
    error: Optional[str] = None
    logs: List[str] = Field(default_factory=list)  # stdout/stderr for code tools


# ══════════════════════════════════════════════════════════════════════════════
# EXECUTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ToolExecutor:
    """Executes tools based on their type."""

    @staticmethod
    def execute_code(config: CodeToolConfig, inputs: Dict[str, Any]) -> ToolExecutionResult:
        """Execute a Code tool (Python or JavaScript)."""
        if not config.code.strip():
            return ToolExecutionResult(success=False, error="No code provided")

        if config.language == CodeLanguage.PYTHON:
            return ToolExecutor._run_python(config, inputs)
        elif config.language == CodeLanguage.JAVASCRIPT:
            return ToolExecutor._run_javascript(config, inputs)
        else:
            return ToolExecutionResult(success=False, error=f"Unsupported language: {config.language}")

    @staticmethod
    def _run_python(config: CodeToolConfig, inputs: Dict[str, Any]) -> ToolExecutionResult:
        """Run Python code in a subprocess."""
        wrapper = f"""
import json, sys
params = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {{}}

{config.code}

if 'run' in dir():
    _result = run(params)
    print("__TOOL_OUTPUT__" + json.dumps(_result if _result is not None else {{}}, default=str))
else:
    print("__TOOL_OUTPUT__" + json.dumps({{"error": "No run(params) function defined"}}))
"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(wrapper)
                f.flush()
                result = subprocess.run(
                    ['python3', f.name, json.dumps(inputs or {})],
                    capture_output=True, text=True,
                    timeout=config.timeout_seconds,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
            os.unlink(f.name)

            logs = []
            output = None
            for line in (result.stdout or "").split("\n"):
                if line.startswith("__TOOL_OUTPUT__"):
                    try:
                        output = json.loads(line[len("__TOOL_OUTPUT__"):])
                    except json.JSONDecodeError:
                        output = line[len("__TOOL_OUTPUT__"):]
                elif line.strip():
                    logs.append(line)

            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                return ToolExecutionResult(
                    success=False, error=stderr or f"Exit code {result.returncode}",
                    logs=logs, output=output,
                )
            return ToolExecutionResult(success=True, output=output, logs=logs)
        except subprocess.TimeoutExpired:
            return ToolExecutionResult(success=False, error=f"Timeout after {config.timeout_seconds}s")
        except Exception as e:
            return ToolExecutionResult(success=False, error=str(e))

    @staticmethod
    def _run_javascript(config: CodeToolConfig, inputs: Dict[str, Any]) -> ToolExecutionResult:
        """Run JavaScript code via Node.js subprocess."""
        wrapper = f"""
const params = JSON.parse(process.argv[2] || '{{}}');

{config.code}

if (typeof run === 'function') {{
    Promise.resolve(run(params)).then(r => {{
        console.log("__TOOL_OUTPUT__" + JSON.stringify(r || {{}}));
    }}).catch(e => {{
        console.log("__TOOL_OUTPUT__" + JSON.stringify({{error: e.message}}));
    }});
}} else {{
    console.log("__TOOL_OUTPUT__" + JSON.stringify({{error: "No run(params) function defined"}}));
}}
"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(wrapper)
                f.flush()
                result = subprocess.run(
                    ['node', f.name, json.dumps(inputs or {})],
                    capture_output=True, text=True,
                    timeout=config.timeout_seconds,
                )
            os.unlink(f.name)

            logs = []
            output = None
            for line in (result.stdout or "").split("\n"):
                if line.startswith("__TOOL_OUTPUT__"):
                    try:
                        output = json.loads(line[len("__TOOL_OUTPUT__"):])
                    except json.JSONDecodeError:
                        output = line[len("__TOOL_OUTPUT__"):]
                elif line.strip():
                    logs.append(line)

            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                return ToolExecutionResult(
                    success=False, error=stderr or f"Exit code {result.returncode}",
                    logs=logs, output=output,
                )
            return ToolExecutionResult(success=True, output=output, logs=logs)
        except subprocess.TimeoutExpired:
            return ToolExecutionResult(success=False, error=f"Timeout after {config.timeout_seconds}s")
        except FileNotFoundError:
            return ToolExecutionResult(success=False, error="Node.js not found. Install Node.js to run JavaScript tools.")
        except Exception as e:
            return ToolExecutionResult(success=False, error=str(e))

    @staticmethod
    def execute_rest_api(config: RestApiToolConfig, inputs: Dict[str, Any]) -> ToolExecutionResult:
        """Execute a REST API tool (real HTTP request)."""
        import httpx

        if not config.url.strip():
            return ToolExecutionResult(success=False, error="No URL provided")

        # Build URL with variable interpolation
        url = config.url
        for k, v in (inputs or {}).items():
            url = url.replace(f"{{{{{k}}}}}", str(v))

        # Build headers
        headers = {}
        for h in config.headers:
            if h.enabled and h.key:
                val = h.value
                for k, v in (inputs or {}).items():
                    val = val.replace(f"{{{{{k}}}}}", str(v))
                headers[h.key] = val

        # Auth
        if config.auth_type == AuthType.BEARER:
            token = config.auth_config.get("token", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif config.auth_type == AuthType.API_KEY:
            key_name = config.auth_config.get("key_name", "X-API-Key")
            key_value = config.auth_config.get("key_value", "")
            key_in = config.auth_config.get("key_in", "header")  # header or query
            if key_in == "header":
                headers[key_name] = key_value
        elif config.auth_type == AuthType.BASIC:
            import base64
            username = config.auth_config.get("username", "")
            password = config.auth_config.get("password", "")
            cred = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {cred}"

        # Query params
        params = {}
        for qp in config.query_params:
            if qp.enabled and qp.key:
                val = qp.value
                for k, v in (inputs or {}).items():
                    val = val.replace(f"{{{{{k}}}}}", str(v))
                params[qp.key] = val

        # Body
        body_content = None
        if config.body_type == BodyType.JSON and config.body_raw:
            raw = config.body_raw
            for k, v in (inputs or {}).items():
                raw = raw.replace(f"{{{{{k}}}}}", json.dumps(v) if isinstance(v, (dict, list)) else str(v))
            try:
                body_content = json.loads(raw)
            except json.JSONDecodeError:
                body_content = raw
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
        elif config.body_type == BodyType.FORM:
            body_content = {f.key: f.value for f in config.body_form if f.enabled and f.key}
        elif config.body_type == BodyType.RAW and config.body_raw:
            body_content = config.body_raw

        try:
            with httpx.Client(
                timeout=config.timeout_seconds,
                follow_redirects=config.follow_redirects,
                verify=config.verify_ssl,
            ) as client:
                if config.body_type == BodyType.JSON:
                    resp = client.request(config.method.value, url, headers=headers, params=params, json=body_content)
                elif config.body_type == BodyType.FORM:
                    resp = client.request(config.method.value, url, headers=headers, params=params, data=body_content)
                elif config.body_type == BodyType.RAW:
                    resp = client.request(config.method.value, url, headers=headers, params=params, content=body_content)
                else:
                    resp = client.request(config.method.value, url, headers=headers, params=params)

            # Parse response
            try:
                output = resp.json()
            except Exception:
                output = resp.text

            resp_headers = dict(resp.headers)
            is_success = 200 <= resp.status_code < 400

            return ToolExecutionResult(
                success=is_success,
                output=output,
                status_code=resp.status_code,
                headers=resp_headers,
                error=None if is_success else f"HTTP {resp.status_code}",
            )
        except httpx.TimeoutException:
            return ToolExecutionResult(success=False, error=f"Request timeout after {config.timeout_seconds}s")
        except httpx.ConnectError as e:
            return ToolExecutionResult(success=False, error=f"Connection error: {e}")
        except Exception as e:
            return ToolExecutionResult(success=False, error=str(e))

    @staticmethod
    def execute_mcp(config: McpToolConfig, inputs: Dict[str, Any]) -> ToolExecutionResult:
        """Execute an MCP tool call via HTTP to the MCP server."""
        import httpx

        if not config.server_url.strip():
            return ToolExecutionResult(success=False, error="No MCP server URL configured")
        if not config.tool_name.strip():
            return ToolExecutionResult(success=False, error="No MCP tool name specified")

        # Build MCP JSON-RPC request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": config.tool_name,
                "arguments": inputs or {},
            },
        }

        headers = {"Content-Type": "application/json"}
        for h in config.headers:
            if h.enabled and h.key:
                headers[h.key] = h.value

        # Auth
        if config.auth_type == AuthType.BEARER:
            token = config.auth_config.get("token", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif config.auth_type == AuthType.API_KEY:
            key_name = config.auth_config.get("key_name", "X-API-Key")
            key_value = config.auth_config.get("key_value", "")
            headers[key_name] = key_value

        try:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                resp = client.post(config.server_url, json=mcp_request, headers=headers)

            resp_data = resp.json()

            if "error" in resp_data:
                err = resp_data["error"]
                return ToolExecutionResult(
                    success=False,
                    status_code=resp.status_code,
                    error=err.get("message", str(err)) if isinstance(err, dict) else str(err),
                    output=resp_data,
                )

            result = resp_data.get("result", {})
            # MCP result has "content" array
            content = result.get("content", [])
            output = content[0].get("text", content[0]) if content else result

            return ToolExecutionResult(
                success=True,
                output=output,
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
        except httpx.TimeoutException:
            return ToolExecutionResult(success=False, error=f"MCP request timeout after {config.timeout_seconds}s")
        except httpx.ConnectError as e:
            return ToolExecutionResult(success=False, error=f"Cannot connect to MCP server: {e}")
        except Exception as e:
            return ToolExecutionResult(success=False, error=str(e))

    @staticmethod
    def discover_mcp_tools(server_url: str, headers: Dict[str, str] = None, timeout: int = 15) -> ToolExecutionResult:
        """List available tools on an MCP server via tools/list."""
        import httpx
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {},
        }
        hdrs = {"Content-Type": "application/json"}
        if headers:
            hdrs.update(headers)
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(server_url, json=mcp_request, headers=hdrs)
            data = resp.json()
            tools_list = data.get("result", {}).get("tools", [])
            return ToolExecutionResult(success=True, output=tools_list, status_code=resp.status_code)
        except Exception as e:
            return ToolExecutionResult(success=False, error=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

def _tool_def_from_row(row) -> ToolDefinition:
    """Convert a ToolModel ORM row to a ToolDefinition Pydantic model."""
    config = row.config_json if isinstance(row.config_json, dict) else {}
    endpoints = row.endpoints_json if isinstance(row.endpoints_json, list) else []
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    tags = row.tags if isinstance(row.tags, list) else []
    return ToolDefinition(
        tool_id=row.id, name=row.name, description=row.description or "",
        tool_type=ToolType(row.tool_type) if row.tool_type else ToolType.REST_API,
        version=1, status=row.status or "active", tags=tags,
        is_public=row.is_public if row.is_public is not None else True,
        owner_id=row.created_by or "",
        created_at=row.created_at or datetime.utcnow(),
        updated_at=row.updated_at or datetime.utcnow(),
        metadata=meta,
    )


class ToolRegistry:
    """
    Central registry for all tools. Provides CRUD, versioning,
    execution, and search. PostgreSQL-backed with in-memory fallback.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._versions: Dict[str, List[ToolDefinition]] = {}
        self._execution_log: List[Dict[str, Any]] = []
        self._executor = ToolExecutor()
        self._db_available = False

    def _sf(self):
        from backend.db.sync_bridge import get_session_factory
        return get_session_factory()

    # ── Async DB helpers ──────────────────────────────────────────

    async def _db_create(self, tool: ToolDefinition) -> Optional[ToolDefinition]:
        factory = self._sf()
        if not factory:
            return None
        from backend.db.models import ToolModel
        async with factory() as session:
            row = ToolModel(
                id=tool.tool_id, name=tool.name, description=tool.description,
                tool_type=tool.tool_type.value, category=tool.tags[0] if tool.tags else "",
                status=tool.status, tags=tool.tags,
                config_json=tool.metadata or {},
                is_public=tool.is_public,
                is_platform_tool=False,
                created_by=tool.owner_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return tool

    async def _db_get(self, tool_id) -> Optional[ToolDefinition]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import ToolModel
        async with factory() as session:
            row = (await session.execute(
                select(ToolModel).where(ToolModel.id == tool_id)
            )).scalar_one_or_none()
            return _tool_def_from_row(row) if row else None

    async def _db_update(self, tool_id, updates) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import ToolModel
        async with factory() as session:
            row = (await session.execute(
                select(ToolModel).where(ToolModel.id == tool_id)
            )).scalar_one_or_none()
            if not row:
                return False
            for k, v in updates.items():
                if k == "tags" and hasattr(row, "tags"):
                    row.tags = v
                elif k == "status" and hasattr(row, "status"):
                    row.status = v
                elif k == "name" and hasattr(row, "name"):
                    row.name = v
                elif k == "description" and hasattr(row, "description"):
                    row.description = v
            row.updated_at = datetime.utcnow()
            await session.commit()
            return True

    async def _db_delete(self, tool_id) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import ToolModel
        async with factory() as session:
            row = (await session.execute(
                select(ToolModel).where(ToolModel.id == tool_id)
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def _db_list(self, tool_type=None, status=None) -> List[ToolDefinition]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import ToolModel
        async with factory() as session:
            q = select(ToolModel)
            if tool_type:
                q = q.where(ToolModel.tool_type == tool_type.value)
            if status:
                q = q.where(ToolModel.status == status)
            q = q.order_by(ToolModel.updated_at.desc())
            rows = (await session.execute(q)).scalars().all()
            return [_tool_def_from_row(r) for r in rows]

    async def _db_search(self, query) -> List[ToolDefinition]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select, or_
        from backend.db.models import ToolModel
        async with factory() as session:
            q = select(ToolModel).where(or_(
                ToolModel.name.ilike(f"%{query}%"),
                ToolModel.description.ilike(f"%{query}%"),
            ))
            rows = (await session.execute(q)).scalars().all()
            return [_tool_def_from_row(r) for r in rows]

    async def _db_stats(self) -> Dict[str, Any]:
        factory = self._sf()
        if not factory:
            return {}
        from sqlalchemy import select, func
        from backend.db.models import ToolModel
        async with factory() as session:
            total = (await session.execute(select(func.count(ToolModel.id)))).scalar() or 0
            active = (await session.execute(
                select(func.count(ToolModel.id)).where(ToolModel.status == "active")
            )).scalar() or 0
            return {"total_tools": total, "active_tools": active, "persistence": "postgresql"}

    # ── CRUD ──────────────────────────────────────────────────────

    def create(self, tool: ToolDefinition) -> ToolDefinition:
        tool.created_at = datetime.utcnow()
        tool.updated_at = datetime.utcnow()
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_create(tool))
            except Exception:
                pass
        self._tools[tool.tool_id] = tool
        self._versions[tool.tool_id] = [copy.deepcopy(tool)]
        return tool

    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._tools.get(tool_id)

    def update(self, tool_id: str, updates: Dict[str, Any]) -> Optional[ToolDefinition]:
        tool = self._tools.get(tool_id)
        if not tool:
            return None
        for k, v in updates.items():
            if hasattr(tool, k) and k not in ("tool_id", "created_at"):
                setattr(tool, k, v)
        tool.version += 1
        tool.updated_at = datetime.utcnow()
        self._versions.setdefault(tool_id, []).append(copy.deepcopy(tool))
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_update(tool_id, updates))
            except Exception:
                pass
        return tool

    def delete(self, tool_id: str) -> bool:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_delete(tool_id))
            except Exception:
                pass
        removed = self._tools.pop(tool_id, None)
        self._versions.pop(tool_id, None)
        return removed is not None

    def list_all(self, tool_type: Optional[ToolType] = None, status: Optional[str] = None) -> List[ToolDefinition]:
        tools = list(self._tools.values())
        if tool_type:
            tools = [t for t in tools if t.tool_type == tool_type]
        if status:
            tools = [t for t in tools if t.status == status]
        return sorted(tools, key=lambda t: t.updated_at, reverse=True)

    def search(self, query: str) -> List[ToolDefinition]:
        q = query.lower()
        return [
            t for t in self._tools.values()
            if q in t.name.lower() or q in t.description.lower() or any(q in tag for tag in t.tags)
        ]

    def get_tools_for_agent(self, agent_id: str) -> List[ToolDefinition]:
        """Get all tools accessible to a specific agent."""
        return [
            t for t in self._tools.values()
            if t.is_public or agent_id in t.allowed_agent_ids
        ]

    # ── Execution ─────────────────────────────────────────────────

    def execute(
        self, tool_id: str, inputs: Dict[str, Any] = None,
        agent_id: Optional[str] = None,
    ) -> ToolExecutionResult:
        """Execute a tool with given inputs — real execution, not simulated."""
        tool = self._tools.get(tool_id)
        if not tool:
            return ToolExecutionResult(success=False, tool_id=tool_id, error="Tool not found")

        if tool.status not in ("active", "draft"):
            return ToolExecutionResult(
                success=False, tool_id=tool_id, tool_name=tool.name,
                error=f"Tool is not active (status: {tool.status})"
            )

        # Access check
        if not tool.is_public and agent_id and agent_id not in tool.allowed_agent_ids:
            return ToolExecutionResult(
                success=False, tool_id=tool_id, tool_name=tool.name,
                error=f"Agent '{agent_id}' not authorized to use tool '{tool.name}'"
            )

        start = time.time()

        # Dispatch to correct executor
        if tool.tool_type == ToolType.CODE and tool.code_config:
            result = ToolExecutor.execute_code(tool.code_config, inputs or {})
        elif tool.tool_type == ToolType.REST_API and tool.rest_api_config:
            result = ToolExecutor.execute_rest_api(tool.rest_api_config, inputs or {})
        elif tool.tool_type == ToolType.MCP and tool.mcp_config:
            result = ToolExecutor.execute_mcp(tool.mcp_config, inputs or {})
        else:
            result = ToolExecutionResult(success=False, error=f"Missing config for tool type {tool.tool_type.value}")

        latency = round((time.time() - start) * 1000, 1)
        result.tool_id = tool.tool_id
        result.tool_name = tool.name
        result.tool_type = tool.tool_type.value
        result.latency_ms = latency

        # Update tool stats
        tool.execution_count += 1
        tool.last_execution = datetime.utcnow()
        tool.avg_latency_ms = round(
            (tool.avg_latency_ms * (tool.execution_count - 1) + latency) / tool.execution_count, 1
        )
        total_runs = tool.execution_count
        prev_successes = round(tool.success_rate * (total_runs - 1) / 100)
        tool.success_rate = round((prev_successes + (1 if result.success else 0)) / total_runs * 100, 1)

        self._execution_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "tool_id": tool_id,
            "tool_name": tool.name,
            "tool_type": tool.tool_type.value,
            "agent_id": agent_id,
            "latency_ms": latency,
            "success": result.success,
            "error": result.error,
        })

        return result

    def get_execution_log(self, tool_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        log = self._execution_log
        if tool_id:
            log = [e for e in log if e.get("tool_id") == tool_id]
        return log[-limit:]

    # ── MCP Discovery ─────────────────────────────────────────────

    def discover_mcp(self, server_url: str, headers: Dict[str, str] = None) -> ToolExecutionResult:
        """List available tools on an MCP server."""
        return ToolExecutor.discover_mcp_tools(server_url, headers)

    # ── Cloning ───────────────────────────────────────────────────

    def clone(self, tool_id: str, new_name: str) -> Optional[ToolDefinition]:
        original = self._tools.get(tool_id)
        if not original:
            return None
        cloned = copy.deepcopy(original)
        cloned.tool_id = f"tool-{uuid.uuid4().hex[:8]}"
        cloned.name = new_name
        cloned.version = 1
        cloned.status = "draft"
        cloned.execution_count = 0
        cloned.metadata["cloned_from"] = tool_id
        return self.create(cloned)

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        tools = list(self._tools.values())
        by_type: Dict[str, int] = {}
        for t in tools:
            by_type[t.tool_type.value] = by_type.get(t.tool_type.value, 0) + 1
        return {
            "total_tools": len(tools),
            "by_type": by_type,
            "active_tools": sum(1 for t in tools if t.status == "active"),
            "total_executions": sum(t.execution_count for t in tools),
        }
