import os
from langgraph.pregel.remote import RemoteGraph
from langgraph_supervisor import create_supervisor
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_core.runnables import RunnableConfig
from langchain.chat_models import init_chat_model
from langchain_google_vertexai import ChatVertexAI
import logging

logger = logging.getLogger(__name__)

# This system prompt is ALWAYS included at the bottom of the message.
UNEDITABLE_SYSTEM_PROMPT = """\nYou can invoke sub-agents by calling the available delegation tools.
When delegating, you MUST call the tool (as an actual tool/function call) and pass the user's request as the `user_query` argument.
Do NOT write tool calls like `delegate_to_<name>(user_query)` as plain text.
Otherwise, answer the user yourself.

The user will see all messages and tool calls produced in the conversation, 
along with all returned from the sub-agents. With this in mind, ensure you 
never repeat any information already presented to the user.
"""

DEFAULT_SUPERVISOR_PROMPT = """You are a supervisor AI overseeing a team of specialist agents. 
For each incoming user message, decide if it should be handled by one of your agents. 
"""


class AgentsConfig(BaseModel):
    deployment_url: str
    """The URL of the LangGraph deployment"""
    agent_id: str
    """The ID of the agent to use"""
    name: str
    """The name of the agent"""


class GraphConfigPydantic(BaseModel):
    agents: List[AgentsConfig] = Field(
        default=[],
        metadata={"x_oap_ui_config": {"type": "agents"}},
    )
    system_prompt: Optional[str] = Field(
        default=DEFAULT_SUPERVISOR_PROMPT,
        metadata={
            "x_oap_ui_config": {
                "type": "textarea",
                "placeholder": "Enter a system prompt...",
                "description": f"The system prompt to use in all generations. The following prompt will always be included at the end of the system prompt:\n---{UNEDITABLE_SYSTEM_PROMPT}---",
                "default": DEFAULT_SUPERVISOR_PROMPT,
            }
        },
    )
    supervisor_model: str = Field(
        default="openai:gpt-4.1",
        metadata={
            "x_oap_ui_config": {
                "type": "select",
                "placeholder": "Select the model to use for the supervisor.",
                "options": [
                    {
                        "label": "Claude Sonnet 4",
                        "value": "anthropic:claude-sonnet-4-0",
                    },
                    {
                        "label": "Claude 3.7 Sonnet",
                        "value": "anthropic:claude-3-7-sonnet-latest",
                    },
                    {
                        "label": "Claude 3.5 Sonnet",
                        "value": "anthropic:claude-3-5-sonnet-latest",
                    },
                    {
                        "label": "Claude 3.5 Haiku",
                        "value": "anthropic:claude-3-5-haiku-latest",
                    },
                    {
                        "label": "o4 mini",
                        "value": "openai:o4-mini",
                    },
                    {
                        "label": "o3",
                        "value": "openai:o3",
                    },
                    {
                        "label": "o3 mini",
                        "value": "openai:o3-mini",
                    },
                    {
                        "label": "GPT 4o",
                        "value": "openai:gpt-4o",
                    },
                    {
                        "label": "GPT 4o mini",
                        "value": "openai:gpt-4o-mini",
                    },
                    {
                        "label": "GPT 4.1",
                        "value": "openai:gpt-4.1",
                    },
                    {
                        "label": "GPT 4.1 mini",
                        "value": "openai:gpt-4.1-mini",
                    },
                    {"label": "Gemini 2.0 Flash (Vertex)", "value": "google_vertexai:gemini-2.0-flash-exp"},
                    {"label": "Gemini 1.5 Pro (Vertex)", "value": "google_vertexai:gemini-1.5-pro"},
                    {"label": "Gemini 1.5 Flash (Vertex)", "value": "google_vertexai:gemini-1.5-flash"},
                    {"label": "Gemini 1.5 Flash-8B (Vertex)", "value": "google_vertexai:gemini-1.5-flash-8b"},
                ]
            }
        },
    )


class OAPRemoteGraph(RemoteGraph):
    def __init__(self, graph_id: str, *, url: str = None, api_key: str = None, headers: dict = None, **kwargs):
        """Initialize OAPRemoteGraph with authentication headers support."""
        from langgraph_sdk import get_client
        
        # Create client with headers if provided
        if headers:
            client = get_client(url=url, headers=headers)
            super().__init__(graph_id, client=client, **kwargs)
        else:
            super().__init__(graph_id, url=url, api_key=api_key, **kwargs)
    
    def _sanitize_config(self, config: RunnableConfig) -> RunnableConfig:
        """Sanitize the config to remove non-serializable fields."""
        sanitized = super()._sanitize_config(config)

        # Filter out keys that are already defined in GraphConfigPydantic
        # to avoid the child graph inheriting config from the supervisor
        # (e.g. system_prompt)
        graph_config_fields = set(GraphConfigPydantic.model_fields.keys())

        if "configurable" in sanitized:
            sanitized["configurable"] = {
                k: v
                for k, v in sanitized["configurable"].items()
                if k not in graph_config_fields
            }

        if "metadata" in sanitized:
            sanitized["metadata"] = {
                k: v
                for k, v in sanitized["metadata"].items()
                if k not in graph_config_fields
            }

        # IMPORTANT: Do not forward supervisor thread IDs to child deployments.
        # Each deployment maintains its own thread store; reusing a thread_id from the
        # supervisor will cause 404s on the child server (e.g. /threads/{id}/runs/stream).
        # Remove any thread/run identifiers that could be interpreted by the SDK.
        for key in ("thread_id", "threadId", "run_id", "runId"):
            if key in sanitized:
                sanitized.pop(key, None)
            if "configurable" in sanitized and key in sanitized.get("configurable", {}):
                sanitized["configurable"].pop(key, None)
            if "metadata" in sanitized and key in sanitized.get("metadata", {}):
                sanitized["metadata"].pop(key, None)

        return sanitized


def make_child_graphs(cfg: GraphConfigPydantic):
    """
    Instantiate a list of RemoteGraph nodes based on the configuration.

    Args:
        cfg: The configuration for the graph

    Returns:
        A list of RemoteGraph instances
    """
    import re
    import json
    import urllib.request
    import urllib.error

    def sanitize_name(name):
        # Replace spaces with underscores
        sanitized = name.replace(" ", "_")
        # Remove any other disallowed characters (<, >, |, \, /)
        sanitized = re.sub(r"[<|\\/>]", "", sanitized)
        return sanitized

    # If no agents in config, return empty list
    if not cfg.agents:
        return []

    # Auth disabled — no headers needed
    headers = {}

    def convert_to_internal_url(deployment_url: str) -> str:
        """
        Convert external deployment URLs to internal service URLs for efficient
        service-to-service communication when running on the same host.
        
        This allows the UI to use external URLs while the supervisor uses internal URLs.
        """
        # Map of external URL patterns to internal service URLs
        url_mappings = {
            "/api/agents/tools": os.getenv("TOOLS_URL", "http://localhost:2024"),
            "/api/agents/supervisor": os.getenv("SUPERVISOR_URL", "http://localhost:2025"),
        }
        
        # Check if the deployment_url contains any of the patterns
        for pattern, internal_url in url_mappings.items():
            if pattern in deployment_url:
                return internal_url
        
        # If no pattern matches, return the original URL
        return deployment_url

    def create_remote_graph_wrapper(agent: AgentsConfig):
        internal_url = convert_to_internal_url(agent.deployment_url)
        
        # Debug: Log headers to verify they're being passed
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[SUPERVISOR AUTH DEBUG] Headers being used: {headers}")
        
        configured_assistant_id = (agent.agent_id or "").strip()
        if configured_assistant_id:
            # In local dev, deployments often use an in-memory store, so assistant IDs can
            # become stale after a restart. If we can verify the assistant doesn't exist,
            # fall back to creating/searching by graph_id.
            try:
                verify_headers = {"Content-Type": "application/json"}
                if headers:
                    verify_headers.update(headers)
                verify_req = urllib.request.Request(
                    url=internal_url.rstrip("/")
                    + f"/assistants/{configured_assistant_id}",
                    headers=verify_headers,
                    method="GET",
                )
                with urllib.request.urlopen(verify_req, timeout=10) as resp:
                    if 200 <= resp.status < 300:
                        # If the configured assistant exists but has no configurable
                        # settings, it's often a generic assistant (e.g. 'agent'/'emails')
                        # rather than the intended specialized one. In that case, fall
                        # through to discovery so we can select a better match.
                        try:
                            assistant_obj = json.loads(resp.read().decode("utf-8"))
                            cfg = (assistant_obj.get("config") or {}).get("configurable") or {}
                            if cfg:
                                return OAPRemoteGraph(
                                    configured_assistant_id,
                                    url=internal_url,
                                    name=sanitize_name(agent.name),
                                    api_key=None,
                                    headers=headers,
                                )
                        except Exception:
                            return OAPRemoteGraph(
                                configured_assistant_id,
                                url=internal_url,
                                name=sanitize_name(agent.name),
                                api_key=None,
                                headers=headers,
                            )
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    # If auth or other server errors prevent verification, trust the
                    # configured ID rather than silently switching.
                    return OAPRemoteGraph(
                        configured_assistant_id,
                        url=internal_url,
                        name=sanitize_name(agent.name),
                        api_key=None,
                        headers=headers,
                    )
                # If 404, fall through to the local-dev assistant discovery logic below.
            except Exception:
                # If verification fails unexpectedly, trust the configured ID.
                return OAPRemoteGraph(
                    configured_assistant_id,
                    url=internal_url,
                    name=sanitize_name(agent.name),
                    api_key=None,
                    headers=headers,
                )

        # In local dev, child deployments usually use an in-memory store.
        # That means assistants are lost on restart. /runs/stream requires a valid
        # assistant_id, so we proactively ensure an assistant exists.
        child_graph_id = "agent"
        child_assistant_id: str = child_graph_id

        try:
            search_headers = {"Content-Type": "application/json"}
            if headers:
                search_headers.update(headers)
            search_body = json.dumps({"graph_id": child_graph_id, "limit": 50, "offset": 0}).encode("utf-8")
            search_req = urllib.request.Request(
                url=internal_url.rstrip("/") + "/assistants/search",
                data=search_body,
                headers=search_headers,
                method="POST",
            )
            with urllib.request.urlopen(search_req, timeout=10) as resp:
                assistants = json.loads(resp.read().decode("utf-8"))
                if isinstance(assistants, list) and len(assistants) > 0:
                    desired_name = sanitize_name(agent.name)
                    desired_name_lc = desired_name.lower()
                    name_matches = [
                        a
                        for a in assistants
                        if (
                            (sanitize_name(a.get("name") or "").lower() == desired_name_lc)
                            or (desired_name_lc in sanitize_name(a.get("name") or "").lower())
                            or (sanitize_name(a.get("name") or "").lower() in desired_name_lc)
                        )
                    ]

                    # Prefer assistants that actually have a configured model/system prompt.
                    def has_config(a: dict) -> bool:
                        cfg = (a.get("config") or {}).get("configurable") or {}
                        return bool(cfg)

                    selected = next((a for a in name_matches if has_config(a)), None)
                    selected = selected or (name_matches[0] if name_matches else assistants[0])
                    child_assistant_id = selected["assistant_id"]
                else:
                    create_headers = {"Content-Type": "application/json"}
                    if headers:
                        create_headers.update(headers)
                    create_body = json.dumps(
                        {
                            "graph_id": child_graph_id,
                            "name": sanitize_name(agent.name),
                            "if_exists": "do_nothing",
                        }
                    ).encode("utf-8")
                    create_req = urllib.request.Request(
                        url=internal_url.rstrip("/") + "/assistants",
                        data=create_body,
                        headers=create_headers,
                        method="POST",
                    )
                    with urllib.request.urlopen(create_req, timeout=10) as resp2:
                        created = json.loads(resp2.read().decode("utf-8"))
                        child_assistant_id = created["assistant_id"]
        except Exception:
            # If we fail to query/create assistants (e.g. auth), fall back to graph id.
            child_assistant_id = child_graph_id

        return OAPRemoteGraph(
            child_assistant_id,
            url=internal_url,
            name=sanitize_name(agent.name),
            api_key=None,
            headers=headers,
        )

    return [create_remote_graph_wrapper(a) for a in cfg.agents]


def get_api_key_for_model(model_name: str, config: RunnableConfig):
    model_name = model_name.lower()
    
    # Vertex AI models don't use API keys - they use service account authentication
    if model_name.startswith("google_vertexai:"):
        return None  # Authentication handled via GOOGLE_APPLICATION_CREDENTIALS
    
    model_to_key = {
        "openai:": "OPENAI_API_KEY",
        "anthropic:": "ANTHROPIC_API_KEY", 
        "google_genai:": "GOOGLE_API_KEY",
        "google:": "GOOGLE_API_KEY"
    }
    key_name = next((key for prefix, key in model_to_key.items() 
                    if model_name.startswith(prefix)), None)
    if not key_name:
        return None
    api_keys = config.get("configurable", {}).get("apiKeys", {})
    if api_keys and api_keys.get(key_name) and len(api_keys[key_name]) > 0:
        return api_keys[key_name]
    # Fallback to environment variable
    return os.getenv(key_name)


def make_model(cfg: GraphConfigPydantic, model_api_key: str):
    """Instantiate the LLM for the supervisor based on the config."""
    # Check if this is a Vertex AI model
    if cfg.supervisor_model.lower().startswith("google_vertexai:"):
        # Extract model name (e.g., "google_vertexai:gemini-1.5-pro" -> "gemini-1.5-pro")
        vertex_model_name = cfg.supervisor_model.split(":", 1)[1]
        return ChatVertexAI(
            model_name=vertex_model_name,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        )
    else:
        # For other models, use init_chat_model with API key
        return init_chat_model(
            model=cfg.supervisor_model,
            api_key=model_api_key
        )


def make_prompt(cfg: GraphConfigPydantic):
    """Build the system prompt, falling back to a sensible default."""
    # Only include delegation instructions when sub-agents are configured.
    # When agents=[], the delegation prompt confuses the model into trying
    # to call non-existent tools, resulting in empty responses.
    if cfg.agents:
        return cfg.system_prompt + UNEDITABLE_SYSTEM_PROMPT
    return cfg.system_prompt


def graph(config: RunnableConfig):
    cfg = GraphConfigPydantic(**config.get("configurable", {}))
    
    # Auth disabled — no token extraction needed
    child_graphs = make_child_graphs(cfg)

    # Get the API key from the RunnableConfig or from the environment variable
    # For Vertex AI, this will be None (uses service account)
    model_api_key = get_api_key_for_model(cfg.supervisor_model, config)
    if model_api_key is None and not cfg.supervisor_model.lower().startswith("google_vertexai:"):
        model_api_key = "No token found"

    return create_supervisor(
        child_graphs,
        model=make_model(cfg, model_api_key),
        prompt=make_prompt(cfg),
        config_schema=GraphConfigPydantic,
        handoff_tool_prefix="delegate_to_",
        output_mode="last_message",
        add_handoff_messages=True,
    )

