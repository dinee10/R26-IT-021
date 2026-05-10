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


def parse_args():
    parser = argparse.ArgumentParser(description="Train the herbal plant classifier.")
    parser.add_argument(
        "--data-dir",
        default="backend/ml/dataset/plant_dataset_raw",
        help="Folder containing one subfolder per plant class.",
    )
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--fine-tune-epochs", type=int, default=10)
    parser.add_argument(
        "--model",
        choices=["efficientnetv2", "mobilenetv2"],
        default="efficientnetv2",
        help="Backbone model to train. EfficientNetV2 is the stronger default for leaf images.",
    )
    return parser.parse_args()


def build_model(class_count, backbone_name):
    augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.08),
            tf.keras.layers.RandomZoom((-0.08, 0.18)),
            tf.keras.layers.RandomTranslation(0.06, 0.06),
            tf.keras.layers.RandomContrast(0.18),
        ],
        name="augmentation",
    )

    if backbone_name == "mobilenetv2":
        preprocess = tf.keras.applications.mobilenet_v2.preprocess_input
        base_model = tf.keras.applications.MobileNetV2(
            input_shape=IMAGE_SIZE + (3,),
            include_top=False,
            weights="imagenet",
        )
        fine_tune_from = -35
    else:
        preprocess = tf.keras.applications.efficientnet_v2.preprocess_input
        base_model = tf.keras.applications.EfficientNetV2B0(
            input_shape=IMAGE_SIZE + (3,),
            include_top=False,
            weights="imagenet",
            include_preprocessing=False,
        )
        fine_tune_from = -60

    base_model.trainable = False

    inputs = tf.keras.Input(shape=IMAGE_SIZE + (3,))
    x = augmentation(inputs)
    x = preprocess(x)
    x = base_model(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.35)(x)
    outputs = tf.keras.layers.Dense(class_count, activation="softmax")(x)
    model = tf.keras.Model(inputs, outputs)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model, base_model, fine_tune_from


def class_weights_for(data_dir, class_names):
    image_suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    counts = []
    for class_name in class_names:
        class_dir = data_dir / class_name
        count = sum(
            1
            for path in class_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in image_suffixes
        )
        counts.append(max(count, 1))

    total = sum(counts)
    class_count = len(class_names)
    return {
        index: total / (class_count * count)
        for index, count in enumerate(counts)
    }


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

    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="training",
        seed=SEED,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="validation",
        seed=SEED,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
    )

    class_names = train_ds.class_names
    class_weights = class_weights_for(data_dir, class_names)
    with (export_dir / "labels.json").open("w", encoding="utf-8") as file:
        json.dump(class_names, file, indent=2)

    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=autotune)
    val_ds = val_ds.cache().prefetch(buffer_size=autotune)

    model, base_model, fine_tune_from = build_model(len(class_names), args.model)
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            export_dir / "herb_model.keras",
            monitor="val_accuracy",
            save_best_only=True,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=6,
            restore_best_weights=True,
        ),
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
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.fine_tune_epochs,
        callbacks=callbacks,
        class_weight=class_weights,
    )

    model.save(export_dir / "herb_model.keras")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    (export_dir / "herb_model.tflite").write_bytes(tflite_model)

    print(f"Saved model, TFLite model, and labels to {export_dir}")


if __name__ == "__main__":
    main()
