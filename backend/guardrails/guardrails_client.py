"""
Guardrails AI Client — communicates with the guardrails-api server.
Handles guard CRUD (deploy/undeploy) and validation requests.
"""
import os
import logging
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger(__name__)

GUARDRAILS_API_URL = os.getenv("GUARDRAILS_API_URL", "http://guardrails:8000")

# Map of guard type → hub validator package
VALIDATOR_MAP = {
    "pii_detection": "guardrails/detect_pii",
    "prompt_injection": "guardrails/regex_match",  # uses regex_match with injection patterns
    "profanity": "guardrails/profanity_free",
    "regex_match": "guardrails/regex_match",
    "valid_length": "guardrails/valid_length",
    "reading_time": "guardrails/reading_time",
}

# Default injection patterns for prompt_injection guard type
PROMPT_INJECTION_REGEX = (
    r"(?i)(ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)"
    r"|you\s+are\s+now\s+(a|an|in)\b"
    r"|system\s*prompt\s*(override|reveal|show|ignore)"
    r"|DAN\s+mode"
    r"|jailbreak"
    r"|do\s+anything\s+now"
    r"|pretend\s+you\s*(are|have)\s+no\s+(rules?|restrictions?|limits?)"
    r"|forget\s+(all\s+)?(your|previous)\s+(instructions?|rules?)"
    r"|bypass\s+(safety|content|filter)"
    r"|act\s+as\s+if\s+you\s+have\s+no\s+guidelines)"
)


class GuardrailsClient:
    """Client for the guardrails-api REST server."""

    def __init__(self, base_url: str = GUARDRAILS_API_URL):
        self.base_url = base_url.rstrip("/")

    # ── Health ────────────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Check if the guardrails-api server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/health")
                return {"status": "healthy", "code": r.status_code, "url": self.base_url}
        except Exception as e:
            return {"status": "unreachable", "error": str(e), "url": self.base_url}

    # ── Guard CRUD (deploy / undeploy) ────────────────────────────

    async def list_guards(self) -> List[Dict[str, Any]]:
        """List all currently deployed guards."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{self.base_url}/guards")
                r.raise_for_status()
                return r.json()
        except Exception as e:
            logger.error(f"Failed to list guards: {e}")
            return []

    async def get_guard(self, guard_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific deployed guard by name."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{self.base_url}/guards/{guard_name}")
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                return r.json()
        except Exception as e:
            logger.error(f"Failed to get guard {guard_name}: {e}")
            return None

    async def deploy_guard(self, guard_name: str, guard_type: str,
                           description: str = "", config: Dict = None) -> Dict[str, Any]:
        """
        Deploy (create) a guard on the guardrails-api server.
        Maps guard_type to the appropriate hub validator.
        """
        validator_id = VALIDATOR_MAP.get(guard_type)
        if not validator_id:
            return {"error": f"Unknown guard type: {guard_type}. Available: {list(VALIDATOR_MAP.keys())}"}

        # Auto-inject default config for prompt_injection
        effective_config = dict(config or {})
        if guard_type == "prompt_injection" and "regex" not in effective_config:
            effective_config["regex"] = PROMPT_INJECTION_REGEX

        # For regex-based guards, use search mode (not fullmatch)
        if guard_type in ("regex_match", "prompt_injection"):
            effective_config.setdefault("match_type", "search")

        # Build the guard spec for the guardrails-api
        validators = [{"id": validator_id, "on": "prompt", "kwargs": effective_config}]

        import uuid as _uuid
        payload = {
            "id": guard_name,
            "name": guard_name,
            "description": description or f"{guard_type} guardrail",
            "validators": validators,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(f"{self.base_url}/guards", json=payload)
                r.raise_for_status()
                return {"status": "deployed", "guard": r.json()}
        except httpx.HTTPStatusError as e:
            body = e.response.text
            logger.error(f"Failed to deploy guard {guard_name}: {e} — {body}")
            return {"error": f"Deploy failed: {body}"}
        except Exception as e:
            logger.error(f"Failed to deploy guard {guard_name}: {e}")
            return {"error": str(e)}

    async def undeploy_guard(self, guard_name: str) -> Dict[str, Any]:
        """Undeploy (delete) a guard from the guardrails-api server."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.delete(f"{self.base_url}/guards/{guard_name}")
                if r.status_code == 404:
                    return {"status": "not_found", "message": f"Guard '{guard_name}' not deployed"}
                r.raise_for_status()
                return {"status": "undeployed"}
        except Exception as e:
            logger.error(f"Failed to undeploy guard {guard_name}: {e}")
            return {"error": str(e)}

    # ── Validation ────────────────────────────────────────────────

    async def validate(self, guard_name: str, text: str,
                       metadata: Dict = None) -> Dict[str, Any]:
        """
        Run validation against a deployed guard.
        Returns the guardrails-api validation result.
        """
        payload = {
            "llmOutput": text,
            **({"metadata": metadata} if metadata else {}),
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{self.base_url}/guards/{guard_name}/validate",
                    json=payload,
                )
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            body = e.response.text
            return {"error": f"Validation failed: {body}", "status_code": e.response.status_code}
        except Exception as e:
            return {"error": str(e)}


# Singleton
guardrails_client = GuardrailsClient()
