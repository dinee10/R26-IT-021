import argparse
import importlib.util
import json
import sys
from pathlib import Path


_training_script_path = Path(__file__).with_name("quality.train_condition_classifier.py")
_training_spec = importlib.util.spec_from_file_location(
    "quality_train_condition_classifier",
    _training_script_path,
)
quality_train_condition_classifier = importlib.util.module_from_spec(_training_spec)
assert _training_spec.loader is not None
sys.modules[_training_spec.name] = quality_train_condition_classifier
_training_spec.loader.exec_module(quality_train_condition_classifier)


def evaluate_model(dataset: Path, model_path: Path, batch_size: int) -> dict:
    import numpy as np
    import tensorflow as tf
    from sklearn.metrics import classification_report, confusion_matrix

    heads = quality_train_condition_classifier.list_condition_heads(
        dataset / "train"
    )
    model = tf.keras.models.load_model(
        model_path,
        custom_objects={
            "masked_sparse_categorical_crossentropy": (
                quality_train_condition_classifier.masked_sparse_categorical_crossentropy
            ),
            "masked_sparse_categorical_accuracy": (
                quality_train_condition_classifier.masked_sparse_categorical_accuracy
            ),
        },
    )
    output: dict = {
        "model_path": str(model_path),
        "heads": heads,
        "species_reports": {},
    }

    for species, condition_names in heads.items():
        test_dir = dataset / "test" / species
        examples = quality_train_condition_classifier.collect_files(
            dataset / "test",
            {species: condition_names},
        )
        if not examples or not test_dir.exists():
            continue

        test_dataset = quality_train_condition_classifier.build_dataset(
            dataset / "test",
            {species: condition_names},
            batch_size,
            False,
        )
        raw_prediction = model.predict(test_dataset, verbose=0)
        probabilities = raw_prediction[species] if isinstance(raw_prediction, dict) else raw_prediction
        predictions = np.argmax(probabilities, axis=1)
        labels = []
        for _, batch_labels in test_dataset:
            labels.extend(batch_labels[species].numpy().tolist())

        report = classification_report(
            labels,
            predictions,
            target_names=condition_names,
            output_dict=True,
            zero_division=0,
        )
        matrix = confusion_matrix(labels, predictions).tolist()
        output["species_reports"][species] = {
            "classification_report": report,
            "confusion_matrix": matrix,
        }

    output_path = model_path.with_suffix(".evaluation.json")
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a plant-aware condition classifier."
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    print(json.dumps(
        evaluate_model(args.dataset, args.model_path, args.batch_size),
        indent=2,
    ))


if __name__ == "__main__":
    main()
