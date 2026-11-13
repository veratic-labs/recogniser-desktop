import numpy as np
import onnxruntime as ort
from pathlib import Path

# Load ONNX model
MODEL_PATH = Path(__file__).resolve().parent / "model_0_numbers.onnx"

session = ort.InferenceSession(
    str(MODEL_PATH),
    providers=["CPUExecutionProvider"]
)

def model_0_numbers_predict(image):
    # Convert image to float32
    X = np.asarray(image, dtype=np.float32).reshape(1, 784)

    # Run inference
    outputs = session.run(
        ["output"],
        {"input": X}
    )

    logits = outputs[0][0]

    # Softmax
    exp = np.exp(logits - np.max(logits))
    probabilities = exp / np.sum(exp)

    # Predicted digit
    prediction = int(np.argmax(logits))
    confidence = float(probabilities[prediction])

    return prediction, confidence
