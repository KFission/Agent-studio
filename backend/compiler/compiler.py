"""
Graph Compiler (Layer 3) - Compiles visual Graph Manifests into executable LangGraph StateGraphs.
This is the critical bridge between the no-code canvas and production-grade agent execution.

Compilation Pipeline:
1. Manifest validation (schema + structural checks)
2. Dependency resolution (topological sort)
3. State schema generation (dynamic Pydantic model)
4. Node function binding (map visual node types to pre-built implementations)
5. Edge routing compilation (conditional edges from node configs)
6. Graph assembly and validation
"""

import json
import time
from typing import Optional, Dict, List, Any, Callable, Type
from pydantic import BaseModel, Field, create_model

from backend.compiler.manifest import (
    GraphManifest, NodeDefinition, EdgeDefinition,
    NodeType, EdgeType, LLMNodeConfig, APIToolConfig,
    ConditionalConfig, ApprovalConfig, TransformConfig,
    RAGConfig, LoopConfig, SubgraphConfig,
)
from backend.llm_registry.provider_factory import ProviderFactory
from backend.llm_registry.model_library import ModelLibrary
from backend.prompt_studio.prompt_manager import PromptManager


class CompilationResult(BaseModel):
    """Result of compiling a graph manifest."""
    success: bool = False
    manifest_id: str = ""
    manifest_name: str = ""
    node_count: int = 0
    edge_count: int = 0
    entry_node: str = ""
    compilation_time_ms: float = 0.0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    compiled_node_ids: List[str] = Field(default_factory=list)


class GraphCompiler:
    """
    Compiles a declarative GraphManifest (JSON from the canvas) into an
    executable LangGraph StateGraph. Each visual node type maps to a
    parameterized Python function — no user-written code required.
    """

    def __init__(
        self,
        provider_factory: Optional[ProviderFactory] = None,
        prompt_manager: Optional[PromptManager] = None,
        library: Optional[ModelLibrary] = None,
    ):
        self._factory = provider_factory or ProviderFactory(library or ModelLibrary())
        self._prompts = prompt_manager or PromptManager()

    def compile(self, manifest: GraphManifest) -> CompilationResult:
        """
        Compile a GraphManifest into a LangGraph StateGraph.

        Returns a CompilationResult with success status, errors, and metadata.
        The compiled graph is stored internally and can be executed via run().
        """
        start = time.time()
        result = CompilationResult(
            manifest_id=manifest.manifest_id,
            manifest_name=manifest.name,
            node_count=len(manifest.nodes),
            edge_count=len(manifest.edges),
        )

        # Step 1: Validate manifest
        errors = manifest.validate()
        if errors:
            result.errors = errors
            result.compilation_time_ms = round((time.time() - start) * 1000, 1)
            return result

        # Step 2: Topological sort
        sorted_ids = manifest.topological_sort()
        if len(sorted_ids) != len(manifest.nodes):
            result.errors.append("Topological sort failed — graph may contain cycles")
            result.compilation_time_ms = round((time.time() - start) * 1000, 1)
            return result

        # Step 3: Generate state schema
        state_model = self._generate_state_model(manifest)

        # Step 4: Build node functions
        node_functions: Dict[str, Callable] = {}
        for node_id in sorted_ids:
            node = manifest.get_node(node_id)
            if not node:
                result.errors.append(f"Node '{node_id}' not found during compilation")
                continue
            try:
                fn = self._build_node_function(node, manifest)
                node_functions[node_id] = fn
                result.compiled_node_ids.append(node_id)
            except Exception as e:
                result.errors.append(f"Failed to compile node '{node_id}' ({node.node_type.value}): {e}")

        if result.errors:
            result.compilation_time_ms = round((time.time() - start) * 1000, 1)
            return result

        # Step 5: Build edge routing
        edge_routing = self._build_edge_routing(manifest)

        # Step 6: Assemble LangGraph StateGraph
        try:
            graph = self._assemble_graph(
                manifest, state_model, node_functions, edge_routing
            )
            entry = manifest.get_entry_node()
            result.entry_node = entry.node_id if entry else ""
            result.success = True

            # Store compiled graph for execution
            self._compiled_graphs = getattr(self, "_compiled_graphs", {})
            self._compiled_graphs[manifest.manifest_id] = {
                "graph": graph,
                "manifest": manifest,
                "state_model": state_model,
                "node_functions": node_functions,
            }

        except Exception as e:
            result.errors.append(f"Graph assembly failed: {e}")

        result.compilation_time_ms = round((time.time() - start) * 1000, 1)
        return result

    def _generate_state_model(self, manifest: GraphManifest) -> Type[BaseModel]:
        """Generate a dynamic Pydantic model for the graph state."""
        fields: Dict[str, Any] = {
            "messages": (List[Any], Field(default_factory=list)),
            "current_node": (str, ""),
            "run_id": (str, ""),
        }

        # Add fields from manifest state schema
        type_map = {
            "str": str, "int": int, "float": float,
            "bool": bool, "list": list, "dict": dict,
        }
        for sf in manifest.state_schema:
            py_type = type_map.get(sf.field_type, str)
            default = sf.default if sf.default is not None else (
                "" if py_type == str else
                0 if py_type in (int, float) else
                False if py_type == bool else
                [] if py_type == list else
                {}
            )
            fields[sf.name] = (py_type, default)

        # Auto-add output keys for each node
        for node in manifest.nodes:
            key = f"output_{node.node_id}"
            if key not in fields:
                fields[key] = (Optional[Any], None)

        return create_model(f"State_{manifest.manifest_id}", **fields)

    def _build_node_function(
        self, node: NodeDefinition, manifest: GraphManifest
    ) -> Callable:
        """Build a LangGraph node function for a visual node definition."""

        if node.node_type in (NodeType.LLM, NodeType.CLASSIFIER):
            return self._build_llm_node(node)
        elif node.node_type == NodeType.API_TOOL:
            return self._build_api_node(node)
        elif node.node_type == NodeType.CONDITIONAL:
            return self._build_conditional_node(node)
        elif node.node_type == NodeType.TRANSFORM:
            return self._build_transform_node(node)
        elif node.node_type in (NodeType.APPROVAL, NodeType.REVIEW):
            return self._build_approval_node(node)
        elif node.node_type == NodeType.RAG:
            return self._build_rag_node(node)
        elif node.node_type == NodeType.LOOP:
            return self._build_loop_node(node)
        elif node.node_type == NodeType.MERGE:
            return self._build_merge_node(node)
        elif node.node_type == NodeType.DATABASE:
            return self._build_database_node(node)
        elif node.node_type == NodeType.SUBGRAPH:
            return self._build_subgraph_node(node)
        else:
            raise ValueError(f"Unsupported node type: {node.node_type}")

    def _build_llm_node(self, node: NodeDefinition) -> Callable:
        """Build an LLM invocation node."""
        config = LLMNodeConfig(**node.config)
        factory = self._factory
        prompts = self._prompts
        node_id = node.node_id

        def llm_node(state: dict) -> dict:
            # Resolve prompt
            prompt_text = config.prompt_template
            if config.prompt_template_id:
                try:
                    template = prompts.get(config.prompt_template_id)
                    if template:
                        current = template.get_current()
                        prompt_text = current.content if current else prompt_text
                except Exception:
                    pass

            # Substitute state variables into prompt
            for key, value in state.items():
                if isinstance(value, str):
                    prompt_text = prompt_text.replace(f"{{{{{key}}}}}", value)

            # Create LLM and invoke
            llm = factory.create(
                config.model_id,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

            messages = []
            if config.system_prompt:
                from langchain_core.messages import SystemMessage, HumanMessage
                messages = [SystemMessage(content=config.system_prompt), HumanMessage(content=prompt_text)]
            else:
                from langchain_core.messages import HumanMessage
                messages = [HumanMessage(content=prompt_text)]

            response = llm.invoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

            return {
                f"output_{node_id}": content,
                "current_node": node_id,
            }

        llm_node.__name__ = f"llm_{node_id}"
        return llm_node

    def _build_api_node(self, node: NodeDefinition) -> Callable:
        """Build an API tool invocation node."""
        config = APIToolConfig(**node.config)
        node_id = node.node_id

        def api_node(state: dict) -> dict:
            import httpx

            # Substitute state variables into URL and body
            url = config.url
            body = config.body_template
            for key, value in state.items():
                if isinstance(value, str):
                    url = url.replace(f"{{{{{key}}}}}", value)
                    body = body.replace(f"{{{{{key}}}}}", value)

            try:
                with httpx.Client(timeout=config.timeout_seconds) as client:
                    response = client.request(
                        method=config.method,
                        url=url,
                        headers=config.headers,
                        content=body if body else None,
                    )
                    result = response.json() if response.content else {}
            except Exception as e:
                result = {"error": str(e)}

            return {
                f"output_{node_id}": result,
                "current_node": node_id,
            }

        api_node.__name__ = f"api_{node_id}"
        return api_node

    def _build_conditional_node(self, node: NodeDefinition) -> Callable:
        """Build a conditional branching node."""
        config = ConditionalConfig(**node.config)
        node_id = node.node_id

        def conditional_node(state: dict) -> dict:
            # Evaluate condition expression against state
            try:
                result = eval(config.condition_expression, {"__builtins__": {}}, {"state": state})
            except Exception:
                result = False

            return {
                f"output_{node_id}": {"condition_result": bool(result)},
                "current_node": node_id,
            }

        conditional_node.__name__ = f"cond_{node_id}"
        return conditional_node

    def _build_transform_node(self, node: NodeDefinition) -> Callable:
        """Build a data transformation node."""
        config = TransformConfig(**node.config)
        node_id = node.node_id

        def transform_node(state: dict) -> dict:
            # Apply input mapping
            mapped = {}
            for target_key, source_expr in config.input_mapping.items():
                if source_expr in state:
                    mapped[target_key] = state[source_expr]

            output = mapped if not config.transform_expression else mapped
            result = {f"output_{node_id}": output, "current_node": node_id}
            if config.output_key:
                result[config.output_key] = output
            return result

        transform_node.__name__ = f"transform_{node_id}"
        return transform_node

    def _build_approval_node(self, node: NodeDefinition) -> Callable:
        """Build a HITL approval/review node that pauses execution."""
        config = ApprovalConfig(**node.config)
        node_id = node.node_id

        def approval_node(state: dict) -> dict:
            # In production, this triggers a LangGraph interrupt.
            # For now, return a pending approval marker.
            return {
                f"output_{node_id}": {
                    "status": "awaiting_approval",
                    "approver_roles": config.approver_roles,
                    "sla_timeout_minutes": config.sla_timeout_minutes,
                    "node_id": node_id,
                },
                "current_node": node_id,
            }

        approval_node.__name__ = f"approval_{node_id}"
        return approval_node

    def _build_rag_node(self, node: NodeDefinition) -> Callable:
        """Build a RAG retrieval node."""
        config = RAGConfig(**node.config)
        node_id = node.node_id

        def rag_node(state: dict) -> dict:
            # Placeholder: in production, queries Pinecone/ChromaDB
            return {
                f"output_{node_id}": {
                    "retrieved_documents": [],
                    "index": config.index_name,
                    "top_k": config.top_k,
                    "status": "retrieval_placeholder",
                },
                "current_node": node_id,
            }

        rag_node.__name__ = f"rag_{node_id}"
        return rag_node

    def _build_loop_node(self, node: NodeDefinition) -> Callable:
        """Build a loop iteration node."""
        config = LoopConfig(**node.config)
        node_id = node.node_id

        def loop_node(state: dict) -> dict:
            items = state.get(config.iterator_key, [])
            if not isinstance(items, list):
                items = [items]
            return {
                f"output_{node_id}": {
                    "items": items[:config.max_iterations],
                    "count": min(len(items), config.max_iterations),
                },
                "current_node": node_id,
            }

        loop_node.__name__ = f"loop_{node_id}"
        return loop_node

    def _build_merge_node(self, node: NodeDefinition) -> Callable:
        """Build a merge/aggregation node."""
        node_id = node.node_id

        def merge_node(state: dict) -> dict:
            # Collect all output_ keys from state
            outputs = {k: v for k, v in state.items() if k.startswith("output_") and v is not None}
            return {
                f"output_{node_id}": {"merged": outputs},
                "current_node": node_id,
            }

        merge_node.__name__ = f"merge_{node_id}"
        return merge_node

    def _build_database_node(self, node: NodeDefinition) -> Callable:
        """Build a database query node."""
        node_id = node.node_id

        def database_node(state: dict) -> dict:
            # Placeholder: in production, executes parameterized SQL
            return {
                f"output_{node_id}": {"status": "database_placeholder", "rows": []},
                "current_node": node_id,
            }

        database_node.__name__ = f"db_{node_id}"
        return database_node

    def _build_subgraph_node(self, node: NodeDefinition) -> Callable:
        """Build a subgraph invocation node."""
        config = SubgraphConfig(**node.config)
        node_id = node.node_id

        def subgraph_node(state: dict) -> dict:
            # Placeholder: in production, invokes a nested compiled graph
            return {
                f"output_{node_id}": {
                    "status": "subgraph_placeholder",
                    "graph_id": config.graph_id,
                },
                "current_node": node_id,
            }

        subgraph_node.__name__ = f"subgraph_{node_id}"
        return subgraph_node

    def _build_edge_routing(self, manifest: GraphManifest) -> Dict[str, Any]:
        """Build edge routing rules for conditional and branching nodes."""
        routing: Dict[str, Any] = {}

        for node in manifest.nodes:
            outgoing = manifest.get_outgoing_edges(node.node_id)
            if not outgoing:
                continue

            if node.node_type == NodeType.CONDITIONAL:
                # Build conditional router
                true_targets = [e.target_node_id for e in outgoing if e.edge_type == EdgeType.CONDITIONAL_TRUE]
                false_targets = [e.target_node_id for e in outgoing if e.edge_type == EdgeType.CONDITIONAL_FALSE]

                # Fallback: if no typed edges, use first two as true/false
                if not true_targets and not false_targets and len(outgoing) >= 2:
                    true_targets = [outgoing[0].target_node_id]
                    false_targets = [outgoing[1].target_node_id]

                routing[node.node_id] = {
                    "type": "conditional",
                    "true": true_targets[0] if true_targets else None,
                    "false": false_targets[0] if false_targets else None,
                }

            elif node.node_type in (NodeType.APPROVAL, NodeType.REVIEW):
                approved = [e.target_node_id for e in outgoing if e.edge_type == EdgeType.APPROVAL_APPROVED]
                rejected = [e.target_node_id for e in outgoing if e.edge_type == EdgeType.APPROVAL_REJECTED]
                if not approved and outgoing:
                    approved = [outgoing[0].target_node_id]

                routing[node.node_id] = {
                    "type": "approval",
                    "approved": approved[0] if approved else None,
                    "rejected": rejected[0] if rejected else None,
                }
            else:
                # Default: route to all targets (sequential)
                routing[node.node_id] = {
                    "type": "default",
                    "targets": [e.target_node_id for e in outgoing],
                }

        return routing

    def _assemble_graph(
        self,
        manifest: GraphManifest,
        state_model: Type[BaseModel],
        node_functions: Dict[str, Callable],
        edge_routing: Dict[str, Any],
    ) -> Any:
        """Assemble the final LangGraph StateGraph."""
        from langgraph.graph import StateGraph, END

        # Use dict-based state for simplicity
        builder = StateGraph(dict)

        # Add all nodes
        for node_id, fn in node_functions.items():
            builder.add_node(node_id, fn)

        # Set entry point
        entry = manifest.get_entry_node()
        if entry:
            builder.set_entry_point(entry.node_id)

        # Add edges
        for node_id, route_info in edge_routing.items():
            if route_info["type"] == "conditional":
                true_target = route_info.get("true")
                false_target = route_info.get("false")

                def make_router(nid, tt, ft):
                    def router(state):
                        output = state.get(f"output_{nid}", {})
                        if isinstance(output, dict) and output.get("condition_result"):
                            return tt or END
                        return ft or END
                    return router

                targets = {}
                if true_target:
                    targets[true_target] = true_target
                if false_target:
                    targets[false_target] = false_target
                targets[END] = END

                builder.add_conditional_edges(
                    node_id,
                    make_router(node_id, true_target, false_target),
                    targets,
                )

            elif route_info["type"] == "default":
                targets = route_info.get("targets", [])
                if len(targets) == 1:
                    builder.add_edge(node_id, targets[0])
                elif len(targets) > 1:
                    # For multiple targets, chain sequentially
                    builder.add_edge(node_id, targets[0])
                else:
                    builder.add_edge(node_id, END)

        # Nodes with no outgoing edges go to END
        nodes_with_outgoing = set(edge_routing.keys())
        for node in manifest.nodes:
            if node.node_id not in nodes_with_outgoing:
                builder.add_edge(node.node_id, END)

        return builder.compile()

    def run(
        self,
        manifest_id: str,
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a previously compiled graph."""
        compiled = getattr(self, "_compiled_graphs", {}).get(manifest_id)
        if not compiled:
            return {"error": f"Graph '{manifest_id}' not compiled. Call compile() first."}

        graph = compiled["graph"]
        state = initial_state or {}

        try:
            result = graph.invoke(state)
            return {"success": True, "state": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_compiled(self) -> List[Dict[str, Any]]:
        """List all compiled graphs."""
        compiled = getattr(self, "_compiled_graphs", {})
        return [
            {
                "manifest_id": mid,
                "name": data["manifest"].name,
                "node_count": len(data["manifest"].nodes),
            }
            for mid, data in compiled.items()
        ]
