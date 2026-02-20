"""
Multi-Provider LLM Model Library.
Central registry of all available models with pricing, capabilities, and metadata.
Supports: Google Gemini, Anthropic Claude, OpenAI GPT, Ollama (Gemma, Kimi, etc.)
"""

from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


class ModelCapability(str, Enum):
    REASONING = "reasoning"
    CLASSIFICATION = "classification"
    CODE_GENERATION = "code_generation"
    STRUCTURED_OUTPUT = "structured_output"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    LONG_CONTEXT = "long_context"
    FAST_INFERENCE = "fast_inference"
    COST_EFFICIENT = "cost_efficient"
    MULTILINGUAL = "multilingual"


class ModelPricing(BaseModel):
    """Token-based pricing per model."""
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    currency: str = "USD"
    free_tier_tokens: int = 0
    notes: str = ""

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        billable_input = max(0, input_tokens - self.free_tier_tokens)
        return (billable_input / 1000 * self.input_cost_per_1k) + (output_tokens / 1000 * self.output_cost_per_1k)


class ModelEntry(BaseModel):
    """A single model definition in the library."""
    model_id: str
    display_name: str
    provider: ModelProvider
    model_name: str  # actual API model identifier
    description: str = ""
    max_tokens: int = 4096
    max_context_window: int = 128000
    default_temperature: float = 0.0
    capabilities: List[ModelCapability] = Field(default_factory=list)
    pricing: ModelPricing = Field(default_factory=ModelPricing)
    is_available: bool = True
    requires_api_key: bool = True
    is_local: bool = False
    added_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ── Built-in Model Catalog ────────────────────────────────────────────────────
# Models are no longer hardcoded. They are populated dynamically when admins
# add LLM provider integrations (e.g. Google Gemini, OpenAI) via the UI.
# The integration flow tests connectivity, discovers available models,
# and lets the admin select which ones to register.
BUILTIN_MODELS: List[ModelEntry] = []


class ModelLibrary:
    """
    Central registry for all LLM models available in Agent Studio.
    Manages built-in models plus user-registered custom models.
    """

    def __init__(self):
        self._models: Dict[str, ModelEntry] = {}
        self._load_builtin()

    def _load_builtin(self) -> None:
        for model in BUILTIN_MODELS:
            self._models[model.model_id] = model

    def register(self, model: ModelEntry) -> None:
        self._models[model.model_id] = model

    def unregister(self, model_id: str) -> bool:
        return self._models.pop(model_id, None) is not None

    def get(self, model_id: str) -> Optional[ModelEntry]:
        return self._models.get(model_id)

    def list_all(self) -> List[ModelEntry]:
        return list(self._models.values())

    def list_by_provider(self, provider: ModelProvider) -> List[ModelEntry]:
        return [m for m in self._models.values() if m.provider == provider]

    def list_by_capability(self, capability: ModelCapability) -> List[ModelEntry]:
        return [m for m in self._models.values() if capability in m.capabilities]

    def list_available(self) -> List[ModelEntry]:
        return [m for m in self._models.values() if m.is_available]

    def list_local(self) -> List[ModelEntry]:
        return [m for m in self._models.values() if m.is_local]

    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> Optional[float]:
        model = self.get(model_id)
        if not model:
            return None
        return model.pricing.estimate_cost(input_tokens, output_tokens)

    def compare_costs(self, input_tokens: int, output_tokens: int) -> List[Dict[str, Any]]:
        """Compare costs across all models for a given token count."""
        results = []
        for model in self.list_available():
            cost = model.pricing.estimate_cost(input_tokens, output_tokens)
            results.append({
                "model_id": model.model_id,
                "display_name": model.display_name,
                "provider": model.provider.value,
                "cost_usd": round(cost, 6),
                "is_local": model.is_local,
            })
        return sorted(results, key=lambda x: x["cost_usd"])

    def to_dict(self) -> List[Dict[str, Any]]:
        return [m.model_dump(mode="json") for m in self._models.values()]
