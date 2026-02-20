from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass(frozen=True)
class ModelInfo:
    id: str
    name: str
    api_model: str
    context_window: int
    default_max_tokens: int
    supports_streaming: bool = True
    supports_vision: bool = False
    can_reason: bool = False


@dataclass
class ProviderInfo:
    id: str
    name: str
    env_key: str
    sort_order: int
    models: list[ModelInfo] = field(default_factory=list)

    @property
    def is_available(self) -> bool:
        if self.id == "antigravity":
            if os.getenv("ANTIGRAVITY_REFRESH_TOKEN"):
                return True
            opencode_path = os.path.expanduser("~/.config/opencode/antigravity-accounts.json")
            if os.path.exists(opencode_path):
                return True
            return False
            
        if self.env_key == "":
            return True
        return os.getenv(self.env_key) is not None


# ---------------------------------------------------------------------------
# Provider 1: Copilot
# ---------------------------------------------------------------------------
_COPILOT_PROVIDER = ProviderInfo(
    id="copilot",
    name="Copilot",
    env_key="",
    sort_order=1,
    models=[
        ModelInfo(id="gpt-4o", name="GPT-4o", api_model="gpt-4o", context_window=128000, default_max_tokens=4096, supports_vision=True),
        ModelInfo(id="gpt-4o-mini", name="GPT-4o mini", api_model="gpt-4o-mini", context_window=128000, default_max_tokens=4096),
        ModelInfo(id="o1", name="o1", api_model="o1", context_window=200000, default_max_tokens=8192, can_reason=True),
        ModelInfo(id="o1-mini", name="o1 mini", api_model="o1-mini", context_window=128000, default_max_tokens=4096, can_reason=True),
        ModelInfo(id="o3-mini", name="o3 mini", api_model="o3-mini", context_window=200000, default_max_tokens=8192, can_reason=True),
        ModelInfo(id="claude-sonnet-4-5", name="Claude Sonnet 4.5 (Copilot)", api_model="claude-sonnet-4-5", context_window=200000, default_max_tokens=4096),
    ],
)

# ---------------------------------------------------------------------------
# Provider 2: Anthropic
# ---------------------------------------------------------------------------
_ANTHROPIC_PROVIDER = ProviderInfo(
    id="anthropic",
    name="Anthropic",
    env_key="ANTHROPIC_API_KEY",
    sort_order=2,
    models=[
        ModelInfo(id="claude-opus-4", name="Claude Opus 4", api_model="claude-opus-4-20250514", context_window=200000, default_max_tokens=4096, can_reason=True),
        ModelInfo(id="claude-sonnet-4", name="Claude Sonnet 4", api_model="claude-sonnet-4-20250514", context_window=200000, default_max_tokens=4096),
        ModelInfo(id="claude-haiku-3-5", name="Claude Haiku 3.5", api_model="claude-haiku-3-5-20241022", context_window=200000, default_max_tokens=4096),
    ],
)

# ---------------------------------------------------------------------------
# Provider 3: NVIDIA NIM
# ---------------------------------------------------------------------------
_NVIDIA_PROVIDER = ProviderInfo(
    id="nvidia",
    name="NVIDIA NIM",
    env_key="NVIDIA_API_KEY",
    sort_order=3,
    models=[
        ModelInfo(id="kimi-k2", name="Kimi K2", api_model="moonshotai/kimi-k2-instruct", context_window=131072, default_max_tokens=4096),
    ],
)

# ---------------------------------------------------------------------------
# Provider 4: Groq
# ---------------------------------------------------------------------------
_GROQ_PROVIDER = ProviderInfo(
    id="groq",
    name="Groq",
    env_key="GROQ_API_KEY",
    sort_order=4,
    models=[
        ModelInfo(id="llama-3.3-70b", name="Llama 3.3 70B", api_model="llama-3.3-70b-versatile", context_window=128000, default_max_tokens=4096),
        ModelInfo(id="llama-3.1-8b", name="Llama 3.1 8B", api_model="llama-3.1-8b-instant", context_window=128000, default_max_tokens=4096),
        ModelInfo(id="mixtral-8x7b", name="Mixtral 8x7B", api_model="mixtral-8x7b-32768", context_window=32768, default_max_tokens=4096),
    ],
)

# ---------------------------------------------------------------------------
# Provider 5: Google Gemini
# ---------------------------------------------------------------------------
_GEMINI_PROVIDER = ProviderInfo(
    id="gemini",
    name="Google Gemini",
    env_key="GEMINI_API_KEY",
    sort_order=5,
    models=[
        ModelInfo(id="gemini-2.5-flash", name="Gemini 2.5 Flash", api_model="gemini-2.5-flash-preview-05-20", context_window=1000000, default_max_tokens=4096),
        ModelInfo(id="gemini-2.5-pro", name="Gemini 2.5 Pro", api_model="gemini-2.5-pro-preview-06-05", context_window=1000000, default_max_tokens=4096, can_reason=True),
    ],
)

# ---------------------------------------------------------------------------
# Provider 6: Mistral
# ---------------------------------------------------------------------------
_MISTRAL_PROVIDER = ProviderInfo(
    id="mistral",
    name="Mistral",
    env_key="MISTRAL_API_KEY",
    sort_order=6,
    models=[
        ModelInfo(id="mistral-large", name="Mistral Large", api_model="mistral-large-latest", context_window=128000, default_max_tokens=4096),
        ModelInfo(id="mistral-small", name="Mistral Small", api_model="mistral-small-latest", context_window=32000, default_max_tokens=4096),
    ],
)

# ---------------------------------------------------------------------------
# Provider 7: OpenRouter
# ---------------------------------------------------------------------------
_OPENROUTER_PROVIDER = ProviderInfo(
    id="openrouter",
    name="OpenRouter",
    env_key="OPENROUTER_API_KEY",
    sort_order=7,
    models=[
        ModelInfo(id="deepseek-r1", name="DeepSeek R1", api_model="deepseek/deepseek-r1", context_window=64000, default_max_tokens=4096, can_reason=True),
        ModelInfo(id="qwen-2.5-72b", name="Qwen 2.5 72B", api_model="qwen/qwen-2.5-72b-instruct", context_window=131072, default_max_tokens=4096),
        ModelInfo(id="llama-3.1-405b", name="Llama 3.1 405B", api_model="meta-llama/llama-3.1-405b-instruct", context_window=131072, default_max_tokens=4096),
        ModelInfo(id="gemma-3-27b", name="Gemma 3 27B", api_model="google/gemma-3-27b-it", context_window=131072, default_max_tokens=4096),
    ],
)

# ---------------------------------------------------------------------------
# Provider 8: Antigravity (Google IDE)
# ---------------------------------------------------------------------------
_ANTIGRAVITY_PROVIDER = ProviderInfo(
    id="antigravity",
    name="Antigravity",
    env_key="ANTIGRAVITY_REFRESH_TOKEN",
    sort_order=8,
    models=[
        ModelInfo(
            id="ag-gemini-3-flash",
            name="Gemini 3 Flash (Antigravity)",
            api_model="gemini-3-flash",
            context_window=1048576,
            default_max_tokens=4096,
        ),
        ModelInfo(
            id="ag-gemini-3-pro",
            name="Gemini 3 Pro (Antigravity)",
            api_model="gemini-3-pro",
            context_window=1048576,
            default_max_tokens=4096,
            can_reason=True,
        ),
        ModelInfo(
            id="ag-claude-sonnet-4-6",
            name="Claude Sonnet 4.6 (Antigravity)",
            api_model="claude-sonnet-4-6",
            context_window=200000,
            default_max_tokens=4096,
        ),
        ModelInfo(
            id="ag-claude-opus-4-6",
            name="Claude Opus 4.6 Thinking (Antigravity)",
            api_model="claude-opus-4-6-thinking",
            context_window=200000,
            default_max_tokens=4096,
            can_reason=True,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Global registries
# ---------------------------------------------------------------------------
SUPPORTED_MODELS: dict[str, ModelInfo] = {}
PROVIDER_REGISTRY: dict[str, ProviderInfo] = {}

_ALL_PROVIDERS = [
    _COPILOT_PROVIDER,
    _ANTHROPIC_PROVIDER,
    _NVIDIA_PROVIDER,
    _GROQ_PROVIDER,
    _GEMINI_PROVIDER,
    _MISTRAL_PROVIDER,
    _OPENROUTER_PROVIDER,
    _ANTIGRAVITY_PROVIDER,
]

for _p in _ALL_PROVIDERS:
    PROVIDER_REGISTRY[_p.id] = _p
    for _m in _p.models:
        SUPPORTED_MODELS[_m.id] = _m


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def get_available_providers() -> list[ProviderInfo]:
    """Return providers sorted by sort_order where is_available is True."""
    return sorted(
        [p for p in PROVIDER_REGISTRY.values() if p.is_available],
        key=lambda p: p.sort_order,
    )


def get_models_for_provider(provider_id: str) -> list[ModelInfo]:
    """Return models for a given provider id, empty list if not found."""
    provider = PROVIDER_REGISTRY.get(provider_id)
    return provider.models if provider else []


def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """Return ModelInfo for a model id, None if not found."""
    return SUPPORTED_MODELS.get(model_id)
