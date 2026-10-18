import argparse
import importlib.util
import json
import sys
from pathlib import Path

_training_script_path = Path(__file__).with_name("quality.train_plant_identifier.py")
_training_spec = importlib.util.spec_from_file_location(
    "quality_train_plant_identifier",
    _training_script_path,
)
quality_train_plant_identifier = importlib.util.module_from_spec(_training_spec)
assert _training_spec.loader is not None
sys.modules[_training_spec.name] = quality_train_plant_identifier
_training_spec.loader.exec_module(quality_train_plant_identifier)


def evaluate_model(dataset: Path, model_path: Path, batch_size: int) -> dict:
    import numpy as np
    import tensorflow as tf
    from sklearn.metrics import classification_report, confusion_matrix

    class_names = quality_train_plant_identifier.list_class_names(
        dataset / "train"
    )
    test_dataset = quality_train_plant_identifier.build_dataset(
        dataset / "test",
        class_names,
        batch_size,
        False,
    )
    model = tf.keras.models.load_model(model_path)

    probabilities = model.predict(test_dataset)
    predictions = np.argmax(probabilities, axis=1)
    labels = np.concatenate([batch_labels.numpy() for _, batch_labels in test_dataset])

    report = classification_report(
        labels,
        predictions,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(labels, predictions).tolist()

    output = {
        "model_path": str(model_path),
        "classes": class_names,
        "classification_report": report,
        "confusion_matrix": matrix,
    }

    output_path = model_path.with_suffix(".evaluation.json")
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a trained plant-identification model on the test split."
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    output = evaluate_model(
        dataset=args.dataset,
        model_path=args.model_path,
        batch_size=args.batch_size,
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
