import argparse
from collections import Counter
import importlib.util
import json
import sys
from pathlib import Path


MODEL_CHOICES = ("efficientnetv2_b0", "resnet50", "mobilenetv3_large")
IMAGE_EXTENSIONS = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp")


def load_evaluation_module():
    evaluate_script_path = Path(__file__).with_name(
        "quality.evaluate_plant_identifier.py"
    )
    evaluate_spec = importlib.util.spec_from_file_location(
        "quality_evaluate_plant_identifier",
        evaluate_script_path,
    )
    evaluate_module = importlib.util.module_from_spec(evaluate_spec)
    assert evaluate_spec.loader is not None
    sys.modules[evaluate_spec.name] = evaluate_module
    evaluate_spec.loader.exec_module(evaluate_module)
    return evaluate_module


def list_class_names(train_dir: Path) -> list[str]:
    return sorted(path.name for path in train_dir.iterdir() if path.is_dir())


def collect_files(split_dir: Path, class_names: list[str]) -> tuple[list[str], list[int]]:
    image_paths: list[str] = []
    labels: list[int] = []

    for class_index, class_name in enumerate(class_names):
        class_dir = split_dir / class_name
        for pattern in IMAGE_EXTENSIONS:
            for image_path in sorted(class_dir.glob(pattern)):
                image_paths.append(str(image_path))
                labels.append(class_index)

    return image_paths, labels


def compute_class_weights(split_dir: Path, class_names: list[str]) -> dict[int, float]:
    _, labels = collect_files(split_dir, class_names)
    label_counts = Counter(labels)
    total_count = sum(label_counts.values())
    class_count = len(class_names)

    if total_count == 0:
        raise ValueError(f"No training images found in {split_dir}")

    weights = {
        class_index: total_count / (class_count * label_counts[class_index])
        for class_index in range(class_count)
        if label_counts[class_index] > 0
    }

    print("Class weights:")
    for class_index, weight in weights.items():
        print(
            f"  {class_names[class_index]}: "
            f"{weight:.4f} ({label_counts[class_index]} train images)"
        )

    return weights


def build_dataset(split_dir, class_names, batch_size, training):
    import tensorflow as tf

    image_paths, labels = collect_files(split_dir, class_names)
    dataset = tf.data.Dataset.from_tensor_slices((image_paths, labels))

    if training:
        dataset = dataset.shuffle(
            buffer_size=max(len(image_paths), 1),
            reshuffle_each_iteration=True,
        )

    def load_and_preprocess(image_path, label):
        image_bytes = tf.io.read_file(image_path)
        image = tf.io.decode_image(
            image_bytes,
            channels=3,
            expand_animations=False,
        )
        image.set_shape([None, None, 3])
        image = tf.image.resize_with_pad(image, 224, 224)
        image = tf.cast(image, tf.float32)
        return image, label

    dataset = dataset.map(
        load_and_preprocess,
        num_parallel_calls=tf.data.AUTOTUNE,
    )

    if training:
        augmentation = tf.keras.Sequential([
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.08),
            tf.keras.layers.RandomZoom(0.12),
            tf.keras.layers.RandomContrast(0.15),
        ])

        dataset = dataset.map(
            lambda image, label: (augmentation(image, training=True), label),
            num_parallel_calls=tf.data.AUTOTUNE,
        )

    return dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)


def build_model(model_name: str, class_count: int):
    import tensorflow as tf

    inputs = tf.keras.Input(shape=(224, 224, 3))

    if model_name == "efficientnetv2_b0":
        base = tf.keras.applications.EfficientNetV2B0(
            include_top=False,
            include_preprocessing=True,
            weights="imagenet",
            input_tensor=inputs,
            pooling="avg",
        )
    elif model_name == "resnet50":
        x = tf.keras.layers.Lambda(
            tf.keras.applications.resnet50.preprocess_input,
        )(inputs)
        base = tf.keras.applications.ResNet50(
            include_top=False,
            weights="imagenet",
            input_tensor=x,
            pooling="avg",
        )
    elif model_name == "mobilenetv3_large":
        base = tf.keras.applications.MobileNetV3Large(
            include_top=False,
            include_preprocessing=True,
            weights="imagenet",
            input_tensor=inputs,
            pooling="avg",
        )
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    base.trainable = False
    x = tf.keras.layers.Dropout(0.25)(base.output)
    outputs = tf.keras.layers.Dense(class_count, activation="softmax")(x)

    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train a plant-identification classifier with letterbox preprocessing."
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--model", choices=MODEL_CHOICES, default="efficientnetv2_b0")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output-dir", type=Path, default=Path("ml"))
    parser.add_argument(
        "--require-unknown",
        action="store_true",
        help="Fail training if the dataset does not include an unknown class.",
    )
    parser.add_argument(
        "--evaluate-after-training",
        action="store_true",
        help="Evaluate the saved model on the test split after training.",
    )
    parser.add_argument(
        "--use-class-weights",
        action="store_true",
        help="Weight minority classes higher during training.",
    )
    args = parser.parse_args()

    train_dir = args.dataset / "train"
    val_dir = args.dataset / "val"
    class_names = list_class_names(train_dir)

    if args.require_unknown and "unknown" not in class_names:
        raise ValueError("Dataset must include an unknown class folder.")

    if "unknown" not in class_names:
        print(
            "Warning: unknown class is missing. This is acceptable for early "
            "model comparison, but the final plant ID model must include it."
        )

    train_dataset = build_dataset(train_dir, class_names, args.batch_size, True)
    val_dataset = build_dataset(val_dir, class_names, args.batch_size, False)
    class_weights = (
        compute_class_weights(train_dir, class_names)
        if args.use_class_weights
        else None
    )
    model = build_model(args.model, len(class_names))

    history = model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=args.epochs,
        class_weight=class_weights,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / f"quality.plant_identifier.{args.model}.keras"
    labels_path = args.output_dir / f"quality.plant_identifier.{args.model}.labels.json"
    history_path = args.output_dir / f"quality.plant_identifier.{args.model}.history.json"

    model.save(model_path)
    labels_path.write_text(json.dumps(class_names, indent=2), encoding="utf-8")
    history_path.write_text(json.dumps(history.history, indent=2), encoding="utf-8")

    print(f"Saved model: {model_path}")
    print(f"Saved labels: {labels_path}")
    print(f"Saved history: {history_path}")

    if args.evaluate_after_training:
        evaluate_module = load_evaluation_module()
        evaluation = evaluate_module.evaluate_model(
            dataset=args.dataset,
            model_path=model_path,
            batch_size=args.batch_size,
        )
        print(json.dumps(evaluation, indent=2))


if __name__ == "__main__":
    main()
