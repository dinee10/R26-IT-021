from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

_MODEL_CACHE: dict[tuple[str, str, str], tuple[Any, list[str], Any, Any, Any, float, float]] = {}
_MODEL_CACHE_LOCK = Lock()


class SoilClassifierService:
    """Load and run a trained soil-image classifier when the real model is available."""

    def __init__(self, model_dir: str | Path | None = None):
        self.model_dir = Path(model_dir) if model_dir is not None else Path(__file__).resolve().parent
        self.model_path = self.model_dir / 'soil_model.keras'
        self.labels_path = self.model_dir / 'soil_labels.json'
        self.metadata_path = self.model_dir / 'soil_model_metadata.json'
        self.feature_bank_path = self.model_dir / 'soil_feature_bank.npz'

    def predict(self, image_file: Any) -> dict[str, Any]:
        if image_file is None:
            return {
                'success': False,
                'available': False,
                'model_available': all(
                    path.exists()
                    for path in (
                        self.model_path,
                        self.labels_path,
                        self.metadata_path,
                        self.feature_bank_path,
                    )
                ),
                'message': 'No soil image was uploaded for classification.',
                'soil_type': None,
                'confidence': None,
                'soil_analysis': None,
            }

        if not all(
            path.exists()
            for path in (
                self.model_path,
                self.labels_path,
                self.metadata_path,
                self.feature_bank_path,
            )
        ):
            return {
                'success': False,
                'available': False,
                'model_available': False,
                'message': (
                    'Soil classification model files are incomplete. '
                    'Train the classifier with the labeled soil-image dataset first.'
                ),
                'soil_type': None,
                'confidence': None,
                'soil_analysis': None,
            }

        try:
            import tensorflow as tf
            from PIL import Image
            import numpy as np
        except ImportError as exc:
            return {
                'success': False,
                'available': False,
                'model_available': False,
                'message': f'Soil classification dependencies are incomplete: {exc}',
                'soil_type': None,
                'confidence': None,
                'soil_analysis': None,
            }

        try:
            image = Image.open(image_file).convert('RGB')
            image = image.resize((224, 224), Image.Resampling.BILINEAR)
            array = np.asarray(image, dtype=np.float32)
            tensor = np.expand_dims(array, axis=0)

            cache_key = (
                str(self.model_path.resolve()),
                str(self.labels_path.resolve()),
                str(self.feature_bank_path.resolve()),
            )
            with _MODEL_CACHE_LOCK:
                if cache_key not in _MODEL_CACHE:
                    model = tf.keras.models.load_model(self.model_path)
                    with self.labels_path.open('r', encoding='utf-8') as file:
                        labels = json.load(file)
                    feature_model = tf.keras.Model(
                        inputs=model.input,
                        outputs=model.get_layer('dropout').input,
                    )
                    with np.load(self.feature_bank_path) as feature_bank:
                        embeddings = feature_bank['embeddings'].astype(np.float32)
                        feature_labels = feature_bank['labels'].astype(np.int32)
                        distance_threshold = float(feature_bank['distance_threshold'])
                        minimum_confidence = float(feature_bank['minimum_confidence'])
                    embedding_norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                    embeddings = embeddings / np.maximum(embedding_norms, 1e-12)
                    _MODEL_CACHE[cache_key] = (
                        model,
                        labels,
                        feature_model,
                        embeddings,
                        feature_labels,
                        distance_threshold,
                        minimum_confidence,
                    )
                (
                    model,
                    labels,
                    feature_model,
                    embeddings,
                    feature_labels,
                    distance_threshold,
                    minimum_confidence,
                ) = _MODEL_CACHE[cache_key]

            probabilities = model.predict(tensor, verbose=0)[0]
            predicted_index = int(np.argmax(probabilities))
            predicted_label = labels[predicted_index]
            confidence = float(probabilities[predicted_index])
            features = feature_model.predict(tensor, verbose=0)[0]
            feature_norm = float(np.linalg.norm(features))
            normalized_features = features / max(feature_norm, 1e-12)
            class_embeddings = embeddings[feature_labels == predicted_index]
            if not len(class_embeddings):
                raise ValueError(f'No training features are available for {predicted_label}.')
            nearest_distance = 1.0 - float(np.max(class_embeddings @ normalized_features))

            if confidence < minimum_confidence or nearest_distance > distance_threshold:
                return {
                    'success': False,
                    'available': True,
                    'model_available': True,
                    'message': (
                        'This image could not be matched to a supported soil type. '
                        'Upload a clear, close-up photo of alluvial, black, clay, or red soil.'
                    ),
                    'soil_type': None,
                    'confidence': confidence,
                    'soil_analysis': None,
                }

            return {
                'success': True,
                'available': True,
                'model_available': True,
                'message': 'Soil image classified using the trained model.',
                'soil_type': predicted_label,
                'confidence': confidence,
                'soil_analysis': {
                    'class_names': labels,
                    'probabilities': {label: float(probabilities[i]) for i, label in enumerate(labels)},
                },
            }
        except Exception as exc:  # pragma: no cover - runtime guard for invalid image or missing model state
            return {
                'success': False,
                'available': False,
                'model_available': False,
                'message': f'Soil classification failed: {exc}',
                'soil_type': None,
                'confidence': None,
                'soil_analysis': None,
            }
