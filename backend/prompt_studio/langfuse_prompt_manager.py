"""
JAI Agent OS — Langfuse-backed Prompt Manager
Replaces the in-memory PromptManager with one that stores prompts in Langfuse.
Supports: versioning, labels, config, variables, text + chat prompt types.
"""

import re
import httpx
from typing import Optional, Dict, List, Any


class LangfusePromptManager:
    """
    Manages prompts via Langfuse's REST API.
    All state lives in Langfuse — no local storage.
    """

    def __init__(self, host: str, public_key: str, secret_key: str):
        self._host = host.rstrip("/")
        self._public_key = public_key
        self._secret_key = secret_key

    def _auth(self):
        return (self._public_key, self._secret_key)

    def _api(self, path: str) -> str:
        return f"{self._host}/api/public/v2{path}"

    # ── CRUD ───────────────────────────────────────────────────────────

    def list_prompts(self, limit: int = 50, page: int = 1, name: Optional[str] = None,
                     tag: Optional[str] = None, label: Optional[str] = None) -> Dict:
        """List all prompts with pagination."""
        params: Dict[str, Any] = {"limit": limit, "page": page}
        if name:
            params["name"] = name
        if tag:
            params["tag"] = tag
        if label:
            params["label"] = label
        try:
            resp = httpx.get(self._api("/prompts"), auth=self._auth(), params=params, timeout=10)
            if resp.status_code != 200:
                return {"data": [], "meta": {"totalItems": 0}}
            return resp.json()
        except Exception as e:
            print(f"[LANGFUSE-PROMPTS] list error: {e}")
            return {"data": [], "meta": {"totalItems": 0}}

    def get_prompt(self, name: str, version: Optional[int] = None,
                   label: Optional[str] = None) -> Optional[Dict]:
        """Get a prompt by name. Optionally specify version or label."""
        params: Dict[str, Any] = {}
        if version is not None:
            params["version"] = version
        elif label:
            params["label"] = label
        else:
            params["label"] = "latest"
        try:
            resp = httpx.get(self._api(f"/prompts/{name}"), auth=self._auth(),
                             params=params, timeout=10)
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception as e:
            print(f"[LANGFUSE-PROMPTS] get error: {e}")
            return None

    def create_prompt(self, name: str, prompt: Any, prompt_type: str = "text",
                      config: Optional[Dict] = None, labels: Optional[List[str]] = None,
                      tags: Optional[List[str]] = None) -> Optional[Dict]:
        """Create a new prompt or a new version of an existing prompt."""
        body: Dict[str, Any] = {
            "name": name,
            "prompt": prompt,
            "type": prompt_type,
            "labels": labels or ["latest"],
            "config": config or {},
            "tags": tags or [],
        }
        try:
            resp = httpx.post(self._api("/prompts"), auth=self._auth(),
                              json=body, timeout=10)
            if resp.status_code in (200, 201):
                return resp.json()
            print(f"[LANGFUSE-PROMPTS] create error {resp.status_code}: {resp.text[:200]}")
            return None
        except Exception as e:
            print(f"[LANGFUSE-PROMPTS] create error: {e}")
            return None

    def get_all_versions(self, name: str) -> List[Dict]:
        """Get all versions of a prompt by fetching the list entry then each version."""
        listing = self.list_prompts(limit=100)
        entry = None
        for p in listing.get("data", []):
            if p.get("name") == name:
                entry = p
                break
        if not entry:
            return []

        version_nums = sorted(entry.get("versions", []))
        versions = []
        for v in version_nums:
            prompt_data = self.get_prompt(name, version=v)
            if prompt_data:
                versions.append(prompt_data)
        return versions

    def set_label(self, name: str, version: int, label: str) -> bool:
        """Set a label on a specific version (promote to production, etc.)."""
        prompt = self.get_prompt(name, version=version)
        if not prompt:
            return False
        current_labels = prompt.get("labels", [])
        if label not in current_labels:
            current_labels.append(label)
        # Langfuse doesn't have a dedicated label endpoint on older versions
        # We recreate the prompt version with updated labels
        body = {
            "name": name,
            "prompt": prompt.get("prompt"),
            "type": prompt.get("type", "text"),
            "labels": current_labels,
            "config": prompt.get("config", {}),
            "tags": prompt.get("tags", []),
        }
        try:
            resp = httpx.post(self._api("/prompts"), auth=self._auth(), json=body, timeout=10)
            return resp.status_code in (200, 201)
        except Exception:
            return False

    # ── Variables ──────────────────────────────────────────────────────

    @staticmethod
    def extract_variables(prompt_content: Any) -> List[str]:
        """Extract {{variable}} placeholders from prompt content."""
        if isinstance(prompt_content, str):
            return list(set(re.findall(r"\{\{(\w+)\}\}", prompt_content)))
        elif isinstance(prompt_content, list):
            # Chat prompt — extract from all messages
            variables = set()
            for msg in prompt_content:
                content = msg.get("content", "")
                variables.update(re.findall(r"\{\{(\w+)\}\}", content))
            return list(variables)
        return []

    @staticmethod
    def render_prompt(prompt_content: Any, variables: Dict[str, str]) -> Any:
        """Render a prompt by substituting {{variable}} placeholders."""
        if isinstance(prompt_content, str):
            result = prompt_content
            for key, value in variables.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
            return result
        elif isinstance(prompt_content, list):
            rendered = []
            for msg in prompt_content:
                content = msg.get("content", "")
                for key, value in variables.items():
                    content = content.replace(f"{{{{{key}}}}}", str(value))
                rendered.append({**msg, "content": content})
            return rendered
        return prompt_content

    # ── Versioning: Rollback & Diff ──────────────────────────────────

    def rollback_to_version(self, name: str, target_version: int) -> Optional[Dict]:
        """Rollback a prompt to a previous version by creating a new version with the old content."""
        old_prompt = self.get_prompt(name, version=target_version)
        if not old_prompt:
            return None
        # Create a new version with the old content, labelled as latest
        result = self.create_prompt(
            name=name,
            prompt=old_prompt.get("prompt", ""),
            prompt_type=old_prompt.get("type", "text"),
            config=old_prompt.get("config", {}),
            labels=["latest"],
            tags=old_prompt.get("tags", []),
        )
        if result:
            result["_rollback_from"] = target_version
        return result

    def diff_versions(self, name: str, version_a: int, version_b: int) -> Optional[Dict]:
        """Compare two versions of a prompt, returning a structured diff."""
        prompt_a = self.get_prompt(name, version=version_a)
        prompt_b = self.get_prompt(name, version=version_b)
        if not prompt_a or not prompt_b:
            return None

        content_a = prompt_a.get("prompt", "")
        content_b = prompt_b.get("prompt", "")

        # Compute line-level diff
        import difflib
        if isinstance(content_a, str) and isinstance(content_b, str):
            diff_lines = list(difflib.unified_diff(
                content_a.splitlines(keepends=True),
                content_b.splitlines(keepends=True),
                fromfile=f"v{version_a}",
                tofile=f"v{version_b}",
                lineterm="",
            ))
        else:
            # Chat prompts — diff the JSON representation
            import json
            a_str = json.dumps(content_a, indent=2)
            b_str = json.dumps(content_b, indent=2)
            diff_lines = list(difflib.unified_diff(
                a_str.splitlines(keepends=True),
                b_str.splitlines(keepends=True),
                fromfile=f"v{version_a}",
                tofile=f"v{version_b}",
                lineterm="",
            ))

        vars_a = set(self.extract_variables(content_a))
        vars_b = set(self.extract_variables(content_b))

        return {
            "name": name,
            "version_a": version_a,
            "version_b": version_b,
            "content_a": content_a,
            "content_b": content_b,
            "diff": "\n".join(diff_lines),
            "has_changes": content_a != content_b,
            "variables_added": list(vars_b - vars_a),
            "variables_removed": list(vars_a - vars_b),
            "labels_a": prompt_a.get("labels", []),
            "labels_b": prompt_b.get("labels", []),
        }

    # ── Seed built-in prompts ─────────────────────────────────────────

    def seed_builtin_prompts(self) -> int:
        """Seed built-in prompts into Langfuse if they don't exist yet."""
        from backend.prompt_studio.prompt_manager import BUILTIN_TEMPLATES
        seeded = 0
        for t in BUILTIN_TEMPLATES:
            existing = self.get_prompt(t.name)
            if existing:
                continue
            current = t.get_current()
            if not current:
                continue
            result = self.create_prompt(
                name=t.name,
                prompt=current.content,
                prompt_type="text",
                config={"model": "gemini-2.5-flash", "temperature": 0.7},
                labels=["latest", "production"],
                tags=t.tags + [t.category.value],
            )
            if result:
                seeded += 1
        return seeded
