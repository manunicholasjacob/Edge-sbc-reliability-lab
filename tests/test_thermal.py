"""Tests for thermal module functionality."""

import time
import pytest

from edge_sbc_reliability_lab.thermal.temp_logger import TempLogger, get_cpu_temperature
from edge_sbc_reliability_lab.thermal.freq_logger import FreqLogger, get_cpu_frequency
from edge_sbc_reliability_lab.thermal.drift_analysis import (
    analyze_thermal_drift,
    compute_latency_temp_correlation,
    compute_thermal_impact_score,
)


class TestTempLogger:
    """Tests for temperature logger."""
    
    def test_get_cpu_temperature(self):
        """Test getting CPU temperature."""
        temp = get_cpu_temperature()
        
        # Should return a float (may be 0 if not on Pi)
        assert isinstance(temp, float)
        assert temp >= 0
    
    def test_temp_logger_basic(self):
        """Test basic temperature logger functionality."""
        logger = TempLogger(sample_interval_sec=0.1)
        
        logger.start()
        time.sleep(0.3)  # Let it collect a few samples
        samples = logger.stop()
        
        # Should have collected some samples
        assert len(samples) >= 1
        
        # Check sample structure
        if samples:
            sample = samples[0]
            assert hasattr(sample, 'timestamp_ns')
            assert hasattr(sample, 'temp_c')
    
    def test_temp_logger_summary(self):
        """Test temperature logger summary."""
        logger = TempLogger(sample_interval_sec=0.1)
        
        logger.start()
        time.sleep(0.3)
        logger.stop()
        
        summary = logger.get_summary()
        
        assert "min_c" in summary
        assert "max_c" in summary
        assert "mean_c" in summary
        assert "sample_count" in summary


class TestFreqLogger:
    """Tests for frequency logger."""
    
    def test_get_cpu_frequency(self):
        """Test getting CPU frequency."""
        freq = get_cpu_frequency()
        
        # Should return a float (may be 0 if not on Pi)
        assert isinstance(freq, float)
        assert freq >= 0
    
    def test_freq_logger_basic(self):
        """Test basic frequency logger functionality."""
        logger = FreqLogger(sample_interval_sec=0.1)
        
        logger.start()
        time.sleep(0.3)
        samples = logger.stop()
        
        assert len(samples) >= 1


class TestDriftAnalysis:
    """Tests for drift analysis functions."""
    
    def test_analyze_thermal_drift(self):
        """Test thermal drift analysis."""
        # Create sample data
        latencies_ms = [10.0 + i * 0.01 for i in range(100)]
        temperatures_c = [50.0 + i * 0.1 for i in range(100)]
        timestamps_sec = [i * 0.1 for i in range(100)]
        
        result = analyze_thermal_drift(latencies_ms, temperatures_c, timestamps_sec)
        
        assert "temp_rise_c" in result
        assert "latency_drift_pct" in result
        assert "correlation" in result
        assert result["temp_rise_c"] > 0
    
    def test_analyze_thermal_drift_insufficient_data(self):
        """Test drift analysis with insufficient data."""
        result = analyze_thermal_drift([10.0], [50.0], [0.0])
        
        # Should return zeros for insufficient data
        assert result["temp_rise_c"] == 0.0
    
    def test_compute_thermal_impact_score(self):
        """Test thermal impact score computation."""
        drift_analysis = {
            "temp_rise_c": 10.0,
            "latency_drift_pct": 5.0,
            "correlation": 0.5,
        }
        
        score = compute_thermal_impact_score(drift_analysis)
        
        assert 0 <= score <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
