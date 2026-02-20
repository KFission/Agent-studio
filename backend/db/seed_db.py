"""
Database seeder — populates all tables with default/seed data on first startup.
Only inserts if tables are empty (idempotent).
"""
import hashlib
import logging
import os
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    AgentModel, ToolModel, PromptTemplateModel, TenantModel, UserModel,
    GuardrailRuleModel,
)
from backend.seed.seed_templates import SEED_AGENTS, SEED_PROMPTS

logger = logging.getLogger(__name__)


def _hash_password(password: str, salt: str = "jai-agent-os") -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 (stdlib, no extra deps)."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations=100_000
    ).hex()


def verify_password(password: str, password_hash: str, salt: str = "jai-agent-os") -> bool:
    """Verify a password against its hash."""
    return _hash_password(password, salt) == password_hash


async def seed_all(session: AsyncSession) -> dict:
    """
    Seed all tables if empty. Returns counts of inserted rows.
    Safe to call on every startup — skips if data already exists.
    """
    counts = {}
    counts["users"] = await _seed_users(session)
    counts["tenants"] = await _seed_tenants(session)
    counts["agents"] = await _seed_agents(session)
    counts["tools"] = await _seed_tools(session)
    counts["prompts"] = await _seed_prompts(session)
    counts["guardrails"] = await _seed_guardrails(session)
    await session.commit()
    return counts


# ── Users ─────────────────────────────────────────────────────────

async def _seed_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(UserModel.id)))
    if result.scalar_one() > 0:
        return 0

    users = [
        UserModel(
            id="admin-001",
            username="admin",
            email="admin@jaggaer.com",
            password_hash=_hash_password("admin123"),
            first_name="Platform",
            last_name="Admin",
            display_name="Platform Admin",
            tenant_id="default",
            roles=["platform_admin"],
            is_active=True,
        ),
    ]
    session.add_all(users)
    await session.flush()
    logger.info(f"Seeded {len(users)} users")
    return len(users)


# ── Tenants ───────────────────────────────────────────────────────

async def _seed_tenants(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(TenantModel.id)))
    if result.scalar_one() > 0:
        return 0

    tenants = [
        TenantModel(
            id="tenant-default",
            name="Jaggaer Default",
            slug="default",
            tier="enterprise",
            owner_email="admin@jaggaer.com",
            domain="jaggaer.com",
            is_active=True,
            allowed_providers=["google", "anthropic", "openai", "ollama"],
            quota_json={
                "max_agents": 100, "max_tools": 200, "max_users": 50,
                "llm_requests_per_minute": 60, "llm_requests_per_day": 10000,
                "max_api_keys": 10,
            },
        ),
    ]
    session.add_all(tenants)
    await session.flush()
    logger.info(f"Seeded {len(tenants)} tenants")
    return len(tenants)


# ── Agents ────────────────────────────────────────────────────────

async def _seed_agents(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(AgentModel.id)))
    if result.scalar_one() > 0:
        return 0

    rows = []
    for a in SEED_AGENTS:
        tool_bindings = [{"tool_id": tid, "tool_name": tid} for tid in a.get("tools", [])]
        rows.append(AgentModel(
            id=a["agent_id"],
            name=a["name"],
            description=a["description"],
            status="active" if a.get("status") == "active" else "draft",
            tags=a.get("tags", []),
            model_config_json={
                "model_id": a.get("config", {}).get("llm_model", "gemini-2.5-flash"),
                "temperature": a.get("config", {}).get("temperature", 0.3),
                "max_tokens": a.get("config", {}).get("max_tokens", 2000),
            },
            tools_json=tool_bindings,
            metadata_json={
                "category": a.get("category", "general"),
                "graph_type": a.get("graph_type", "langgraph"),
                "workflow_steps": a.get("workflow_steps", []),
                "metrics": a.get("metrics", {}),
                "api_readiness": a.get("api_readiness", ""),
                "intent_domains": a.get("intent_domains", {}),
                "seed_config": a.get("config", {}),
            },
            created_by="system",
        ))
    session.add_all(rows)
    await session.flush()
    logger.info(f"Seeded {len(rows)} agents")
    return len(rows)


# ── Tools ─────────────────────────────────────────────────────────

async def _seed_tools(session: AsyncSession) -> int:
    # Tools are now DB-backed only — no hardcoded seed tools.
    # Users create tools via the UI which persists them to PostgreSQL.
    return 0


# ── Prompts ───────────────────────────────────────────────────────

# ── Guardrails ─────────────────────────────────────────────────

_GUARDRAIL_SEEDS = [
    {"name": "PII Detection & Redaction", "description": "Detect and redact personally identifiable information (emails, phone numbers, SSN, credit cards) in agent inputs and outputs using Guardrails AI detect_pii validator", "rule_type": "pii_detection", "action": "redact", "applies_to": "both", "config": {"pii_entities": ["EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "CREDIT_CARD"]}},
    {"name": "Prompt Injection Guard", "description": "Detect and block jailbreak attempts, prompt injection, and instruction override patterns in user inputs", "rule_type": "prompt_injection", "action": "block", "applies_to": "input", "config": {"additional_patterns": []}},
    {"name": "Profanity Guard", "description": "Ensure agent outputs are free of profanity and offensive words using Guardrails AI profanity_free validator", "rule_type": "profanity", "action": "block", "applies_to": "output", "config": {}},
    {"name": "Output Length Limit", "description": "Enforce maximum and minimum character length on agent responses using Guardrails AI valid_length validator", "rule_type": "valid_length", "action": "block", "applies_to": "output", "config": {"min": 1, "max": 10000}},
    {"name": "Reading Time Check", "description": "Ensure agent responses stay within a readable time limit using Guardrails AI reading_time validator", "rule_type": "reading_time", "action": "warn", "applies_to": "output", "config": {"reading_time": 5}},
    {"name": "Sensitive Pattern Filter", "description": "Block or flag text matching sensitive regex patterns (e.g. internal codes, API keys) using Guardrails AI regex_match validator", "rule_type": "regex_match", "action": "redact", "applies_to": "both", "config": {"regex": "(?i)(api[_-]?key|secret|password|CONFIDENTIAL)"}},
]


async def _seed_guardrails(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(GuardrailRuleModel.id)))
    if result.scalar_one() > 0:
        return 0

    rows = []
    for g in _GUARDRAIL_SEEDS:
        rows.append(GuardrailRuleModel(
            name=g["name"],
            description=g["description"],
            rule_type=g["rule_type"],
            action=g["action"],
            applies_to=g["applies_to"],
            config_json=g.get("config", {}),
        ))
    session.add_all(rows)
    await session.flush()
    logger.info(f"Seeded {len(rows)} guardrail rules")
    return len(rows)


async def _seed_prompts(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(PromptTemplateModel.id)))
    if result.scalar_one() > 0:
        return 0

    rows = []
    for p in SEED_PROMPTS:
        rows.append(PromptTemplateModel(
            id=p["template_id"],
            name=p["name"],
            description=p.get("description", ""),
            category=p.get("category", "custom"),
            content=p["content"],
            is_builtin=True,
            created_by="system",
        ))

    session.add_all(rows)
    await session.flush()
    logger.info(f"Seeded {len(rows)} prompt templates")
    return len(rows)
