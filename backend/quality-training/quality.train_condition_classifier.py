import argparse
from collections import Counter
import importlib.util
import json
import sys
from pathlib import Path


MODEL_CHOICES = ("efficientnetv2_b0", "mobilenetv3_large", "resnet50")
IMAGE_EXTENSIONS = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp")


def load_evaluation_module():
    evaluate_script_path = Path(__file__).with_name(
        "quality.evaluate_condition_classifier.py"
    )
    evaluate_spec = importlib.util.spec_from_file_location(
        "quality_evaluate_condition_classifier",
        evaluate_script_path,
    )
    evaluate_module = importlib.util.module_from_spec(evaluate_spec)
    assert evaluate_spec.loader is not None
    sys.modules[evaluate_spec.name] = evaluate_module
    evaluate_spec.loader.exec_module(evaluate_module)
    return evaluate_module


def list_species(dataset_dir: Path) -> list[str]:
    return sorted(path.name for path in dataset_dir.iterdir() if path.is_dir())


def list_condition_heads(train_dir: Path) -> dict[str, list[str]]:
    return {
        species: sorted(path.name for path in (train_dir / species).iterdir() if path.is_dir())
        for species in list_species(train_dir)
    }


def collect_files(split_dir: Path, heads: dict[str, list[str]]) -> list[tuple[str, str, int]]:
    examples: list[tuple[str, str, int]] = []

    for species, condition_names in heads.items():
        for condition_index, condition_name in enumerate(condition_names):
            condition_dir = split_dir / species / condition_name

            if not condition_dir.exists():
                continue

            for pattern in IMAGE_EXTENSIONS:
                for image_path in sorted(condition_dir.glob(pattern)):
                    examples.append((str(image_path), species, condition_index))

    return examples


def build_dataset(split_dir, heads, batch_size, training):
    import tensorflow as tf

    examples = collect_files(split_dir, heads)
    image_paths = [example[0] for example in examples]
    species_ids = [example[1] for example in examples]
    labels = [example[2] for example in examples]
    output_names = list(heads.keys())
    dataset = tf.data.Dataset.from_tensor_slices((image_paths, species_ids, labels))

    if training:
        dataset = dataset.shuffle(
            buffer_size=max(len(image_paths), 1),
            reshuffle_each_iteration=True,
        )

    def load_and_preprocess(image_path, species_id, label):
        image_bytes = tf.io.read_file(image_path)
        image = tf.io.decode_image(
            image_bytes,
            channels=3,
            expand_animations=False,
        )
        image.set_shape([None, None, 3])
        image = tf.image.resize_with_pad(image, 224, 224)
        image = tf.cast(image, tf.float32)
        labels_by_head = {
            output_name: tf.where(
                tf.equal(species_id, output_name),
                label,
                tf.constant(-1, dtype=label.dtype),
            )
            for output_name in output_names
        }
        return image, labels_by_head

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
            lambda image, labels: (augmentation(image, training=True), labels),
            num_parallel_calls=tf.data.AUTOTUNE,
        )

    return dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)


def masked_sparse_categorical_crossentropy(y_true, y_pred):
    import tensorflow as tf

    mask = tf.not_equal(y_true, -1)
    safe_y_true = tf.where(mask, y_true, tf.zeros_like(y_true))
    loss = tf.keras.losses.sparse_categorical_crossentropy(safe_y_true, y_pred)
    mask = tf.cast(mask, loss.dtype)
    return tf.math.divide_no_nan(tf.reduce_sum(loss * mask), tf.reduce_sum(mask))


def masked_sparse_categorical_accuracy(y_true, y_pred):
    import tensorflow as tf

    mask = tf.not_equal(y_true, -1)
    safe_y_true = tf.where(mask, y_true, tf.zeros_like(y_true))
    predictions = tf.argmax(y_pred, axis=-1, output_type=safe_y_true.dtype)
    matches = tf.cast(tf.equal(safe_y_true, predictions), tf.float32)
    mask = tf.cast(mask, tf.float32)
    return tf.math.divide_no_nan(tf.reduce_sum(matches * mask), tf.reduce_sum(mask))


def build_model(model_name: str, heads: dict[str, list[str]]):
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
    elif model_name == "mobilenetv3_large":
        base = tf.keras.applications.MobileNetV3Large(
            include_top=False,
            include_preprocessing=True,
            weights="imagenet",
            input_tensor=inputs,
            pooling="avg",
        )
    elif model_name == "resnet50":
        x = tf.keras.layers.Rescaling(255.0)(inputs)
        x = tf.keras.applications.resnet50.preprocess_input(x)
        base = tf.keras.applications.ResNet50(
            include_top=False,
            weights="imagenet",
            input_tensor=x,
            pooling="avg",
        )
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    base.trainable = False
    shared = tf.keras.layers.Dropout(0.25)(base.output)
    outputs = {
        species: tf.keras.layers.Dense(
            len(condition_names),
            activation="softmax",
            name=species,
        )(shared)
        for species, condition_names in heads.items()
    }
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss={
            species: masked_sparse_categorical_crossentropy
            for species in heads
        },
        metrics={
            species: [masked_sparse_categorical_accuracy]
            for species in heads
        },
    )
    return model


def compute_sample_weight_dataset(dataset, heads):
    return dataset


def save_condition_config(output_dir: Path, model_name: str, heads: dict[str, list[str]]) -> None:
    labels_path = output_dir / f"quality.condition_classifier.{model_name}.labels.json"
    labels_path.write_text(json.dumps(heads, indent=2), encoding="utf-8")


def print_dataset_counts(heads: dict[str, list[str]], train_dir: Path) -> None:
    for species, condition_names in heads.items():
        counts = Counter()
        for condition_name in condition_names:
            condition_dir = train_dir / species / condition_name
            counts[condition_name] = sum(
                len(list(condition_dir.glob(pattern)))
                for pattern in IMAGE_EXTENSIONS
            )
        print(f"{species}: {dict(counts)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train a plant-aware multi-head condition classifier."
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--model", choices=MODEL_CHOICES, default="efficientnetv2_b0")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--output-dir", type=Path, default=Path("ml"))
    parser.add_argument(
        "--evaluate-after-training",
        action="store_true",
        help="Evaluate the saved model on the test split after training.",
    )
    args = parser.parse_args()

    train_dir = args.dataset / "train"
    val_dir = args.dataset / "val"
    heads = list_condition_heads(train_dir)

    if not heads:
        raise ValueError(f"No species folders found in {train_dir}")

    print_dataset_counts(heads, train_dir)
    train_dataset = build_dataset(train_dir, heads, args.batch_size, True)
    val_dataset = build_dataset(val_dir, heads, args.batch_size, False)
    model = build_model(args.model, heads)

    history = model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=args.epochs,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / f"quality.condition_classifier.{args.model}.keras"
    history_path = args.output_dir / f"quality.condition_classifier.{args.model}.history.json"

    model.save(model_path)
    save_condition_config(args.output_dir, args.model, heads)
    history_path.write_text(json.dumps(history.history, indent=2), encoding="utf-8")

    print(f"Saved model: {model_path}")
    print(f"Saved labels: {model_path.with_suffix('.labels.json')}")
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
