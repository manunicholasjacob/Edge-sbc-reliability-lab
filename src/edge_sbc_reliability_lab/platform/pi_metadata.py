"""
Raspberry Pi specific metadata extraction.

Provides utilities to identify Pi model, revision, and capabilities.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple


# Raspberry Pi revision codes to model names
PI_REVISIONS = {
    # Pi 5
    "c04170": "Raspberry Pi 5 Model B 4GB",
    "d04170": "Raspberry Pi 5 Model B 8GB",
    # Pi 4
    "a03111": "Raspberry Pi 4 Model B 1GB",
    "b03111": "Raspberry Pi 4 Model B 2GB",
    "b03112": "Raspberry Pi 4 Model B 2GB",
    "c03111": "Raspberry Pi 4 Model B 4GB",
    "c03112": "Raspberry Pi 4 Model B 4GB",
    "d03114": "Raspberry Pi 4 Model B 8GB",
    # Pi 400
    "c03130": "Raspberry Pi 400 4GB",
    # Pi 3
    "a02082": "Raspberry Pi 3 Model B 1GB",
    "a22082": "Raspberry Pi 3 Model B 1GB",
    "a32082": "Raspberry Pi 3 Model B 1GB",
    "a020d3": "Raspberry Pi 3 Model B+ 1GB",
    # Pi Zero 2
    "902120": "Raspberry Pi Zero 2 W",
}


def is_raspberry_pi() -> bool:
    """
    Check if running on a Raspberry Pi.
    
    Returns:
        True if running on a Raspberry Pi
    """
    model_path = Path("/proc/device-tree/model")
    if model_path.exists():
        try:
            model = model_path.read_text().lower()
            return "raspberry pi" in model
        except Exception:
            pass
    
    # Check cpuinfo
    try:
        with open("/proc/cpuinfo", "r") as f:
            content = f.read().lower()
            return "raspberry pi" in content or "bcm2" in content
    except Exception:
        pass
    
    return False


def get_pi_model() -> str:
    """
    Get Raspberry Pi model string.
    
    Returns:
        Model string or "Unknown" if not a Pi
    """
    model_path = Path("/proc/device-tree/model")
    if model_path.exists():
        try:
            return model_path.read_text().strip().rstrip('\x00')
        except Exception:
            pass
    
    # Try to get from revision
    revision = get_pi_revision()
    if revision and revision in PI_REVISIONS:
        return PI_REVISIONS[revision]
    
    return "Unknown"


def get_pi_revision() -> str:
    """
    Get Raspberry Pi revision code.
    
    Returns:
        Revision code string or empty string if not available
    """
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Revision"):
                    return line.split(":")[-1].strip()
    except Exception:
        pass
    
    return ""


def get_pi_serial() -> str:
    """
    Get Raspberry Pi serial number.
    
    Returns:
        Serial number or empty string if not available
    """
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.split(":")[-1].strip()
    except Exception:
        pass
    
    return ""


def get_pi_memory_mb() -> int:
    """
    Get Raspberry Pi memory size in MB.
    
    Returns:
        Memory size in MB
    """
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    # Parse "MemTotal:        3884736 kB"
                    parts = line.split()
                    if len(parts) >= 2:
                        kb = int(parts[1])
                        return kb // 1024
    except Exception:
        pass
    
    return 0


def get_pi_firmware_version() -> str:
    """
    Get Raspberry Pi firmware version using vcgencmd.
    
    Returns:
        Firmware version string or empty string if not available
    """
    try:
        result = subprocess.run(
            ["vcgencmd", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    
    return ""


def get_pi_throttling_status() -> Dict[str, bool]:
    """
    Get Raspberry Pi throttling status using vcgencmd.
    
    Returns:
        Dictionary with throttling flags
    """
    status = {
        "under_voltage_detected": False,
        "arm_frequency_capped": False,
        "currently_throttled": False,
        "soft_temp_limit_active": False,
        "under_voltage_occurred": False,
        "arm_frequency_capped_occurred": False,
        "throttling_occurred": False,
        "soft_temp_limit_occurred": False,
    }
    
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse "throttled=0x0" or "throttled=0x50000"
            output = result.stdout.strip()
            match = re.search(r"throttled=0x([0-9a-fA-F]+)", output)
            if match:
                flags = int(match.group(1), 16)
                
                # Current status (bits 0-3)
                status["under_voltage_detected"] = bool(flags & 0x1)
                status["arm_frequency_capped"] = bool(flags & 0x2)
                status["currently_throttled"] = bool(flags & 0x4)
                status["soft_temp_limit_active"] = bool(flags & 0x8)
                
                # Historical status (bits 16-19)
                status["under_voltage_occurred"] = bool(flags & 0x10000)
                status["arm_frequency_capped_occurred"] = bool(flags & 0x20000)
                status["throttling_occurred"] = bool(flags & 0x40000)
                status["soft_temp_limit_occurred"] = bool(flags & 0x80000)
    except Exception:
        pass
    
    return status


def get_pi_voltage(component: str = "core") -> Optional[float]:
    """
    Get Raspberry Pi voltage reading.
    
    Args:
        component: Component to read ("core", "sdram_c", "sdram_i", "sdram_p")
        
    Returns:
        Voltage in volts or None if not available
    """
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_volts", component],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse "volt=1.2000V"
            match = re.search(r"volt=([0-9.]+)V", result.stdout)
            if match:
                return float(match.group(1))
    except Exception:
        pass
    
    return None


def get_pi_clock_speed(component: str = "arm") -> Optional[int]:
    """
    Get Raspberry Pi clock speed.
    
    Args:
        component: Component to read ("arm", "core", "h264", "isp", "v3d", etc.)
        
    Returns:
        Clock speed in Hz or None if not available
    """
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_clock", component],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse "frequency(48)=1800000000"
            match = re.search(r"=(\d+)", result.stdout)
            if match:
                return int(match.group(1))
    except Exception:
        pass
    
    return None


def get_pi_info() -> Dict[str, any]:
    """
    Get comprehensive Raspberry Pi information.
    
    Returns:
        Dictionary with all available Pi information
    """
    return {
        "is_raspberry_pi": is_raspberry_pi(),
        "model": get_pi_model(),
        "revision": get_pi_revision(),
        "serial": get_pi_serial(),
        "memory_mb": get_pi_memory_mb(),
        "firmware_version": get_pi_firmware_version(),
        "throttling_status": get_pi_throttling_status(),
        "core_voltage": get_pi_voltage("core"),
        "arm_clock_hz": get_pi_clock_speed("arm"),
    }
