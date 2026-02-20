"""
Prompt Studio - Template CRUD, variable injection, version history.
Enables non-Python developers to build, test, and manage prompt templates
through the Agent Studio UI without writing code.
"""

import re
import uuid
import hashlib
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class PromptCategory(str, Enum):
    AGENT = "agent"
    CLASSIFIER = "classifier"
    EXTRACTOR = "extractor"
    SUMMARIZER = "summarizer"
    VALIDATOR = "validator"
    CUSTOM = "custom"


class PromptVersion(BaseModel):
    """A single version of a prompt template."""
    version_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    version_number: int = 1
    content: str
    variables: List[str] = Field(default_factory=list)
    change_note: str = ""
    created_by: str = "system"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    content_hash: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:12]
        if not self.variables:
            self.variables = PromptTemplate.extract_variables(self.content)


class PromptTemplate(BaseModel):
    """A managed prompt template with version history."""
    template_id: str = Field(default_factory=lambda: f"PT-{uuid.uuid4().hex[:8].upper()}")
    name: str
    description: str = ""
    category: PromptCategory = PromptCategory.CUSTOM
    tags: List[str] = Field(default_factory=list)
    current_version: int = 1
    versions: List[PromptVersion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def extract_variables(content: str) -> List[str]:
        """Extract {{variable}} placeholders from prompt content."""
        return list(set(re.findall(r"\{\{(\w+)\}\}", content)))

    def get_current(self) -> Optional[PromptVersion]:
        for v in self.versions:
            if v.version_number == self.current_version:
                return v
        return self.versions[-1] if self.versions else None

    def get_version(self, version_number: int) -> Optional[PromptVersion]:
        for v in self.versions:
            if v.version_number == version_number:
                return v
        return None

    def render(self, variables: Dict[str, str], version_number: Optional[int] = None) -> str:
        """Render the prompt template with variable substitution."""
        ver = self.get_version(version_number) if version_number else self.get_current()
        if not ver:
            raise ValueError(f"No version found for template {self.template_id}")

        content = ver.content
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))

        # Check for unresolved variables
        remaining = re.findall(r"\{\{(\w+)\}\}", content)
        if remaining:
            raise ValueError(f"Unresolved variables: {remaining}")

        return content

    def add_version(self, content: str, change_note: str = "", created_by: str = "system") -> PromptVersion:
        """Add a new version of this template."""
        next_num = max((v.version_number for v in self.versions), default=0) + 1
        version = PromptVersion(
            version_number=next_num,
            content=content,
            change_note=change_note,
            created_by=created_by,
        )
        self.versions.append(version)
        self.current_version = next_num
        self.updated_at = datetime.utcnow()
        return version


# ── Built-in Prompt Templates ─────────────────────────────────────────────────

BUILTIN_TEMPLATES: List[PromptTemplate] = [
    PromptTemplate(
        template_id="PT-CLASSIFY",
        name="Intent Classifier",
        description="Classify user intent into one of the provided categories",
        category=PromptCategory.CLASSIFIER,
        tags=["routing", "classification"],
        versions=[PromptVersion(
            version_number=1,
            content="""You are an intent classifier for a procurement system.

Given the user message, classify it into exactly ONE of these categories:
{{categories}}

User message: {{user_message}}

Respond with ONLY the category name, nothing else.""",
            change_note="Initial version",
        )],
    ),
    PromptTemplate(
        template_id="PT-EXTRACT",
        name="Entity Extractor",
        description="Extract structured entities from unstructured text",
        category=PromptCategory.EXTRACTOR,
        tags=["extraction", "structured-output"],
        versions=[PromptVersion(
            version_number=1,
            content="""Extract the following entities from the text below.
Return a JSON object with these fields: {{fields}}

Text:
{{input_text}}

If a field is not found, set it to null. Return ONLY valid JSON.""",
            change_note="Initial version",
        )],
    ),
    PromptTemplate(
        template_id="PT-AGENT-REASON",
        name="Agent Reasoning Step",
        description="General-purpose agent reasoning with context and tools",
        category=PromptCategory.AGENT,
        tags=["agent", "reasoning"],
        versions=[PromptVersion(
            version_number=1,
            content="""You are {{agent_name}}, a procurement AI agent.

Your job: {{job_description}}

Context from previous steps:
{{context}}

Available tools:
{{tools}}

Current task: {{task}}

Think step by step, then decide your next action. If you need to call a tool, specify the tool name and parameters. If you have enough information to respond, provide your answer.""",
            change_note="Initial version",
        )],
    ),
    PromptTemplate(
        template_id="PT-SUMMARIZE",
        name="Result Summarizer",
        description="Summarize agent execution results for the end user",
        category=PromptCategory.SUMMARIZER,
        tags=["summary", "output"],
        versions=[PromptVersion(
            version_number=1,
            content="""Summarize the following agent execution results in a clear, concise format suitable for a {{audience}} audience.

Agent: {{agent_name}}
Task: {{task}}
Results:
{{results}}

Provide:
1. A one-sentence summary
2. Key findings (bullet points)
3. Recommended next steps""",
            change_note="Initial version",
        )],
    ),
]


class PromptManager:
    """
    Manages prompt templates with CRUD, versioning, and rendering.
    In-memory store for Phase 1; PostgreSQL-backed in Phase 2.
    """

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._load_builtins()

    def _load_builtins(self) -> None:
        for t in BUILTIN_TEMPLATES:
            self._templates[t.template_id] = t

    def create(
        self,
        name: str,
        content: str,
        description: str = "",
        category: PromptCategory = PromptCategory.CUSTOM,
        tags: Optional[List[str]] = None,
        created_by: str = "user",
    ) -> PromptTemplate:
        template = PromptTemplate(
            name=name,
            description=description,
            category=category,
            tags=tags or [],
        )
        version = template.add_version(content, change_note="Initial version", created_by=created_by)
        self._templates[template.template_id] = template
        return template

    def get(self, template_id: str) -> Optional[PromptTemplate]:
        return self._templates.get(template_id)

    def update(self, template_id: str, content: str, change_note: str = "", created_by: str = "user") -> Optional[PromptVersion]:
        template = self.get(template_id)
        if not template:
            return None
        return template.add_version(content, change_note=change_note, created_by=created_by)

    def delete(self, template_id: str) -> bool:
        return self._templates.pop(template_id, None) is not None

    def list_all(self) -> List[PromptTemplate]:
        return list(self._templates.values())

    def list_by_category(self, category: PromptCategory) -> List[PromptTemplate]:
        return [t for t in self._templates.values() if t.category == category]

    def search(self, query: str) -> List[PromptTemplate]:
        q = query.lower()
        return [
            t for t in self._templates.values()
            if q in t.name.lower() or q in t.description.lower() or any(q in tag for tag in t.tags)
        ]

    def render(self, template_id: str, variables: Dict[str, str], version_number: Optional[int] = None) -> str:
        template = self.get(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")
        return template.render(variables, version_number)

    def get_variables(self, template_id: str) -> List[str]:
        template = self.get(template_id)
        if not template:
            return []
        current = template.get_current()
        return current.variables if current else []

    def to_dict(self) -> List[Dict[str, Any]]:
        return [t.model_dump(mode="json") for t in self._templates.values()]
