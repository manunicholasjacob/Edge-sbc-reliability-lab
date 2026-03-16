"""
Core benchmark runner that orchestrates all components.

Provides the main entry point for running complete benchmarks with
thermal monitoring, power proxy, and result generation.
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from edge_sbc_reliability_lab.core.config import ExperimentConfig
from edge_sbc_reliability_lab.core.logging_utils import get_logger, ProgressLogger
from edge_sbc_reliability_lab.core.output import OutputManager, RunPaths, create_manifest
from edge_sbc_reliability_lab.core.statistics import (
    compute_latency_stats,
    compute_drift_metrics,
    compute_stability_score,
)
from edge_sbc_reliability_lab.core.timestamps import TimestampManager, format_duration
from edge_sbc_reliability_lab.inference.common import BenchmarkResult, create_random_input
from edge_sbc_reliability_lab.inference.runtime_interface import get_runtime, list_available_runtimes
from edge_sbc_reliability_lab.platform.system_snapshot import capture_system_snapshot
from edge_sbc_reliability_lab.thermal.temp_logger import TempLogger, get_cpu_temperature
from edge_sbc_reliability_lab.thermal.freq_logger import FreqLogger
from edge_sbc_reliability_lab.thermal.throttle_detector import ThrottleDetector
from edge_sbc_reliability_lab.thermal.drift_analysis import analyze_thermal_drift


class BenchmarkRunner:
    """
    Main benchmark runner that orchestrates all components.
    
    Handles:
    - Model loading and inference
    - Thermal monitoring
    - Frequency monitoring
    - Throttle detection
    - Result generation and saving
    """
    
    def __init__(self, config: ExperimentConfig):
        """
        Initialize benchmark runner.
        
        Args:
            config: Experiment configuration
        """
        self.config = config
        self.logger = get_logger("BenchmarkRunner")
        self.output_manager = OutputManager(config.output_dir)
        
        # Components
        self.temp_logger: Optional[TempLogger] = None
        self.freq_logger: Optional[FreqLogger] = None
        self.throttle_detector: Optional[ThrottleDetector] = None
        self.timestamp_manager: Optional[TimestampManager] = None
        
        # Results
        self.benchmark_result: Optional[BenchmarkResult] = None
        self.run_paths: Optional[RunPaths] = None
        self.warnings: List[str] = []
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the complete benchmark.
        
        Returns:
            Dictionary with benchmark summary and paths to results
        """
        self.logger.info(f"Starting benchmark: {self.config.experiment_name}")
        self.logger.info(f"Runtime: {self.config.runtime}, Model: {self.config.model_name}")
        
        # Initialize timestamp manager
        self.timestamp_manager = TimestampManager()
        start_time_iso = self.timestamp_manager.start_time_iso
        
        # Create output directory
        self.run_paths = self.output_manager.create_run_directory(
            experiment_name=self.config.experiment_name,
            model_name=self.config.model_name,
            runtime=self.config.runtime,
        )
        self.logger.info(f"Output directory: {self.run_paths.run_dir}")
        
        # Capture system snapshot
        self.logger.info("Capturing system snapshot...")
        snapshot = capture_system_snapshot(
            config_hash=self.config.get_config_hash(),
            cooling_note=self.config.cooling_setup_note,
            ambient_note=self.config.ambient_note,
        )
        
        # Pre-run checks
        self._run_pre_checks(snapshot)
        
        # Initialize monitoring
        self._start_monitoring()
        
        # Run benchmark
        try:
            self.benchmark_result = self._run_inference_benchmark()
        except Exception as e:
            self.logger.error(f"Benchmark failed: {e}")
            self.warnings.append(f"Benchmark error: {e}")
            self.benchmark_result = BenchmarkResult(
                runtime=self.config.runtime,
                model_name=self.config.model_name,
                model_path=self.config.model_path,
                batch_size=self.config.batch_size,
                threads=self.config.threads,
                warmup_runs=self.config.warmup_runs,
                measured_runs=self.config.measured_runs,
                sustained_duration_sec=self.config.sustained_duration_sec,
                success=False,
                errors=[str(e)],
            )
        
        # Stop monitoring
        self._stop_monitoring()
        
        # Record end time
        end_time_iso = datetime.now(timezone.utc).isoformat()
        duration_sec = self.timestamp_manager.elapsed_sec()
        
        # Generate summary
        summary = self._generate_summary()
        
        # Save all results
        self._save_results(
            snapshot=snapshot,
            summary=summary,
            start_time=start_time_iso,
            end_time=end_time_iso,
            duration_sec=duration_sec,
        )
        
        self.logger.info(f"Benchmark complete in {format_duration(duration_sec)}")
        self.logger.info(f"Results saved to: {self.run_paths.run_dir}")
        
        return {
            "success": self.benchmark_result.success,
            "run_dir": str(self.run_paths.run_dir),
            "summary": summary,
            "warnings": self.warnings,
            "duration_sec": duration_sec,
        }
    
    def _run_pre_checks(self, snapshot):
        """Run pre-benchmark checks and generate warnings."""
        # Check temperature
        temp = snapshot.cpu_temp_c
        if temp > 70:
            self.warnings.append(f"High starting temperature: {temp:.1f}°C")
        elif temp > 60:
            self.warnings.append(f"Elevated starting temperature: {temp:.1f}°C")
        
        # Check governor
        if snapshot.cpu_governor != "performance":
            self.warnings.append(
                f"CPU governor is '{snapshot.cpu_governor}', not 'performance'. "
                "Results may vary due to frequency scaling."
            )
        
        # Check runtime availability
        available = list_available_runtimes()
        if self.config.runtime not in available:
            raise RuntimeError(
                f"Runtime '{self.config.runtime}' not available. "
                f"Available runtimes: {available}"
            )
        
        # Check model file
        if self.config.model_path:
            model_path = Path(self.config.model_path)
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found: {self.config.model_path}")
    
    def _start_monitoring(self):
        """Start background monitoring threads."""
        if self.config.collect_temperature:
            self.temp_logger = TempLogger(self.config.thermal_sample_interval_sec)
            self.temp_logger.start()
            self.logger.info("Temperature logging started")
        
        if self.config.collect_frequency:
            self.freq_logger = FreqLogger(self.config.thermal_sample_interval_sec)
            self.freq_logger.start()
            self.logger.info("Frequency logging started")
        
        self.throttle_detector = ThrottleDetector()
        self.throttle_detector.capture_start_state()
    
    def _stop_monitoring(self):
        """Stop background monitoring threads."""
        if self.temp_logger:
            self.temp_logger.stop()
        
        if self.freq_logger:
            self.freq_logger.stop()
        
        if self.throttle_detector:
            self.throttle_detector.capture_end_state()
            throttle_warnings = self.throttle_detector.get_warnings()
            self.warnings.extend(throttle_warnings)
    
    def _run_inference_benchmark(self) -> BenchmarkResult:
        """Run the actual inference benchmark."""
        result = BenchmarkResult(
            runtime=self.config.runtime,
            model_name=self.config.model_name,
            model_path=self.config.model_path,
            batch_size=self.config.batch_size,
            threads=self.config.threads,
            warmup_runs=self.config.warmup_runs,
            measured_runs=self.config.measured_runs,
            sustained_duration_sec=self.config.sustained_duration_sec,
        )
        
        # Get runtime
        runtime = get_runtime(self.config.runtime)
        runtime.set_threads(self.config.threads)
        
        # Load model
        self.logger.info(f"Loading model: {self.config.model_path}")
        runtime.load_model(
            self.config.model_path,
            input_shape=self.config.input_shape
        )
        
        # Get input shape
        input_shape = self.config.input_shape or runtime.get_input_shape()
        input_dtype = self.config.input_dtype or runtime.get_input_dtype()
        
        # Adjust batch size
        if input_shape[0] != self.config.batch_size:
            input_shape = [self.config.batch_size] + list(input_shape[1:])
        
        # Create input data
        self.logger.info(f"Input shape: {input_shape}, dtype: {input_dtype}")
        input_data = create_random_input(input_shape, input_dtype, seed=42)
        
        # Warmup
        self.logger.info(f"Running {self.config.warmup_runs} warmup iterations...")
        for _ in range(self.config.warmup_runs):
            runtime.run_inference(input_data)
        
        # Record start time
        result.start_time_ns = time.monotonic_ns()
        
        # Run benchmark
        latencies = []
        timestamps = []
        
        if self.config.sustained_duration_sec > 0:
            # Sustained duration mode
            self.logger.info(
                f"Running sustained benchmark for {self.config.sustained_duration_sec}s..."
            )
            duration_ns = int(self.config.sustained_duration_sec * 1e9)
            run_start = time.monotonic_ns()
            
            progress = ProgressLogger(
                total=int(self.config.sustained_duration_sec),
                logger=self.logger,
                prefix="Sustained run",
                update_interval=10,
            )
            last_progress_sec = 0
            
            while (time.monotonic_ns() - run_start) < duration_ns:
                # Measure inference
                inf_start = time.monotonic_ns()
                runtime.run_inference(input_data)
                inf_end = time.monotonic_ns()
                
                latencies.append(inf_end - inf_start)
                timestamps.append(inf_end - result.start_time_ns)
                
                # Update progress
                elapsed_sec = int((inf_end - run_start) / 1e9)
                if elapsed_sec > last_progress_sec:
                    progress.update(elapsed_sec - last_progress_sec)
                    last_progress_sec = elapsed_sec
                
                # Inter-inference delay
                if self.config.inter_inference_delay_ms > 0:
                    time.sleep(self.config.inter_inference_delay_ms / 1000.0)
            
            progress.finish()
        else:
            # Fixed iteration mode
            self.logger.info(f"Running {self.config.measured_runs} measured iterations...")
            
            progress = ProgressLogger(
                total=self.config.measured_runs,
                logger=self.logger,
                prefix="Benchmark",
                update_interval=10,
            )
            
            for i in range(self.config.measured_runs):
                # Measure inference
                inf_start = time.monotonic_ns()
                runtime.run_inference(input_data)
                inf_end = time.monotonic_ns()
                
                latencies.append(inf_end - inf_start)
                timestamps.append(inf_end - result.start_time_ns)
                
                progress.update(1)
                
                # Inter-inference delay
                if self.config.inter_inference_delay_ms > 0:
                    time.sleep(self.config.inter_inference_delay_ms / 1000.0)
            
            progress.finish()
        
        # Record end time
        result.end_time_ns = time.monotonic_ns()
        result.total_time_ns = result.end_time_ns - result.start_time_ns
        
        # Store results
        result.latencies_ns = latencies
        result.timestamps_ns = timestamps
        result.success = True
        
        # Cleanup
        runtime.cleanup()
        
        self.logger.info(f"Completed {len(latencies)} inferences")
        
        return result
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark summary."""
        summary = {
            "success": self.benchmark_result.success,
            "total_inferences": len(self.benchmark_result.latencies_ns),
            "total_time_sec": self.benchmark_result.total_time_ns / 1e9,
        }
        
        if not self.benchmark_result.success:
            summary["errors"] = self.benchmark_result.errors
            return summary
        
        # Latency statistics
        stats = compute_latency_stats(
            self.benchmark_result.latencies_ns,
            self.benchmark_result.total_time_ns
        )
        summary["latency"] = stats.to_dict()
        
        # Drift metrics
        drift = compute_drift_metrics(
            self.benchmark_result.latencies_ns,
            self.benchmark_result.timestamps_ns,
        )
        summary["drift"] = drift
        
        # Stability score
        summary["stability_score"] = compute_stability_score(stats, drift)
        
        # Thermal summary
        if self.temp_logger:
            summary["thermal"] = self.temp_logger.get_summary()
            
            # Thermal drift analysis
            temp_samples = self.temp_logger.get_current_samples()
            if temp_samples and len(self.benchmark_result.latencies_ns) > 0:
                temps = [s.temp_c for s in temp_samples]
                times = [s.timestamp_sec for s in temp_samples]
                latencies_ms = [l / 1e6 for l in self.benchmark_result.latencies_ns]
                
                thermal_drift = analyze_thermal_drift(latencies_ms, temps, times)
                summary["thermal_drift"] = thermal_drift
        
        # Frequency summary
        if self.freq_logger:
            summary["frequency"] = self.freq_logger.get_summary()
        
        # Throttle summary
        if self.throttle_detector:
            summary["throttling"] = self.throttle_detector.get_summary()
        
        return summary
    
    def _save_results(
        self,
        snapshot,
        summary: Dict[str, Any],
        start_time: str,
        end_time: str,
        duration_sec: float,
    ):
        """Save all results to output directory."""
        # Save config
        self.config.save(self.run_paths.config_path)
        
        # Save system snapshot
        OutputManager.save_json(snapshot.to_dict(), self.run_paths.system_snapshot_path)
        
        # Save latency samples
        if self.config.save_raw_latencies and self.benchmark_result.latencies_ns:
            OutputManager.save_latency_samples(
                self.benchmark_result.latencies_ns,
                self.benchmark_result.timestamps_ns,
                self.run_paths.latency_samples_path,
            )
        
        # Save thermal trace
        if self.temp_logger and self.config.save_thermal_trace:
            self.temp_logger.save_csv(str(self.run_paths.thermal_trace_path))
        
        # Save frequency trace
        if self.freq_logger:
            self.freq_logger.save_csv(str(self.run_paths.frequency_trace_path))
        
        # Save summary
        OutputManager.save_json(summary, self.run_paths.summary_path)
        
        # Save warnings
        OutputManager.save_json({"warnings": self.warnings}, self.run_paths.warnings_path)
        
        # Create and save manifest
        manifest = create_manifest(
            config=self.config.to_dict(),
            system_snapshot=snapshot.to_dict(),
            summary=summary,
            warnings=self.warnings,
            run_paths=self.run_paths,
            start_time=start_time,
            end_time=end_time,
            duration_sec=duration_sec,
        )
        OutputManager.save_json(manifest, self.run_paths.manifest_path)
        
        # Generate plots if requested
        if self.config.generate_plots:
            self._generate_plots()
    
    def _generate_plots(self):
        """Generate visualization plots."""
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            
            # Latency distribution
            if self.benchmark_result.latencies_ns:
                latencies_ms = [l / 1e6 for l in self.benchmark_result.latencies_ns]
                
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.hist(latencies_ms, bins=50, edgecolor='black', alpha=0.7)
                ax.set_xlabel('Latency (ms)')
                ax.set_ylabel('Count')
                ax.set_title(f'Latency Distribution - {self.config.model_name} ({self.config.runtime})')
                ax.grid(True, alpha=0.3)
                
                fig.savefig(
                    self.run_paths.figures_dir / 'latency_distribution.png',
                    dpi=150,
                    bbox_inches='tight'
                )
                plt.close(fig)
                
                # Latency over time
                timestamps_sec = [t / 1e9 for t in self.benchmark_result.timestamps_ns]
                
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(timestamps_sec, latencies_ms, alpha=0.7, linewidth=0.5)
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Latency (ms)')
                ax.set_title(f'Latency Over Time - {self.config.model_name} ({self.config.runtime})')
                ax.grid(True, alpha=0.3)
                
                fig.savefig(
                    self.run_paths.figures_dir / 'latency_over_time.png',
                    dpi=150,
                    bbox_inches='tight'
                )
                plt.close(fig)
            
            # Temperature over time
            if self.temp_logger:
                temp_df = self.temp_logger.to_dataframe()
                if not temp_df.empty:
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(temp_df['timestamp_sec'], temp_df['temp_c'], 'r-', linewidth=1.5)
                    ax.set_xlabel('Time (s)')
                    ax.set_ylabel('Temperature (°C)')
                    ax.set_title(f'CPU Temperature Over Time - {self.config.model_name}')
                    ax.grid(True, alpha=0.3)
                    
                    fig.savefig(
                        self.run_paths.figures_dir / 'temperature_over_time.png',
                        dpi=150,
                        bbox_inches='tight'
                    )
                    plt.close(fig)
            
            self.logger.info("Plots generated successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to generate plots: {e}")
            self.warnings.append(f"Plot generation failed: {e}")


def run_benchmark(config: ExperimentConfig) -> Dict[str, Any]:
    """
    Convenience function to run a benchmark.
    
    Args:
        config: Experiment configuration
        
    Returns:
        Benchmark results dictionary
    """
    runner = BenchmarkRunner(config)
    return runner.run()
