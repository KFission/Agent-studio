"""
Graph Manifest Schema - Declarative JSON format for visual agent graphs.
The manifest is the bridge between the ReactFlow canvas (L1) and the
LangGraph compiler (L3). Every visual graph serializes to this format.
"""

import uuid
from typing import Optional, Dict, List, Any, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """All supported visual node types from the canvas palette."""
    LLM = "llm"
    CLASSIFIER = "classifier"
    API_TOOL = "api"
    DATABASE = "database"
    RAG = "rag"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    MERGE = "merge"
    APPROVAL = "approval"
    REVIEW = "review"
    TRANSFORM = "transform"
    SUBGRAPH = "subgraph"


class EdgeType(str, Enum):
    """Edge routing types."""
    DEFAULT = "default"
    CONDITIONAL_TRUE = "conditional_true"
    CONDITIONAL_FALSE = "conditional_false"
    LOOP_BODY = "loop_body"
    LOOP_EXIT = "loop_exit"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"


class RetryPolicy(BaseModel):
    """Retry configuration for a node."""
    max_retries: int = 3
    backoff: Literal["fixed", "exp", "linear"] = "exp"
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0


class LLMNodeConfig(BaseModel):
    """Configuration for LLM and Classifier nodes."""
    model_id: str = "gemini-2.5-flash"
    temperature: float = 0.0
    max_tokens: int = 4096
    prompt_template: str = ""
    prompt_template_id: Optional[str] = None  # reference to Prompt Studio template
    system_prompt: Optional[str] = None
    output_schema: Optional[Dict[str, Any]] = None  # Pydantic-style JSON schema
    labels: List[str] = Field(default_factory=list)  # for classifier nodes
    confidence_threshold: float = 0.8  # for classifier nodes


class APIToolConfig(BaseModel):
    """Configuration for API Tool nodes."""
    url: str = ""
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    body_template: str = ""
    auth_type: Literal["none", "api_key", "oauth2", "mtls"] = "none"
    response_mapping: Dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 30


class DatabaseConfig(BaseModel):
    """Configuration for Database nodes."""
    connection_id: str = ""
    query_template: str = ""
    parameters: Dict[str, str] = Field(default_factory=dict)
    result_schema: Optional[Dict[str, Any]] = None


class RAGConfig(BaseModel):
    """Configuration for RAG Retrieval nodes."""
    index_name: str = ""
    namespace: str = "default"
    top_k: int = 5
    filter_metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding_model: str = "text-embedding-004"


class ConditionalConfig(BaseModel):
    """Configuration for Conditional branch nodes."""
    condition_expression: str = ""  # JSONPath or Python expression
    true_label: str = "True"
    false_label: str = "False"


class LoopConfig(BaseModel):
    """Configuration for Loop nodes."""
    iterator_key: str = ""  # state key containing the list to iterate
    max_iterations: int = 100
    parallel: bool = False
    break_condition: Optional[str] = None


class ApprovalConfig(BaseModel):
    """Configuration for HITL Approval nodes."""
    approver_roles: List[str] = Field(default_factory=list)
    sla_timeout_minutes: int = 240
    escalation_role: Optional[str] = None
    auto_approve_conditions: Optional[str] = None


class TransformConfig(BaseModel):
    """Configuration for Transform nodes."""
    input_mapping: Dict[str, str] = Field(default_factory=dict)
    transform_expression: str = ""  # JMESPath or JSONata
    output_key: str = ""


class SubgraphConfig(BaseModel):
    """Configuration for Subgraph nodes."""
    graph_id: str = ""
    graph_version: Optional[int] = None
    input_mapping: Dict[str, str] = Field(default_factory=dict)
    output_mapping: Dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 120


class NodeDefinition(BaseModel):
    """A single node in the graph manifest."""
    node_id: str
    node_type: NodeType
    label: str = ""
    description: str = ""
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    config: Dict[str, Any] = Field(default_factory=dict)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_typed_config(self) -> BaseModel:
        """Parse config dict into the appropriate typed config model."""
        config_map = {
            NodeType.LLM: LLMNodeConfig,
            NodeType.CLASSIFIER: LLMNodeConfig,
            NodeType.API_TOOL: APIToolConfig,
            NodeType.DATABASE: DatabaseConfig,
            NodeType.RAG: RAGConfig,
            NodeType.CONDITIONAL: ConditionalConfig,
            NodeType.LOOP: LoopConfig,
            NodeType.MERGE: TransformConfig,
            NodeType.APPROVAL: ApprovalConfig,
            NodeType.REVIEW: ApprovalConfig,
            NodeType.TRANSFORM: TransformConfig,
            NodeType.SUBGRAPH: SubgraphConfig,
        }
        model_cls = config_map.get(self.node_type, LLMNodeConfig)
        return model_cls(**self.config)


class EdgeDefinition(BaseModel):
    """A directed edge between two nodes."""
    edge_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType = EdgeType.DEFAULT
    label: str = ""
    condition: Optional[str] = None  # for conditional edges
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StateField(BaseModel):
    """A field in the graph state schema."""
    name: str
    field_type: str = "str"  # str, int, float, bool, list, dict
    default: Optional[Any] = None
    description: str = ""


class ManifestVersion(BaseModel):
    """Version metadata for a graph manifest."""
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "user"
    change_note: str = ""
    status: Literal["draft", "published", "deployed", "deprecated", "archived"] = "draft"


class GraphManifest(BaseModel):
    """
    Complete graph manifest — the declarative JSON document that defines
    an agent workflow. Produced by the ReactFlow canvas, consumed by the
    Graph Compiler to generate executable LangGraph StateGraphs.
    """
    manifest_id: str = Field(default_factory=lambda: f"GM-{uuid.uuid4().hex[:8].upper()}")
    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    nodes: List[NodeDefinition] = Field(default_factory=list)
    edges: List[EdgeDefinition] = Field(default_factory=list)
    state_schema: List[StateField] = Field(default_factory=list)
    entry_node_id: Optional[str] = None  # first node to execute
    version_info: ManifestVersion = Field(default_factory=ManifestVersion)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[NodeDefinition]:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def get_outgoing_edges(self, node_id: str) -> List[EdgeDefinition]:
        return [e for e in self.edges if e.source_node_id == node_id]

    def get_incoming_edges(self, node_id: str) -> List[EdgeDefinition]:
        return [e for e in self.edges if e.target_node_id == node_id]

    def get_entry_node(self) -> Optional[NodeDefinition]:
        """Find the entry node (explicitly set or node with no incoming edges)."""
        if self.entry_node_id:
            return self.get_node(self.entry_node_id)
        # Auto-detect: node with no incoming edges
        target_ids = {e.target_node_id for e in self.edges}
        for n in self.nodes:
            if n.node_id not in target_ids:
                return n
        return self.nodes[0] if self.nodes else None

    def topological_sort(self) -> List[str]:
        """Return node IDs in topological order for compilation."""
        adj: Dict[str, List[str]] = {n.node_id: [] for n in self.nodes}
        in_degree: Dict[str, int] = {n.node_id: 0 for n in self.nodes}
        for e in self.edges:
            if e.source_node_id in adj:
                adj[e.source_node_id].append(e.target_node_id)
                in_degree[e.target_node_id] = in_degree.get(e.target_node_id, 0) + 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            nid = queue.pop(0)
            result.append(nid)
            for neighbor in adj.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return result

    def validate(self) -> List[str]:
        """Validate the manifest for common errors. Returns list of error messages."""
        errors = []
        node_ids = {n.node_id for n in self.nodes}

        if not self.nodes:
            errors.append("Graph has no nodes")

        if not self.name:
            errors.append("Graph name is required")

        # Check edges reference valid nodes
        for e in self.edges:
            if e.source_node_id not in node_ids:
                errors.append(f"Edge {e.edge_id}: source '{e.source_node_id}' not found")
            if e.target_node_id not in node_ids:
                errors.append(f"Edge {e.edge_id}: target '{e.target_node_id}' not found")

        # Check for entry node
        if not self.get_entry_node():
            errors.append("No entry node found (set entry_node_id or ensure one node has no incoming edges)")

        # Check conditional nodes have both branches
        for n in self.nodes:
            if n.node_type == NodeType.CONDITIONAL:
                outgoing = self.get_outgoing_edges(n.node_id)
                types = {e.edge_type for e in outgoing}
                if EdgeType.CONDITIONAL_TRUE not in types and EdgeType.CONDITIONAL_FALSE not in types:
                    if len(outgoing) < 2:
                        errors.append(f"Conditional node '{n.node_id}' needs at least 2 outgoing edges")

        # Check for cycles (topological sort should cover all nodes)
        sorted_ids = self.topological_sort()
        if len(sorted_ids) != len(self.nodes):
            errors.append("Graph contains cycles — LangGraph requires a DAG (except explicit loop nodes)")

        return errors
