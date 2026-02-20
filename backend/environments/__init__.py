"""Environment Management — Backend-enforced environment model with promotions, approvals, diffs, and env vars."""
from .environment_manager import EnvironmentManager, EnvironmentConfig, PromotionRecord, PromotionStatus

__all__ = ["EnvironmentManager", "EnvironmentConfig", "PromotionRecord", "PromotionStatus"]
