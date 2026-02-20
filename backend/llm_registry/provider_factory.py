"""
Unified LLM Provider Factory.
Creates LangChain ChatModel instances for any registered provider.
Supports: Google Gemini (Vertex AI), Anthropic Claude, OpenAI GPT, Ollama (local).
"""

from typing import Optional, Type, Any, Dict
from pydantic import BaseModel

from backend.config.settings import settings
from backend.llm_registry.model_library import ModelProvider, ModelEntry, ModelLibrary


class ProviderFactory:
    """
    Factory that creates LangChain ChatModel instances from ModelEntry definitions.
    Follows the same pattern as jaggaer_agents LLMFactory but supports all providers.
    Caches instances by (model_id, temperature, max_tokens) to avoid redundant init.
    """

    def __init__(self, library: Optional[ModelLibrary] = None, langfuse_manager=None):
        self._library = library or ModelLibrary()
        self._langfuse_manager = langfuse_manager
        self._instance_cache: Dict[str, Any] = {}  # key → LLM instance
        self._cache_max = 32

    @property
    def library(self) -> ModelLibrary:
        return self._library

    def create(
        self,
        model_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        structured_output: Optional[Type[BaseModel]] = None,
        credential_data: Optional[Dict[str, Any]] = None,
        langfuse_trace_name: Optional[str] = None,
        langfuse_user_id: Optional[str] = None,
        langfuse_session_id: Optional[str] = None,
        langfuse_tags: Optional[list] = None,
        langfuse_metadata: Optional[dict] = None,
        **kwargs,
    ) -> Any:
        """
        Create a LangChain ChatModel for the given model_id.

        Args:
            model_id: ID from the model library (e.g. 'gemini-2.5-flash', 'claude-sonnet-4')
            temperature: Override default temperature
            max_tokens: Override default max tokens
            structured_output: Optional Pydantic model for structured output
            credential_data: Optional decrypted credential dict (e.g. service account JSON)
            langfuse_trace_name: Optional trace name for Langfuse callback
            langfuse_user_id: Optional user ID for Langfuse trace
            langfuse_session_id: Optional session ID for Langfuse trace
            langfuse_tags: Optional tags for Langfuse trace
            langfuse_metadata: Optional metadata for Langfuse trace
            **kwargs: Additional provider-specific kwargs

        Returns:
            A LangChain BaseChatModel instance
        """
        model = self._library.get(model_id)
        if not model:
            raise ValueError(f"Model '{model_id}' not found in library. "
                             f"Available: {[m.model_id for m in self._library.list_all()]}")

        temp = temperature if temperature is not None else model.default_temperature
        tokens = max_tokens or model.max_tokens

        # Return cached instance when no special per-call overrides
        _cacheable = (not structured_output and not credential_data
                      and not langfuse_trace_name and not kwargs.get("google_api_key"))
        cache_key = f"{model_id}:{temp}:{tokens}"
        if _cacheable and cache_key in self._instance_cache:
            return self._instance_cache[cache_key]

        # Inject Langfuse callback handler if available
        if self._langfuse_manager and self._langfuse_manager.is_ready():
            lf_handler = self._langfuse_manager.get_langchain_handler(
                trace_name=langfuse_trace_name or f"llm-{model_id}",
                user_id=langfuse_user_id,
                session_id=langfuse_session_id,
                tags=langfuse_tags or [model.provider.value, model_id],
                metadata=langfuse_metadata,
            )
            if lf_handler:
                existing_callbacks = kwargs.get("callbacks", [])
                kwargs["callbacks"] = existing_callbacks + [lf_handler]

        if model.provider == ModelProvider.GOOGLE:
            llm = self._create_google(model, temp, tokens, credential_data=credential_data, **kwargs)
        elif model.provider == ModelProvider.ANTHROPIC:
            llm = self._create_anthropic(model, temp, tokens, **kwargs)
        elif model.provider == ModelProvider.OPENAI:
            llm = self._create_openai(model, temp, tokens, **kwargs)
        elif model.provider == ModelProvider.OLLAMA:
            llm = self._create_ollama(model, temp, tokens, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {model.provider}")

        if structured_output:
            return llm.with_structured_output(structured_output)

        # Cache the instance for reuse (evict oldest when full)
        if _cacheable:
            if len(self._instance_cache) >= self._cache_max:
                oldest = next(iter(self._instance_cache))
                del self._instance_cache[oldest]
            self._instance_cache[cache_key] = llm

        return llm

    def _create_google(
        self, model: ModelEntry, temperature: float, max_tokens: int,
        credential_data: Optional[Dict[str, Any]] = None, **kwargs,
    ) -> Any:
        from langchain_google_genai import ChatGoogleGenerativeAI

        extra: Dict[str, Any] = {}

        # If an explicit API key is provided, use it directly (no project/location needed)
        if "google_api_key" in kwargs:
            return ChatGoogleGenerativeAI(
                model=model.model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

        # Fall back to GOOGLE_API_KEY env var (same pattern as Anthropic/OpenAI)
        if settings.google_api_key:
            return ChatGoogleGenerativeAI(
                model=model.model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                google_api_key=settings.google_api_key,
                **kwargs,
            )

        project = settings.gcp_project_id

        if credential_data:
            # Service account JSON uploaded via UI → create Credentials object
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_info(
                credential_data,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            extra["credentials"] = credentials
            project = credential_data.get("project_id", project)

        return ChatGoogleGenerativeAI(
            model=model.model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            project=project,
            location=settings.region,
            **extra,
            **kwargs,
        )

    def _create_anthropic(self, model: ModelEntry, temperature: float, max_tokens: int, **kwargs) -> Any:
        from langchain_anthropic import ChatAnthropic

        api_key = settings.anthropic_api_key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Required for Claude models.")

        return ChatAnthropic(
            model=model.model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            anthropic_api_key=api_key,
            **kwargs,
        )

    def _create_openai(self, model: ModelEntry, temperature: float, max_tokens: int, **kwargs) -> Any:
        from langchain_openai import ChatOpenAI

        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set. Required for OpenAI models.")

        return ChatOpenAI(
            model=model.model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=api_key,
            **kwargs,
        )

    def _create_ollama(self, model: ModelEntry, temperature: float, max_tokens: int, **kwargs) -> Any:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model.model_name,
            temperature=temperature,
            num_predict=max_tokens,
            base_url=settings.ollama_base_url,
            **kwargs,
        )

    def test_model(self, model_id: str, prompt: str = "Say hello in one word.") -> Dict[str, Any]:
        """
        Quick connectivity test for a model. Returns response + metadata.
        """
        import time

        model = self._library.get(model_id)
        if not model:
            return {"success": False, "error": f"Model '{model_id}' not found"}

        try:
            llm = self.create(model_id)
            start = time.time()
            response = llm.invoke(prompt)
            latency_ms = (time.time() - start) * 1000

            content = response.content if hasattr(response, "content") else str(response)
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

            return {
                "success": True,
                "model_id": model_id,
                "provider": model.provider.value,
                "response": content[:200],
                "latency_ms": round(latency_ms, 1),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost": model.pricing.estimate_cost(input_tokens, output_tokens),
            }
        except Exception as e:
            return {
                "success": False,
                "model_id": model_id,
                "provider": model.provider.value,
                "error": str(e),
            }

    def list_available_providers(self) -> Dict[str, bool]:
        """Check which providers have valid credentials configured."""
        return {
            "google": True,  # uses ADC, always potentially available
            "anthropic": bool(settings.anthropic_api_key),
            "openai": bool(settings.openai_api_key),
            "ollama": True,  # local, always potentially available
        }
