"""
Graph Registry - CRUD for graph manifests with version control.
In-memory store for Phase 1; PostgreSQL-backed in Phase 2.
Provides manifest storage, versioning, diff, import/export, and template library.
"""

import copy
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime

from backend.compiler.manifest import GraphManifest, ManifestVersion


class GraphRegistry:
    """
    Central registry for graph manifests with full version history.
    Supports CRUD, semantic versioning, status lifecycle, and template management.
    """

    def __init__(self):
        self._graphs: Dict[str, GraphManifest] = {}
        self._version_history: Dict[str, List[GraphManifest]] = {}  # manifest_id -> [versions]
        self._templates: Dict[str, GraphManifest] = {}

    # ── CRUD ──────────────────────────────────────────────────────────

    def create(self, manifest: GraphManifest) -> GraphManifest:
        """Create a new graph manifest."""
        manifest.created_at = datetime.utcnow()
        manifest.updated_at = datetime.utcnow()
        manifest.version_info.version = 1
        manifest.version_info.status = "draft"
        manifest.version_info.created_at = datetime.utcnow()

        self._graphs[manifest.manifest_id] = manifest
        self._version_history[manifest.manifest_id] = [copy.deepcopy(manifest)]
        return manifest

    def get(self, manifest_id: str) -> Optional[GraphManifest]:
        return self._graphs.get(manifest_id)

    def update(
        self,
        manifest_id: str,
        manifest: GraphManifest,
        change_note: str = "",
        created_by: str = "user",
    ) -> Optional[GraphManifest]:
        """Update a graph manifest, creating a new version."""
        existing = self.get(manifest_id)
        if not existing:
            return None

        # Bump version
        new_version = existing.version_info.version + 1
        manifest.manifest_id = manifest_id
        manifest.version_info = ManifestVersion(
            version=new_version,
            created_by=created_by,
            change_note=change_note,
            status="draft",
        )
        manifest.updated_at = datetime.utcnow()
        manifest.created_at = existing.created_at

        self._graphs[manifest_id] = manifest
        if manifest_id not in self._version_history:
            self._version_history[manifest_id] = []
        self._version_history[manifest_id].append(copy.deepcopy(manifest))
        return manifest

    def delete(self, manifest_id: str) -> bool:
        removed = self._graphs.pop(manifest_id, None)
        self._version_history.pop(manifest_id, None)
        return removed is not None

    def list_all(self, status: Optional[str] = None) -> List[GraphManifest]:
        graphs = list(self._graphs.values())
        if status:
            graphs = [g for g in graphs if g.version_info.status == status]
        return sorted(graphs, key=lambda g: g.updated_at, reverse=True)

    def search(self, query: str) -> List[GraphManifest]:
        q = query.lower()
        return [
            g for g in self._graphs.values()
            if q in g.name.lower() or q in g.description.lower() or any(q in t for t in g.tags)
        ]

    # ── Versioning ────────────────────────────────────────────────────

    def get_version(self, manifest_id: str, version: int) -> Optional[GraphManifest]:
        history = self._version_history.get(manifest_id, [])
        for m in history:
            if m.version_info.version == version:
                return m
        return None

    def list_versions(self, manifest_id: str) -> List[Dict[str, Any]]:
        history = self._version_history.get(manifest_id, [])
        return [
            {
                "version": m.version_info.version,
                "status": m.version_info.status,
                "created_at": m.version_info.created_at.isoformat(),
                "created_by": m.version_info.created_by,
                "change_note": m.version_info.change_note,
                "node_count": len(m.nodes),
                "edge_count": len(m.edges),
            }
            for m in history
        ]

    def rollback(self, manifest_id: str, version: int) -> Optional[GraphManifest]:
        """Rollback to a previous version (creates a new version from the old one)."""
        old = self.get_version(manifest_id, version)
        if not old:
            return None
        return self.update(
            manifest_id,
            copy.deepcopy(old),
            change_note=f"Rollback to v{version}",
        )

    # ── Status Lifecycle ──────────────────────────────────────────────

    def set_status(
        self,
        manifest_id: str,
        status: str,
    ) -> Optional[GraphManifest]:
        """Transition graph status: draft → published → deployed → deprecated → archived."""
        valid_transitions = {
            "draft": ["published", "archived"],
            "published": ["deployed", "draft", "archived"],
            "deployed": ["deprecated", "published"],
            "deprecated": ["archived", "deployed"],
            "archived": ["draft"],
        }

        graph = self.get(manifest_id)
        if not graph:
            return None

        current = graph.version_info.status
        allowed = valid_transitions.get(current, [])
        if status not in allowed:
            raise ValueError(
                f"Cannot transition from '{current}' to '{status}'. "
                f"Allowed: {allowed}"
            )

        graph.version_info.status = status
        graph.updated_at = datetime.utcnow()
        return graph

    # ── Templates ─────────────────────────────────────────────────────

    def save_as_template(self, manifest_id: str, template_name: str) -> Optional[GraphManifest]:
        """Save a graph as a reusable template."""
        graph = self.get(manifest_id)
        if not graph:
            return None

        template = copy.deepcopy(graph)
        template.manifest_id = f"TPL-{uuid.uuid4().hex[:8].upper()}"
        template.name = template_name
        template.metadata["is_template"] = True
        template.metadata["source_manifest_id"] = manifest_id
        self._templates[template.manifest_id] = template
        return template

    def create_from_template(self, template_id: str, name: str) -> Optional[GraphManifest]:
        """Create a new graph from a template."""
        template = self._templates.get(template_id)
        if not template:
            return None

        new_graph = copy.deepcopy(template)
        new_graph.manifest_id = f"GM-{uuid.uuid4().hex[:8].upper()}"
        new_graph.name = name
        new_graph.metadata.pop("is_template", None)
        new_graph.metadata["created_from_template"] = template_id
        new_graph.version_info = ManifestVersion(version=1, status="draft")
        return self.create(new_graph)

    def list_templates(self) -> List[GraphManifest]:
        return list(self._templates.values())

    # ── Import / Export ───────────────────────────────────────────────

    def export_manifest(self, manifest_id: str) -> Optional[Dict[str, Any]]:
        graph = self.get(manifest_id)
        if not graph:
            return None
        return graph.model_dump(mode="json")

    def import_manifest(self, data: Dict[str, Any]) -> GraphManifest:
        manifest = GraphManifest(**data)
        manifest.manifest_id = f"GM-{uuid.uuid4().hex[:8].upper()}"
        return self.create(manifest)

    # ── Stats ─────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        graphs = list(self._graphs.values())
        by_status: Dict[str, int] = {}
        for g in graphs:
            s = g.version_info.status
            by_status[s] = by_status.get(s, 0) + 1

        return {
            "total_graphs": len(graphs),
            "total_templates": len(self._templates),
            "by_status": by_status,
            "total_versions": sum(len(v) for v in self._version_history.values()),
        }
