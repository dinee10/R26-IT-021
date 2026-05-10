import argparse
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("KERAS_HOME", str(REPO_ROOT / "backend" / "ml" / "models" / ".keras"))

import tensorflow as tf


IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
SEED = 22168986
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args():
    parser = argparse.ArgumentParser(description="Train the herbal plant classifier.")
    parser.add_argument(
        "--data-dir",
        default="backend/ml/dataset/plant_dataset_raw",
        help="Folder containing one subfolder per plant class.",
    )
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--fine-tune-epochs", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--fine-tune-learning-rate", type=float, default=0.00001)
    parser.add_argument("--validation-split", type=float, default=0.2)
    parser.add_argument("--dropout", type=float, default=0.45)
    parser.add_argument("--dense-units", type=int, default=256)
    parser.add_argument(
        "--model",
        choices=["efficientnetv2", "efficientnetv2b1", "mobilenetv2"],
        default="efficientnetv2",
        help="Backbone model to train. EfficientNetV2 is the stronger default for leaf images.",
    )
    return parser.parse_args()


def build_model(class_count, args):
    augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.12),
            tf.keras.layers.RandomZoom((-0.10, 0.22)),
            tf.keras.layers.RandomTranslation(0.08, 0.08),
            tf.keras.layers.RandomContrast(0.22),
        ],
        name="augmentation",
    )

    if args.model == "mobilenetv2":
        preprocess = tf.keras.applications.mobilenet_v2.preprocess_input
        base_model = tf.keras.applications.MobileNetV2(
            input_shape=IMAGE_SIZE + (3,),
            include_top=False,
            weights="imagenet",
        )
        fine_tune_from = -35
    else:
        preprocess = None
        backbone = (
            tf.keras.applications.EfficientNetV2B1
            if args.model == "efficientnetv2b1"
            else tf.keras.applications.EfficientNetV2B0
        )
        base_model = backbone(
            input_shape=IMAGE_SIZE + (3,),
            include_top=False,
            weights="imagenet",
            include_preprocessing=True,
        )
        fine_tune_from = -65 if args.model == "efficientnetv2b1" else -45

    base_model.trainable = False

    inputs = tf.keras.Input(shape=IMAGE_SIZE + (3,))
    x = augmentation(inputs)
    if preprocess is not None:
        x = preprocess(x)
    x = base_model(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(args.dropout)(x)
    x = tf.keras.layers.Dense(args.dense_units, activation="relu")(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(0.35)(x)
    outputs = tf.keras.layers.Dense(class_count, activation="softmax")(x)
    model = tf.keras.Model(inputs, outputs)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=args.learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top_3_accuracy"),
        ],
    )
    return model, base_model, fine_tune_from


def class_weights_for(data_dir, class_names):
    counts = []
    for class_name in class_names:
        class_dir = data_dir / class_name
        count = sum(
            1
            for path in class_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
        counts.append(max(count, 1))

    total = sum(counts)
    class_count = len(class_names)
    return {
        index: total / (class_count * count)
        for index, count in enumerate(counts)
    }


def image_paths_and_labels(data_dir):
    class_names = sorted(path.name for path in data_dir.iterdir() if path.is_dir())
    class_to_index = {class_name: index for index, class_name in enumerate(class_names)}
    paths = []
    labels = []

    for class_name in class_names:
        class_dir = data_dir / class_name
        for path in sorted(class_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                paths.append(str(path))
                labels.append(class_to_index[class_name])

    return paths, labels, class_names


def make_dataset(paths, labels, training):
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        dataset = dataset.shuffle(len(paths), seed=SEED, reshuffle_each_iteration=True)

    def load_image(path, label):
        image = tf.io.read_file(path)
        image = tf.io.decode_image(image, channels=3, expand_animations=False)
        image.set_shape((None, None, 3))
        image = tf.image.resize(image, IMAGE_SIZE, method="bilinear")
        return image, label

    return dataset.map(load_image, num_parallel_calls=tf.data.AUTOTUNE).batch(BATCH_SIZE)


def main():
    args = parse_args()
    repo_root = REPO_ROOT
    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = repo_root / data_dir
    export_dir = repo_root / "backend" / "ml" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    if not data_dir.exists():
        raise SystemExit(f"Dataset folder not found: {data_dir}")

    from sklearn.model_selection import train_test_split

    image_paths, labels, class_names = image_paths_and_labels(data_dir)
    if not image_paths:
        raise SystemExit(f"No images found in dataset folder: {data_dir}")

    train_paths, val_paths, train_labels, val_labels = train_test_split(
        image_paths,
        labels,
        test_size=args.validation_split,
        random_state=SEED,
        stratify=labels,
    )

    train_ds = make_dataset(train_paths, train_labels, training=True)
    val_ds = make_dataset(val_paths, val_labels, training=False)

    print(f"Found {len(image_paths)} files belonging to {len(class_names)} classes.")
    print(f"Using {len(train_paths)} files for stratified training.")
    print(f"Using {len(val_paths)} files for stratified validation.")

    class_weights = class_weights_for(data_dir, class_names)
    with (export_dir / "labels.json").open("w", encoding="utf-8") as file:
        json.dump(class_names, file, indent=2)

    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=autotune)
    val_ds = val_ds.cache().prefetch(buffer_size=autotune)

    model, base_model, fine_tune_from = build_model(len(class_names), args)
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            export_dir / "herb_model.keras",
            monitor="val_accuracy",
            save_best_only=True,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=8,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.35,
            patience=3,
            min_lr=1e-6,
        ),
        tf.keras.callbacks.CSVLogger(export_dir / "training_log.csv"),
    ]

    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=callbacks,
        class_weight=class_weights,
    )

    base_model.trainable = True
    for layer in base_model.layers[:fine_tune_from]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=args.fine_tune_learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top_3_accuracy"),
        ],
    )
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.fine_tune_epochs,
        callbacks=callbacks,
        class_weight=class_weights,
    )

    model.save(export_dir / "herb_model.keras")
    write_evaluation_report(model, val_ds, class_names, export_dir)

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    (export_dir / "herb_model.tflite").write_bytes(tflite_model)

    print(f"Saved model, TFLite model, and labels to {export_dir}")


def write_evaluation_report(model, val_ds, class_names, export_dir):
    import numpy as np
    from sklearn.metrics import classification_report, confusion_matrix

    true_labels = []
    predicted_labels = []

    for images, labels in val_ds:
        predictions = model.predict(images, verbose=0)
        true_labels.extend(labels.numpy().tolist())
        predicted_labels.extend(np.argmax(predictions, axis=1).tolist())

    report = {
        "classification_report": classification_report(
            true_labels,
            predicted_labels,
            labels=list(range(len(class_names))),
            target_names=class_names,
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(
            true_labels,
            predicted_labels,
            labels=list(range(len(class_names))),
        ).tolist(),
        "class_names": class_names,
    }

    with (export_dir / "evaluation_report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)


if __name__ == "__main__":
    main()
