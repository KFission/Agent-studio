"""
Agent Studio Platform - Configuration Settings
Multi-provider LLM config, Jaggaer API, LangSmith, channels, and platform settings.
Adapted from JAI Agent Orchestrator patterns.
"""

import os
import json
from typing import Optional, Any, Dict
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def fetch_secret_json(secret_id: str, project_id: str, version: str = "latest") -> Optional[Dict[str, Any]]:
    """Fetch and parse a JSON secret from GCP Secret Manager."""
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("utf-8")
        return json.loads(payload)
    except ImportError:
        return None
    except Exception as e:
        print(f"[SECRET] Failed to fetch secret {secret_id}: {e}")
        return None


class Settings(BaseSettings):
    """Agent Studio platform settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── GCP Configuration ─────────────────────────────────────────────
    gcp_project_id: str = Field(default="gcp-jai-platform-dev", alias="GCP_PROJECT_ID")
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    region: str = Field(default="us-central1", alias="REGION")

    # ── Jaggaer API Configuration ─────────────────────────────────────
    jaggaer_base_url: str = Field(
        default="https://premajor.app11.jaggaer.com/arc/api",
        alias="JAGGAER_BASE_URL",
    )
    jaggaer_api_key: Optional[str] = Field(default=None, alias="JAGGAER_API_KEY")
    jaggaer_tenant_id: str = Field(default="default", alias="JAGGAER_TENANT_ID")
    jaggaer_origination: str = Field(default="agent-studio", alias="JAGGAER_ORIGINATION")

    # ── Google Gemini Models ──────────────────────────────────────────
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_flash_model: str = "gemini-2.0-flash-exp"
    gemini_pro_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.0
    gemini_max_tokens: int = 4096

    # ── Anthropic Claude Models ───────────────────────────────────────
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    claude_model: str = "claude-sonnet-4-20250514"
    claude_temperature: float = 0.0
    claude_max_tokens: int = 8192

    # ── OpenAI Models ─────────────────────────────────────────────────
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.0
    openai_max_tokens: int = 4096

    # ── Ollama (Local / Self-Hosted: Gemma, Kimi, etc.) ───────────────
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = "gemma2:9b"

    # ── LangSmith Observability ───────────────────────────────────────
    langchain_tracing_v2: str = Field(default="true", alias="LANGCHAIN_TRACING_V2")
    langchain_endpoint: str = Field(default="https://api.smith.langchain.com", alias="LANGCHAIN_ENDPOINT")
    langchain_api_key: Optional[str] = Field(default=None, alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="agent-studio", alias="LANGCHAIN_PROJECT")

    # ── Langfuse Observability (self-hosted) ───────────────────────────
    langfuse_host: str = Field(default="http://localhost:3030", alias="LANGFUSE_HOST")
    langfuse_public_key: Optional[str] = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: Optional[str] = Field(default=None, alias="LANGFUSE_SECRET_KEY")

    # ── Redis (Checkpoints, Queues) ───────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # ── PostgreSQL (Graph Registry, Audit) ────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://langfuse:langfuse@localhost:5433/agent_studio",
        alias="DATABASE_URL",
    )
    encryption_key: str = Field(default="", alias="ENCRYPTION_KEY")

    # ── Keycloak IDP Configuration ─────────────────────────────────────
    keycloak_server_url: str = Field(default="http://localhost:8180", alias="KEYCLOAK_SERVER_URL")
    keycloak_realm: str = Field(default="jai-agent-os", alias="KEYCLOAK_REALM")
    keycloak_client_id: str = Field(default="jai-agent-os-api", alias="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: str = Field(default="", alias="KEYCLOAK_CLIENT_SECRET")

    # ── Vertex AI (Service Account) ──────────────────────────────────
    google_application_credentials: str = Field(default="", alias="GOOGLE_APPLICATION_CREDENTIALS")

    # ── Channel Configuration ─────────────────────────────────────────
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET")
    websocket_max_connections: int = 100
    api_rate_limit_per_minute: int = 60

    # ── Platform Defaults ─────────────────────────────────────────────
    agent_timeout_seconds: int = 120
    max_retries: int = 3
    default_max_tokens: int = 4096

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ["dev", "development", "qa", "uit", "prod"]
        if v.lower() not in allowed:
            print(f"[SETTINGS] Warning: environment '{v}' not in {allowed}")
        return v.lower()


settings = Settings()
