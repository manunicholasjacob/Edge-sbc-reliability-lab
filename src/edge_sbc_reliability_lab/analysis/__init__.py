"""Analysis and reporting module."""

from edge_sbc_reliability_lab.analysis.summarize_results import (
    summarize_run,
    summarize_multiple_runs,
    generate_summary_report,
)
from edge_sbc_reliability_lab.analysis.runtime_comparison import (
    compare_runtimes,
    generate_comparison_table,
)
from edge_sbc_reliability_lab.analysis.latency_vs_temp import (
    analyze_latency_temperature,
    plot_latency_vs_temp,
    compute_thermal_sensitivity,
)
from edge_sbc_reliability_lab.analysis.sustained_drift import (
    analyze_sustained_drift,
    plot_drift_over_time,
    compute_stability_metrics,
)
from edge_sbc_reliability_lab.analysis.reliability_summary import (
    compute_reliability_report,
    generate_reliability_score,
    generate_reliability_table,
)
from edge_sbc_reliability_lab.analysis.fairness_checker import (
    check_fairness,
    generate_fairness_report,
)
from edge_sbc_reliability_lab.analysis.compare_runs import (
    compare_runs,
    generate_comparison_markdown,
)
from edge_sbc_reliability_lab.analysis.build_leaderboard import (
    build_leaderboard,
    generate_leaderboard_report,
)

__all__ = [
    "summarize_run",
    "summarize_multiple_runs",
    "generate_summary_report",
    "compare_runtimes",
    "generate_comparison_table",
    "analyze_latency_temperature",
    "plot_latency_vs_temp",
    "compute_thermal_sensitivity",
    "analyze_sustained_drift",
    "plot_drift_over_time",
    "compute_stability_metrics",
    "compute_reliability_report",
    "generate_reliability_score",
    "generate_reliability_table",
    "check_fairness",
    "generate_fairness_report",
    "compare_runs",
    "generate_comparison_markdown",
    "build_leaderboard",
    "generate_leaderboard_report",
]
