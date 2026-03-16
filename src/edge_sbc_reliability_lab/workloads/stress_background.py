"""
Background CPU stress generator for mixed load testing.

Provides controlled background CPU load to simulate resource
contention in realistic deployment scenarios.
"""

import multiprocessing
import os
import signal
import threading
import time
from typing import List, Optional

import psutil


class BackgroundStressor:
    """
    Generates controlled background CPU load.
    
    Uses worker processes to create CPU load while allowing
    the main benchmark to run.
    """
    
    def __init__(
        self,
        target_load_percent: float = 25.0,
        num_workers: Optional[int] = None,
    ):
        """
        Initialize background stressor.
        
        Args:
            target_load_percent: Target CPU load percentage (0-100)
            num_workers: Number of worker processes (default: CPU count - 1)
        """
        self.target_load_percent = min(100, max(0, target_load_percent))
        
        if num_workers is None:
            # Use one less than CPU count to leave room for benchmark
            num_workers = max(1, (psutil.cpu_count() or 4) - 1)
        
        self.num_workers = num_workers
        self._workers: List[multiprocessing.Process] = []
        self._running = False
        self._stop_event: Optional[multiprocessing.Event] = None
    
    def start(self):
        """Start background stress workers."""
        if self._running:
            return
        
        self._stop_event = multiprocessing.Event()
        self._running = True
        
        # Calculate work/sleep ratio for target load
        # Higher load = more work, less sleep
        work_ratio = self.target_load_percent / 100.0
        
        for i in range(self.num_workers):
            worker = multiprocessing.Process(
                target=_stress_worker,
                args=(self._stop_event, work_ratio),
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)
    
    def stop(self):
        """Stop all background stress workers."""
        if not self._running:
            return
        
        self._running = False
        
        if self._stop_event:
            self._stop_event.set()
        
        # Wait for workers to stop
        for worker in self._workers:
            worker.join(timeout=2.0)
            if worker.is_alive():
                worker.terminate()
        
        self._workers = []
        self._stop_event = None
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


def _stress_worker(stop_event: multiprocessing.Event, work_ratio: float):
    """
    Worker process that generates CPU load.
    
    Args:
        stop_event: Event to signal stop
        work_ratio: Ratio of work to total time (0-1)
    """
    # Cycle duration in seconds
    cycle_duration = 0.1
    work_duration = cycle_duration * work_ratio
    sleep_duration = cycle_duration * (1 - work_ratio)
    
    while not stop_event.is_set():
        # Work phase - do CPU-intensive computation
        end_work = time.monotonic() + work_duration
        while time.monotonic() < end_work:
            # Simple CPU-bound work
            _ = sum(i * i for i in range(1000))
        
        # Sleep phase
        if sleep_duration > 0:
            time.sleep(sleep_duration)


def start_cpu_stress(
    target_load_percent: float = 25.0,
    num_workers: Optional[int] = None,
) -> BackgroundStressor:
    """
    Start background CPU stress.
    
    Args:
        target_load_percent: Target CPU load percentage
        num_workers: Number of worker processes
        
    Returns:
        BackgroundStressor instance (call .stop() when done)
    """
    stressor = BackgroundStressor(target_load_percent, num_workers)
    stressor.start()
    return stressor


def stop_cpu_stress(stressor: BackgroundStressor):
    """
    Stop background CPU stress.
    
    Args:
        stressor: BackgroundStressor instance to stop
    """
    stressor.stop()


class MemoryStressor:
    """
    Generates controlled memory pressure.
    
    Allocates memory to simulate memory-constrained scenarios.
    """
    
    def __init__(self, target_mb: int = 512):
        """
        Initialize memory stressor.
        
        Args:
            target_mb: Amount of memory to allocate in MB
        """
        self.target_mb = target_mb
        self._data: Optional[bytes] = None
    
    def start(self):
        """Allocate memory."""
        # Allocate memory as a large byte array
        self._data = bytearray(self.target_mb * 1024 * 1024)
        # Touch the memory to ensure it's actually allocated
        for i in range(0, len(self._data), 4096):
            self._data[i] = 0xFF
    
    def stop(self):
        """Release memory."""
        self._data = None
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


def get_current_system_load() -> dict:
    """
    Get current system load metrics.
    
    Returns:
        Dictionary with CPU and memory load
    """
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "load_avg_1min": os.getloadavg()[0] if hasattr(os, "getloadavg") else 0,
    }
