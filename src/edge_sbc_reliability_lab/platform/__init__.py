"""Platform and environment capture module."""

from edge_sbc_reliability_lab.platform.system_snapshot import (
    SystemSnapshot,
    capture_system_snapshot,
)
from edge_sbc_reliability_lab.platform.governor_check import (
    get_cpu_governor,
    check_governor_consistency,
    get_governor_recommendation,
)
from edge_sbc_reliability_lab.platform.pi_metadata import (
    is_raspberry_pi,
    get_pi_model,
    get_pi_info,
    get_pi_throttling_status,
)
from edge_sbc_reliability_lab.platform.environment_capture import (
    capture_environment_variables,
    capture_full_environment,
    check_background_interference,
)

__all__ = [
    "SystemSnapshot",
    "capture_system_snapshot",
    "get_cpu_governor",
    "check_governor_consistency",
    "get_governor_recommendation",
    "is_raspberry_pi",
    "get_pi_model",
    "get_pi_info",
    "get_pi_throttling_status",
    "capture_environment_variables",
    "capture_full_environment",
    "check_background_interference",
]
