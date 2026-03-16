#!/usr/bin/env python3
"""Create a test ONNX model for validation."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from edge_sbc_reliability_lab.inference.model_loader import create_dummy_onnx_model

os.makedirs('models', exist_ok=True)
create_dummy_onnx_model('models/test_model.onnx', input_shape=(1, 3, 224, 224))
print('Created models/test_model.onnx')
