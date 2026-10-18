import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_MODELS = ("efficientnetv2_b0", "resnet50", "mobilenetv3_large")


def run_command(command: list[str]) -> None:
    print(" ".join(command))
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and evaluate multiple plant-identification models."
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_MODELS),
        choices=DEFAULT_MODELS,
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output-dir", type=Path, default=Path("ml"))
    args = parser.parse_args()

    train_script = Path(__file__).with_name("quality.train_plant_identifier.py")
    evaluate_script = Path(__file__).with_name("quality.evaluate_plant_identifier.py")

    for model_name in args.models:
        run_command([
            sys.executable,
            str(train_script),
            "--dataset",
            str(args.dataset),
            "--model",
            model_name,
            "--epochs",
            str(args.epochs),
            "--batch-size",
            str(args.batch_size),
            "--output-dir",
            str(args.output_dir),
        ])

        model_path = args.output_dir / f"quality.plant_identifier.{model_name}.keras"
        run_command([
            sys.executable,
            str(evaluate_script),
            "--dataset",
            str(args.dataset),
            "--model-path",
            str(model_path),
            "--batch-size",
            str(args.batch_size),
        ])


if __name__ == "__main__":
    main()
