"""Tests for inference module functionality."""

import numpy as np
import pytest

from edge_sbc_reliability_lab.inference.common import (
    create_random_input,
    BenchmarkResult,
    InferenceResult,
)
from edge_sbc_reliability_lab.inference.runtime_interface import (
    list_available_runtimes,
    check_runtime_available,
)


class TestCommon:
    """Tests for common inference utilities."""
    
    def test_create_random_input_float32(self):
        """Test creating float32 random input."""
        shape = [1, 3, 224, 224]
        input_data = create_random_input(shape, "float32")
        
        assert input_data.shape == tuple(shape)
        assert input_data.dtype == np.float32
        assert 0 <= input_data.min() <= input_data.max() <= 1
    
    def test_create_random_input_uint8(self):
        """Test creating uint8 random input."""
        shape = [1, 224, 224, 3]
        input_data = create_random_input(shape, "uint8")
        
        assert input_data.shape == tuple(shape)
        assert input_data.dtype == np.uint8
        assert 0 <= input_data.min() <= input_data.max() <= 255
    
    def test_create_random_input_reproducible(self):
        """Test that seeded input is reproducible."""
        shape = [1, 3, 224, 224]
        
        input1 = create_random_input(shape, "float32", seed=42)
        input2 = create_random_input(shape, "float32", seed=42)
        
        np.testing.assert_array_equal(input1, input2)
    
    def test_benchmark_result(self):
        """Test BenchmarkResult dataclass."""
        result = BenchmarkResult(
            runtime="onnx",
            model_name="test_model",
            model_path="model.onnx",
            batch_size=1,
            threads=4,
            warmup_runs=10,
            measured_runs=100,
            sustained_duration_sec=0,
        )
        
        assert result.runtime == "onnx"
        assert result.success == True
        assert len(result.latencies_ns) == 0
        
        # Test to_dict
        d = result.to_dict()
        assert d["runtime"] == "onnx"
        assert d["model_name"] == "test_model"


class TestRuntimeInterface:
    """Tests for runtime interface."""
    
    def test_list_available_runtimes(self):
        """Test listing available runtimes."""
        runtimes = list_available_runtimes()
        
        assert isinstance(runtimes, list)
        # At least one runtime should be available in test environment
        # (may be empty if no runtimes installed)
    
    def test_check_runtime_available(self):
        """Test checking runtime availability."""
        # Check ONNX (may or may not be installed)
        available, version = check_runtime_available("onnx")
        assert isinstance(available, bool)
        assert isinstance(version, str)
        
        # Check unknown runtime
        available, version = check_runtime_available("unknown_runtime")
        assert available == False


class TestRuntimeIntegration:
    """Integration tests for runtimes (require actual runtimes installed)."""
    
    @pytest.mark.skipif(
        "onnx" not in list_available_runtimes(),
        reason="ONNX Runtime not installed"
    )
    def test_onnx_runtime_interface(self):
        """Test ONNX Runtime interface."""
        from edge_sbc_reliability_lab.inference.runtime_interface import ONNXRuntime
        
        runtime = ONNXRuntime()
        assert runtime.name == "onnx"
    
    @pytest.mark.skipif(
        "tflite" not in list_available_runtimes(),
        reason="TFLite Runtime not installed"
    )
    def test_tflite_runtime_interface(self):
        """Test TFLite Runtime interface."""
        from edge_sbc_reliability_lab.inference.runtime_interface import TFLiteRuntime
        
        runtime = TFLiteRuntime()
        assert runtime.name == "tflite"
    
    @pytest.mark.skipif(
        "torch" not in list_available_runtimes(),
        reason="PyTorch not installed"
    )
    def test_torch_runtime_interface(self):
        """Test PyTorch Runtime interface."""
        from edge_sbc_reliability_lab.inference.runtime_interface import PyTorchRuntime
        
        runtime = PyTorchRuntime()
        assert runtime.name == "torch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
