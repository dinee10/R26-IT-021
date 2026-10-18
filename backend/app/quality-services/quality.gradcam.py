import base64
from typing import Any

import cv2
import numpy as np


def generate_gradcam(
    model: Any,
    preprocessed_image: np.ndarray,
    original_image: np.ndarray,
    output_name: str,
    class_index: int,
) -> dict[str, Any]:
    try:
        import tensorflow as tf
    except ImportError:
        return _unavailable("MODEL_RUNTIME_MISSING")

    conv_layer = _last_conv_layer(model)
    if conv_layer is None:
        return _unavailable("NO_CONVOLUTION_LAYER_FOUND")

    try:
        output_tensor = _select_output_tensor(model, output_name, class_index)
        grad_model = tf.keras.Model(
            inputs=model.inputs,
            outputs=[conv_layer.output, output_tensor],
        )

        with tf.GradientTape() as tape:
            conv_outputs, class_output = grad_model(preprocessed_image, training=False)

        gradients = tape.gradient(class_output, conv_outputs)
        if gradients is None:
            return _unavailable("GRADCAM_GRADIENT_UNAVAILABLE")

        pooled_gradients = tf.reduce_mean(gradients, axis=(0, 1, 2))
        conv_outputs = conv_outputs[0]
        heatmap = conv_outputs @ pooled_gradients[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = tf.maximum(heatmap, 0)
        max_value = tf.reduce_max(heatmap)
        heatmap = tf.math.divide_no_nan(heatmap, max_value).numpy()
    except Exception:
        return _unavailable("GRADCAM_FAILED")

    overlay = _overlay_heatmap(original_image, heatmap)
    success, encoded = cv2.imencode(".jpg", overlay, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not success:
        return _unavailable("GRADCAM_ENCODING_FAILED")

    return {
        "available": True,
        "method": "Grad-CAM",
        "target_output": output_name,
        "target_class_index": class_index,
        "last_conv_layer": conv_layer.name,
        "image_format": "data_url",
        "heatmap_image": (
            "data:image/jpeg;base64,"
            + base64.b64encode(encoded.tobytes()).decode("ascii")
        ),
        "message": (
            "The highlighted regions had the greatest influence on the AI prediction."
        ),
        "limitation": (
            "Grad-CAM highlights influential image regions; it does not identify "
            "specific symptoms unless a separate detector confirms them."
        ),
    }


def _select_output_tensor(model: Any, output_name: str, class_index: int):
    if output_name in model.output_names:
        output_index = model.output_names.index(output_name)
    else:
        output_index = 0

    output_tensor = model.outputs[output_index]
    return output_tensor[:, class_index]


def _last_conv_layer(model: Any):
    for layer in reversed(model.layers):
        try:
            output_shape = layer.output.shape
        except AttributeError:
            continue

        if len(output_shape) == 4:
            return layer

    return None


def _overlay_heatmap(original_image: np.ndarray, heatmap: np.ndarray) -> np.ndarray:
    height, width = original_image.shape[:2]
    resized_heatmap = cv2.resize(heatmap, (width, height))
    heatmap_uint8 = np.uint8(255 * resized_heatmap)
    colored_heatmap = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(original_image, 0.58, colored_heatmap, 0.42, 0)
    return overlay


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "method": "Grad-CAM",
        "reason": reason,
    }
