import argparse
import random
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
AUGMENTED_PREFIX = "quality.aug."


def list_images(stage_dir: Path, augmented: bool) -> list[Path]:
    return sorted(
        path
        for path in stage_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and path.name.startswith(AUGMENTED_PREFIX) == augmented
    )


def split_maturity_dataset(
    source_dir: Path,
    output_dir: Path,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> None:
    if round(train_ratio + val_ratio + test_ratio, 6) != 1:
        raise ValueError("train, val, and test ratios must add up to 1.0")

    random.seed(seed)

    for species_dir in sorted(path for path in source_dir.iterdir() if path.is_dir()):
        for stage_dir in sorted(path for path in species_dir.iterdir() if path.is_dir()):
            original_images = list_images(stage_dir, augmented=False)
            augmented_images = list_images(stage_dir, augmented=True)
            random.shuffle(original_images)

            train_end = int(len(original_images) * train_ratio)
            val_end = train_end + int(len(original_images) * val_ratio)
            splits = {
                "train": original_images[:train_end] + augmented_images,
                "val": original_images[train_end:val_end],
                "test": original_images[val_end:],
            }

            for split_name, split_images in splits.items():
                target_dir = output_dir / split_name / species_dir.name / stage_dir.name
                target_dir.mkdir(parents=True, exist_ok=True)

                for image_path in split_images:
                    shutil.copy2(image_path, target_dir / image_path.name)

                print(
                    f"{split_name}/{species_dir.name}/{stage_dir.name}: "
                    f"{len(split_images)} images"
                )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Split plant maturity images into train, val, and test folders. "
            "Augmented images are copied to train only."
        )
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.source.exists():
        raise FileNotFoundError(f"Missing source folder: {args.source}")

    split_maturity_dataset(
        source_dir=args.source,
        output_dir=args.output,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
