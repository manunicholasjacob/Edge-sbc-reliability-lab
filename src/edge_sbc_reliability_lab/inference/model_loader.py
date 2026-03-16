"""
Model loading utilities.

Provides functions to load and validate models for different runtimes.
"""

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np


def get_model_hash(model_path: str, algorithm: str = "sha256") -> str:
    """
    Compute hash of model file for reproducibility tracking.
    
    Args:
        model_path: Path to model file
        algorithm: Hash algorithm (sha256, md5)
        
    Returns:
        Hex digest of model hash (first 16 characters)
    """
    hash_func = hashlib.new(algorithm)
    
    with open(model_path, "rb") as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()[:16]


def get_model_size_mb(model_path: str) -> float:
    """
    Get model file size in megabytes.
    
    Args:
        model_path: Path to model file
        
    Returns:
        File size in MB
    """
    return os.path.getsize(model_path) / (1024 * 1024)


def detect_model_runtime(model_path: str) -> str:
    """
    Detect appropriate runtime from model file extension.
    
    Args:
        model_path: Path to model file
        
    Returns:
        Runtime name ("onnx", "tflite", "torch")
        
    Raises:
        ValueError: If extension is not recognized
    """
    ext = Path(model_path).suffix.lower()
    
    extension_map = {
        ".onnx": "onnx",
        ".tflite": "tflite",
        ".pt": "torch",
        ".pth": "torch",
    }
    
    if ext not in extension_map:
        raise ValueError(f"Unknown model extension: {ext}")
    
    return extension_map[ext]


def validate_model_file(model_path: str) -> Tuple[bool, str]:
    """
    Validate that a model file exists and is readable.
    
    Args:
        model_path: Path to model file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(model_path)
    
    if not path.exists():
        return False, f"Model file not found: {model_path}"
    
    if not path.is_file():
        return False, f"Path is not a file: {model_path}"
    
    if path.stat().st_size == 0:
        return False, f"Model file is empty: {model_path}"
    
    # Try to read first few bytes
    try:
        with open(path, "rb") as f:
            f.read(1024)
    except Exception as e:
        return False, f"Cannot read model file: {e}"
    
    return True, ""


def get_model_metadata(model_path: str) -> Dict[str, Any]:
    """
    Get metadata about a model file.
    
    Args:
        model_path: Path to model file
        
    Returns:
        Dictionary with model metadata
    """
    path = Path(model_path)
    
    metadata = {
        "path": str(path.resolve()),
        "filename": path.name,
        "extension": path.suffix,
        "size_mb": get_model_size_mb(model_path),
        "hash": get_model_hash(model_path),
        "runtime": detect_model_runtime(model_path),
    }
    
    return metadata


def create_dummy_onnx_model(
    output_path: str,
    input_shape: Tuple[int, ...] = (1, 3, 224, 224),
    input_name: str = "input",
    output_name: str = "output",
) -> str:
    """
    Create a minimal dummy ONNX model for testing.
    
    Args:
        output_path: Path to save the model
        input_shape: Input tensor shape
        input_name: Name of input tensor
        output_name: Name of output tensor
        
    Returns:
        Path to created model
    """
    try:
        import onnx
        from onnx import TensorProto, helper
    except ImportError:
        raise ImportError("onnx package required to create dummy models")
    
    # Create a simple identity-like model
    X = helper.make_tensor_value_info(input_name, TensorProto.FLOAT, list(input_shape))
    Y = helper.make_tensor_value_info(output_name, TensorProto.FLOAT, list(input_shape))
    
    # Identity node
    node = helper.make_node(
        'Identity',
        inputs=[input_name],
        outputs=[output_name],
    )
    
    graph = helper.make_graph(
        [node],
        'dummy_model',
        [X],
        [Y],
    )
    
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 11)])
    model.ir_version = 6  # Compatible with older ONNX Runtime versions
    
    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, output_path)
    
    return output_path


def create_dummy_tflite_model(
    output_path: str,
    input_shape: Tuple[int, ...] = (1, 224, 224, 3),
) -> str:
    """
    Create a minimal dummy TFLite model for testing.
    
    Args:
        output_path: Path to save the model
        input_shape: Input tensor shape (NHWC format)
        
    Returns:
        Path to created model
    """
    try:
        import tensorflow as tf
    except ImportError:
        raise ImportError("tensorflow package required to create dummy TFLite models")
    
    # Create a simple model
    model = tf.keras.Sequential([
        tf.keras.layers.InputLayer(input_shape=input_shape[1:]),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(10),
    ])
    
    # Convert to TFLite
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    
    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    return output_path


def download_sample_model(
    model_name: str,
    output_dir: str = "models",
    runtime: str = "onnx",
) -> Optional[str]:
    """
    Download a sample model for testing.
    
    This is a placeholder - in production, this would download from
    a model zoo or create appropriate test models.
    
    Args:
        model_name: Name of model to download
        output_dir: Directory to save model
        runtime: Target runtime
        
    Returns:
        Path to downloaded model, or None if not available
    """
    # For now, return None - models should be provided by user
    # or created with create_dummy_* functions
    return None
