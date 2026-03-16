"""
Runtime interface abstraction for multi-runtime support.

Provides a unified interface for ONNX Runtime, TFLite, and PyTorch.
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class RuntimeInterface(ABC):
    """Abstract base class for inference runtimes."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Runtime name."""
        pass
    
    @abstractmethod
    def load_model(self, model_path: str, **kwargs) -> None:
        """Load a model from file."""
        pass
    
    @abstractmethod
    def run_inference(self, input_data: np.ndarray) -> np.ndarray:
        """Run inference on input data."""
        pass
    
    @abstractmethod
    def get_input_shape(self) -> List[int]:
        """Get expected input shape."""
        pass
    
    @abstractmethod
    def get_input_dtype(self) -> str:
        """Get expected input data type."""
        pass
    
    def set_threads(self, num_threads: int) -> None:
        """Set number of threads (if supported)."""
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata."""
        return {}
    
    def cleanup(self) -> None:
        """Clean up resources."""
        pass


class ONNXRuntime(RuntimeInterface):
    """ONNX Runtime inference interface."""
    
    def __init__(self):
        self._session = None
        self._input_name = None
        self._input_shape = None
        self._input_dtype = None
        self._num_threads = 4
    
    @property
    def name(self) -> str:
        return "onnx"
    
    def load_model(self, model_path: str, **kwargs) -> None:
        """Load ONNX model."""
        import onnxruntime as ort
        
        # Session options
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = self._num_threads
        sess_options.inter_op_num_threads = self._num_threads
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Create session
        self._session = ort.InferenceSession(
            model_path,
            sess_options,
            providers=['CPUExecutionProvider']
        )
        
        # Get input info
        input_info = self._session.get_inputs()[0]
        self._input_name = input_info.name
        self._input_shape = list(input_info.shape)
        
        # Handle dynamic dimensions
        for i, dim in enumerate(self._input_shape):
            if isinstance(dim, str) or dim is None or dim < 0:
                self._input_shape[i] = 1  # Default to 1 for dynamic dims
        
        # Map ONNX type to numpy dtype
        type_map = {
            'tensor(float)': 'float32',
            'tensor(float16)': 'float16',
            'tensor(int8)': 'int8',
            'tensor(uint8)': 'uint8',
            'tensor(int32)': 'int32',
            'tensor(int64)': 'int64',
        }
        self._input_dtype = type_map.get(input_info.type, 'float32')
    
    def run_inference(self, input_data: np.ndarray) -> np.ndarray:
        """Run ONNX inference."""
        outputs = self._session.run(None, {self._input_name: input_data})
        return outputs[0]
    
    def get_input_shape(self) -> List[int]:
        return self._input_shape or [1, 3, 224, 224]
    
    def get_input_dtype(self) -> str:
        return self._input_dtype or "float32"
    
    def set_threads(self, num_threads: int) -> None:
        self._num_threads = num_threads
        # Note: threads are set at session creation time
    
    def get_model_info(self) -> Dict[str, Any]:
        if not self._session:
            return {}
        
        return {
            "input_name": self._input_name,
            "input_shape": self._input_shape,
            "input_dtype": self._input_dtype,
            "num_inputs": len(self._session.get_inputs()),
            "num_outputs": len(self._session.get_outputs()),
            "providers": self._session.get_providers(),
        }
    
    def cleanup(self) -> None:
        self._session = None


class TFLiteRuntime(RuntimeInterface):
    """TensorFlow Lite inference interface."""
    
    def __init__(self):
        self._interpreter = None
        self._input_details = None
        self._output_details = None
        self._num_threads = 4
    
    @property
    def name(self) -> str:
        return "tflite"
    
    def load_model(self, model_path: str, **kwargs) -> None:
        """Load TFLite model."""
        try:
            import tflite_runtime.interpreter as tflite
        except ImportError:
            import tensorflow.lite as tflite
        
        self._interpreter = tflite.Interpreter(
            model_path=model_path,
            num_threads=self._num_threads
        )
        self._interpreter.allocate_tensors()
        
        self._input_details = self._interpreter.get_input_details()
        self._output_details = self._interpreter.get_output_details()
    
    def run_inference(self, input_data: np.ndarray) -> np.ndarray:
        """Run TFLite inference."""
        self._interpreter.set_tensor(self._input_details[0]['index'], input_data)
        self._interpreter.invoke()
        return self._interpreter.get_tensor(self._output_details[0]['index'])
    
    def get_input_shape(self) -> List[int]:
        if self._input_details:
            return list(self._input_details[0]['shape'])
        return [1, 224, 224, 3]  # TFLite typically uses NHWC
    
    def get_input_dtype(self) -> str:
        if self._input_details:
            dtype = self._input_details[0]['dtype']
            dtype_map = {
                np.float32: 'float32',
                np.float16: 'float16',
                np.int8: 'int8',
                np.uint8: 'uint8',
                np.int32: 'int32',
            }
            return dtype_map.get(dtype, 'float32')
        return "float32"
    
    def set_threads(self, num_threads: int) -> None:
        self._num_threads = num_threads
        # Note: threads are set at interpreter creation time
    
    def get_model_info(self) -> Dict[str, Any]:
        if not self._interpreter:
            return {}
        
        return {
            "input_shape": self.get_input_shape(),
            "input_dtype": self.get_input_dtype(),
            "num_inputs": len(self._input_details) if self._input_details else 0,
            "num_outputs": len(self._output_details) if self._output_details else 0,
        }
    
    def cleanup(self) -> None:
        self._interpreter = None


class PyTorchRuntime(RuntimeInterface):
    """PyTorch inference interface."""
    
    def __init__(self):
        self._model = None
        self._input_shape = [1, 3, 224, 224]
        self._input_dtype = "float32"
        self._num_threads = 4
    
    @property
    def name(self) -> str:
        return "torch"
    
    def load_model(self, model_path: str, **kwargs) -> None:
        """Load PyTorch model."""
        import torch
        
        # Set threads
        torch.set_num_threads(self._num_threads)
        
        # Load model
        self._model = torch.jit.load(model_path, map_location='cpu')
        self._model.eval()
        
        # Get input shape from kwargs or use default
        self._input_shape = kwargs.get('input_shape', [1, 3, 224, 224])
    
    def run_inference(self, input_data: np.ndarray) -> np.ndarray:
        """Run PyTorch inference."""
        import torch
        
        with torch.no_grad():
            input_tensor = torch.from_numpy(input_data)
            output = self._model(input_tensor)
            return output.numpy()
    
    def get_input_shape(self) -> List[int]:
        return self._input_shape
    
    def get_input_dtype(self) -> str:
        return self._input_dtype
    
    def set_threads(self, num_threads: int) -> None:
        self._num_threads = num_threads
        try:
            import torch
            torch.set_num_threads(num_threads)
        except ImportError:
            pass
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "input_shape": self._input_shape,
            "input_dtype": self._input_dtype,
            "framework": "pytorch",
        }
    
    def cleanup(self) -> None:
        self._model = None


def get_runtime(runtime_name: str) -> RuntimeInterface:
    """
    Get a runtime interface by name.
    
    Args:
        runtime_name: Runtime name ("onnx", "tflite", "torch")
        
    Returns:
        RuntimeInterface instance
        
    Raises:
        ValueError: If runtime is not supported or not available
    """
    runtime_name = runtime_name.lower()
    
    if runtime_name == "onnx":
        try:
            import onnxruntime
            return ONNXRuntime()
        except ImportError:
            raise ValueError("ONNX Runtime not installed. Install with: pip install onnxruntime")
    
    elif runtime_name == "tflite":
        try:
            try:
                import tflite_runtime.interpreter
            except ImportError:
                import tensorflow.lite
            return TFLiteRuntime()
        except ImportError:
            raise ValueError("TFLite Runtime not installed. Install with: pip install tflite-runtime")
    
    elif runtime_name in ("torch", "pytorch"):
        try:
            import torch
            return PyTorchRuntime()
        except ImportError:
            raise ValueError("PyTorch not installed. Install with: pip install torch")
    
    else:
        raise ValueError(f"Unknown runtime: {runtime_name}. Supported: onnx, tflite, torch")


def list_available_runtimes() -> List[str]:
    """
    List available inference runtimes.
    
    Returns:
        List of available runtime names
    """
    available = []
    
    try:
        import onnxruntime
        available.append("onnx")
    except ImportError:
        pass
    
    try:
        try:
            import tflite_runtime.interpreter
        except ImportError:
            import tensorflow.lite
        available.append("tflite")
    except ImportError:
        pass
    
    try:
        import torch
        available.append("torch")
    except ImportError:
        pass
    
    return available


def check_runtime_available(runtime_name: str) -> Tuple[bool, str]:
    """
    Check if a runtime is available.
    
    Args:
        runtime_name: Runtime name to check
        
    Returns:
        Tuple of (is_available, version_or_error)
    """
    runtime_name = runtime_name.lower()
    
    if runtime_name == "onnx":
        try:
            import onnxruntime
            return True, onnxruntime.__version__
        except ImportError as e:
            return False, str(e)
    
    elif runtime_name == "tflite":
        try:
            try:
                import tflite_runtime
                return True, getattr(tflite_runtime, '__version__', 'unknown')
            except ImportError:
                import tensorflow
                return True, f"tensorflow {tensorflow.__version__}"
        except ImportError as e:
            return False, str(e)
    
    elif runtime_name in ("torch", "pytorch"):
        try:
            import torch
            return True, torch.__version__
        except ImportError as e:
            return False, str(e)
    
    return False, f"Unknown runtime: {runtime_name}"
