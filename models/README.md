# Models Directory

Place your model files in this directory.

## Supported Formats

- **ONNX** (`.onnx`) - Recommended, best supported
- **TensorFlow Lite** (`.tflite`) - Good support
- **PyTorch** (`.pt`, `.pth`) - Requires PyTorch installed

## Example Models

For testing, you can use models from:

- [ONNX Model Zoo](https://github.com/onnx/models)
- [TensorFlow Hub](https://tfhub.dev/)
- [Hugging Face](https://huggingface.co/models)

## Creating a Test Model

```python
from edge_sbc_reliability_lab.inference.model_loader import create_dummy_onnx_model

create_dummy_onnx_model("models/test_model.onnx", input_shape=(1, 3, 224, 224))
```

## Notes

- Large model files are excluded from git (see `.gitignore`)
- Document model sources and versions for reproducibility
- Consider model quantization for better Pi 5 performance
