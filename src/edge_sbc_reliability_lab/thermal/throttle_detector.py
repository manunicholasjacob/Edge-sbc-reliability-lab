"""
Throttling detection for Raspberry Pi.

Detects thermal throttling, frequency capping, and under-voltage conditions.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


@dataclass
class ThrottleEvent:
    """A detected throttling event."""
    timestamp_sec: float
    event_type: str  # "thermal", "frequency_cap", "under_voltage"
    severity: str  # "warning", "critical"
    details: str


@dataclass
class ThrottleStatus:
    """Current throttling status."""
    under_voltage_now: bool = False
    freq_capped_now: bool = False
    throttled_now: bool = False
    soft_temp_limit_now: bool = False
    under_voltage_occurred: bool = False
    freq_capped_occurred: bool = False
    throttled_occurred: bool = False
    soft_temp_limit_occurred: bool = False
    raw_flags: int = 0


def get_throttle_status() -> ThrottleStatus:
    """
    Get current throttling status from vcgencmd.
    
    Returns:
        ThrottleStatus with all flags
    """
    status = ThrottleStatus()
    
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            # Parse "throttled=0x0" or "throttled=0x50000"
            match = re.search(r"throttled=0x([0-9a-fA-F]+)", result.stdout)
            if match:
                flags = int(match.group(1), 16)
                status.raw_flags = flags
                
                # Current status (bits 0-3)
                status.under_voltage_now = bool(flags & 0x1)
                status.freq_capped_now = bool(flags & 0x2)
                status.throttled_now = bool(flags & 0x4)
                status.soft_temp_limit_now = bool(flags & 0x8)
                
                # Historical status (bits 16-19)
                status.under_voltage_occurred = bool(flags & 0x10000)
                status.freq_capped_occurred = bool(flags & 0x20000)
                status.throttled_occurred = bool(flags & 0x40000)
                status.soft_temp_limit_occurred = bool(flags & 0x80000)
    except Exception:
        pass
    
    return status


def detect_throttling() -> Tuple[bool, List[str]]:
    """
    Detect if any throttling is currently active.
    
    Returns:
        Tuple of (is_throttled, list_of_reasons)
    """
    status = get_throttle_status()
    reasons = []
    
    if status.under_voltage_now:
        reasons.append("Under-voltage detected - check power supply")
    if status.freq_capped_now:
        reasons.append("ARM frequency capped")
    if status.throttled_now:
        reasons.append("Currently throttled")
    if status.soft_temp_limit_now:
        reasons.append("Soft temperature limit active")
    
    return len(reasons) > 0, reasons


def check_throttle_history() -> Tuple[bool, List[str]]:
    """
    Check if any throttling has occurred since boot.
    
    Returns:
        Tuple of (throttling_occurred, list_of_events)
    """
    status = get_throttle_status()
    events = []
    
    if status.under_voltage_occurred:
        events.append("Under-voltage has occurred since boot")
    if status.freq_capped_occurred:
        events.append("ARM frequency capping has occurred since boot")
    if status.throttled_occurred:
        events.append("Throttling has occurred since boot")
    if status.soft_temp_limit_occurred:
        events.append("Soft temperature limit has been reached since boot")
    
    return len(events) > 0, events


class ThrottleDetector:
    """
    Continuous throttle monitoring during benchmark runs.
    
    Tracks throttling events and their timing for correlation
    with performance measurements.
    """
    
    def __init__(self):
        """Initialize throttle detector."""
        self.events: List[ThrottleEvent] = []
        self._start_status: Optional[ThrottleStatus] = None
        self._end_status: Optional[ThrottleStatus] = None
    
    def capture_start_state(self):
        """Capture throttle state at benchmark start."""
        self._start_status = get_throttle_status()
    
    def capture_end_state(self):
        """Capture throttle state at benchmark end."""
        self._end_status = get_throttle_status()
    
    def check_and_record(self, timestamp_sec: float):
        """
        Check current throttle status and record any events.
        
        Args:
            timestamp_sec: Current timestamp in seconds since benchmark start
        """
        status = get_throttle_status()
        
        if status.under_voltage_now:
            self.events.append(ThrottleEvent(
                timestamp_sec=timestamp_sec,
                event_type="under_voltage",
                severity="critical",
                details="Under-voltage detected"
            ))
        
        if status.throttled_now:
            self.events.append(ThrottleEvent(
                timestamp_sec=timestamp_sec,
                event_type="thermal",
                severity="critical",
                details="Thermal throttling active"
            ))
        
        if status.freq_capped_now:
            self.events.append(ThrottleEvent(
                timestamp_sec=timestamp_sec,
                event_type="frequency_cap",
                severity="warning",
                details="Frequency capped"
            ))
        
        if status.soft_temp_limit_now:
            self.events.append(ThrottleEvent(
                timestamp_sec=timestamp_sec,
                event_type="thermal",
                severity="warning",
                details="Soft temperature limit active"
            ))
    
    def get_summary(self) -> Dict:
        """
        Get summary of throttling during benchmark.
        
        Returns:
            Dictionary with throttle summary
        """
        summary = {
            "throttle_events_count": len(self.events),
            "throttle_detected": len(self.events) > 0,
            "event_types": list(set(e.event_type for e in self.events)),
            "critical_events": sum(1 for e in self.events if e.severity == "critical"),
            "warning_events": sum(1 for e in self.events if e.severity == "warning"),
        }
        
        # Check if throttling occurred during run (not before)
        if self._start_status and self._end_status:
            summary["new_throttle_during_run"] = (
                not self._start_status.throttled_occurred and
                self._end_status.throttled_occurred
            )
            summary["new_undervoltage_during_run"] = (
                not self._start_status.under_voltage_occurred and
                self._end_status.under_voltage_occurred
            )
        
        return summary
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert events to DataFrame."""
        if not self.events:
            return pd.DataFrame(columns=["timestamp_sec", "event_type", "severity", "details"])
        
        return pd.DataFrame([
            {
                "timestamp_sec": e.timestamp_sec,
                "event_type": e.event_type,
                "severity": e.severity,
                "details": e.details,
            }
            for e in self.events
        ])
    
    def get_warnings(self) -> List[str]:
        """
        Get warning messages about throttling.
        
        Returns:
            List of warning strings
        """
        warnings = []
        
        summary = self.get_summary()
        
        if summary["critical_events"] > 0:
            warnings.append(
                f"CRITICAL: {summary['critical_events']} critical throttle events detected"
            )
        
        if summary.get("new_throttle_during_run"):
            warnings.append(
                "WARNING: Thermal throttling occurred during benchmark - results may be affected"
            )
        
        if summary.get("new_undervoltage_during_run"):
            warnings.append(
                "WARNING: Under-voltage detected during benchmark - check power supply"
            )
        
        if "thermal" in summary["event_types"]:
            warnings.append(
                "WARNING: Thermal events detected - consider improved cooling"
            )
        
        return warnings
