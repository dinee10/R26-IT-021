from __future__ import annotations

"""Training pipeline for the labeled soil-image dataset."""

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_ROOT = BASE_DIR / 'dataset' / 'soil'
TRAIN_DIR = DATASET_ROOT / 'train'
VALIDATION_DIR = DATASET_ROOT / 'validation'
TEST_DIR = DATASET_ROOT / 'test'
MODEL_PATH = Path(__file__).resolve().parent / 'soil_model.keras'
LABELS_PATH = Path(__file__).resolve().parent / 'soil_labels.json'
METADATA_PATH = Path(__file__).resolve().parent / 'soil_model_metadata.json'
FEATURE_BANK_PATH = Path(__file__).resolve().parent / 'soil_feature_bank.npz'
FEATURE_DISTANCE_THRESHOLD = 0.41
MINIMUM_CONFIDENCE = 0.35

REQUIRED_DATASET_MESSAGE = (
    'A labeled soil-image dataset with matching classes in train, validation, '
    'and test splits is required before training can start.'
)
IMAGE_EXTENSIONS = {'.bmp', '.gif', '.jpeg', '.jpg', '.png'}


def _class_names_for_split(split_dir: Path) -> list[str]:
    return sorted(
        path.name
        for path in split_dir.iterdir()
        if path.is_dir()
        and any(
            image.is_file() and image.suffix.lower() in IMAGE_EXTENSIONS
            for image in path.rglob('*')
        )
    )


def check_soil_training_readiness() -> dict[str, Any]:
    split_dirs = {
        'train': TRAIN_DIR,
        'validation': VALIDATION_DIR,
        'test': TEST_DIR,
    }
    split_classes = {
        split: _class_names_for_split(path) if path.is_dir() else []
        for split, path in split_dirs.items()
    }
    class_sets_match = (
        bool(split_classes['train'])
        and all(classes == split_classes['train'] for classes in split_classes.values())
    )
    dataset_available = class_sets_match
    model_available = all(
        path.exists()
        for path in (MODEL_PATH, LABELS_PATH, METADATA_PATH, FEATURE_BANK_PATH)
    )

    if not dataset_available:
        return {
            'dataset_available': False,
            'model_available': model_available,
            'message': REQUIRED_DATASET_MESSAGE,
            'classes_by_split': split_classes,
            'expected_structure': {
                'train': 'dataset/soil/train/<soil_class>/',
                'validation': 'dataset/soil/validation/<soil_class>/',
                'test': 'dataset/soil/test/<soil_class>/',
            },
            'requirements': [
                'labeled soil images',
                'consistent class folders',
                'train/validation/test splits',
                'model metadata and class labels',
            ],
        }

    image_counts = {
        split: {
            class_name: sum(
                1
                for image in (path / class_name).rglob('*')
                if image.is_file() and image.suffix.lower() in IMAGE_EXTENSIONS
            )
            for class_name in split_classes[split]
        }
        for split, path in split_dirs.items()
    }
    return {
        'dataset_available': True,
        'model_available': model_available,
        'message': 'A labeled soil dataset is present and ready for training.',
        'dataset_root': str(DATASET_ROOT),
        'train_dir': str(TRAIN_DIR),
        'validation_dir': str(VALIDATION_DIR),
        'test_dir': str(TEST_DIR),
        'classes': split_classes['train'],
        'image_counts': image_counts,
    }


def _get_class_names() -> list[str]:
    class_names = _class_names_for_split(TRAIN_DIR)
    if not class_names:
        raise FileNotFoundError('The soil dataset is missing class folders under dataset/soil/train/.')
    return class_names


def train_soil_classifier() -> dict[str, Any]:
    """Train a transfer-learning soil classifier when a valid labeled dataset is present."""
    readiness = check_soil_training_readiness()
    if not readiness['dataset_available']:
        raise FileNotFoundError(readiness['message'])

    try:
        import tensorflow as tf
    except ImportError as exc:
        raise RuntimeError(
            'TensorFlow is required for soil-image training. Install the ML dependencies before training.'
        ) from exc

    if not all(path.exists() for path in (TRAIN_DIR, VALIDATION_DIR, TEST_DIR)):
        raise FileNotFoundError(REQUIRED_DATASET_MESSAGE)

    class_names = _get_class_names()
    image_size = (224, 224)
    train_ds = tf.keras.utils.image_dataset_from_directory(
        TRAIN_DIR,
        image_size=image_size,
        batch_size=32,
        label_mode='categorical',
        class_names=class_names,
        seed=42,
        shuffle=True,
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        VALIDATION_DIR,
        image_size=image_size,
        batch_size=32,
        label_mode='categorical',
        class_names=class_names,
        shuffle=False,
    )
    test_ds = tf.keras.utils.image_dataset_from_directory(
        TEST_DIR,
        image_size=image_size,
        batch_size=32,
        label_mode='categorical',
        class_names=class_names,
        shuffle=False,
    )

    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.prefetch(AUTOTUNE)
    val_ds = val_ds.prefetch(AUTOTUNE)
    test_ds = test_ds.prefetch(AUTOTUNE)

    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights='imagenet',
        pooling='avg',
    )
    base_model.trainable = False

    inputs = tf.keras.Input(shape=(224, 224, 3), name='soil_image')
    x = tf.keras.applications.mobilenet_v2.preprocess_input(inputs)
    x = base_model(x, training=False)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(len(class_names), activation='softmax', name='soil_class')(x)
    model = tf.keras.Model(inputs, outputs)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss='categorical_crossentropy',
        metrics=['accuracy'],
    )

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=15,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=3,
                restore_best_weights=True,
            )
        ],
    )

    results = model.evaluate(test_ds, return_dict=True)
    feature_model = tf.keras.Model(
        inputs=model.input,
        outputs=model.get_layer('dropout').input,
    )
    feature_batches = []
    label_batches = []
    for images, labels in train_ds:
        feature_batches.append(feature_model(images, training=False).numpy())
        label_batches.append(tf.argmax(labels, axis=1).numpy())

    with FEATURE_BANK_PATH.open('wb') as file:
        np.savez_compressed(
            file,
            embeddings=np.concatenate(feature_batches).astype(np.float32),
            labels=np.concatenate(label_batches).astype(np.int32),
            distance_threshold=np.float32(FEATURE_DISTANCE_THRESHOLD),
            minimum_confidence=np.float32(MINIMUM_CONFIDENCE),
        )

    model.save(MODEL_PATH)

    with LABELS_PATH.open('w', encoding='utf-8') as file:
        json.dump(class_names, file, indent=2)

    metadata = {
        'model_type': 'MobileNetV2 transfer learning',
        'input_shape': [224, 224, 3],
        'classes': class_names,
        'dataset_source': 'User-provided archive; no source or license metadata was included.',
        'training_dir': 'backend/dataset/soil/train',
        'validation_dir': 'backend/dataset/soil/validation',
        'test_dir': 'backend/dataset/soil/test',
        'epochs': int(len(history.history.get('loss', []))),
        'test_metrics': {key: float(value) for key, value in results.items()},
        'image_counts': readiness['image_counts'],
        'unknown_image_rejection': {
            'method': 'nearest training-image feature cosine distance',
            'distance_threshold': FEATURE_DISTANCE_THRESHOLD,
            'minimum_confidence': MINIMUM_CONFIDENCE,
        },
    }
    with METADATA_PATH.open('w', encoding='utf-8') as file:
        json.dump(metadata, file, indent=2)

    return {
        'success': True,
        'model_available': True,
        'model_path': str(MODEL_PATH),
        'labels_path': str(LABELS_PATH),
        'metadata_path': str(METADATA_PATH),
        'class_names': class_names,
        'test_metrics': {key: float(value) for key, value in results.items()},
    }


if __name__ == '__main__':
    try:
        outcome = train_soil_classifier()
        print(json.dumps(outcome, indent=2))
    except Exception as exc:  # pragma: no cover - explicit training guard for missing dataset
        print(json.dumps({
            'success': False,
            'model_available': False,
            'error': str(exc),
        }, indent=2))
