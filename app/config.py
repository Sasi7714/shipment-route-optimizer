"""Environment-controlled feature switches for safe, incremental rollout."""
from dataclasses import dataclass
import os


def _enabled(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class FeatureFlags:
    """Flags are read at process startup; restart after changing environment values."""

    optimization_enabled: bool = True
    pareto_analysis_enabled: bool = True

    @classmethod
    def from_environment(cls) -> "FeatureFlags":
        return cls(
            optimization_enabled=_enabled("ENABLE_OPTIMIZATION", True),
            pareto_analysis_enabled=_enabled("ENABLE_PARETO_ANALYSIS", True),
        )
