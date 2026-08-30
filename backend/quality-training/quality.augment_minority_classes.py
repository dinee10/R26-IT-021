import argparse
import random
from pathlib import Path

import cv2
import numpy as np


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
AUGMENTED_PREFIX = "quality.aug."


def list_images(class_dir: Path) -> list[Path]:
    return sorted(
        path for path in class_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and not path.name.startswith(AUGMENTED_PREFIX)
    )


def count_images(class_dir: Path) -> int:
    return sum(
        1 for path in class_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def augment_image(image: np.ndarray, rng: random.Random) -> np.ndarray:
    augmented = image.copy()
    height, width = augmented.shape[:2]

    if rng.random() < 0.5:
        augmented = cv2.flip(augmented, 1)

    angle = rng.uniform(-18, 18)
    scale = rng.uniform(0.92, 1.08)
    center = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, scale)
    augmented = cv2.warpAffine(
        augmented,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )

    brightness = rng.uniform(-18, 18)
    contrast = rng.uniform(0.88, 1.15)
    augmented = cv2.convertScaleAbs(augmented, alpha=contrast, beta=brightness)

    if rng.random() < 0.25:
        noise = rng.normalvariate(0, 4)
        noise_array = np.random.default_rng(rng.randint(0, 999999)).normal(
            noise,
            3,
            augmented.shape,
        )
        augmented = np.clip(augmented.astype(np.float32) + noise_array, 0, 255)
        augmented = augmented.astype(np.uint8)

    if rng.random() < 0.15:
        augmented = cv2.GaussianBlur(augmented, (3, 3), 0)

    return augmented


def write_augmented_image(
    class_dir: Path,
    source_image_path: Path,
    augmented: np.ndarray,
    index: int,
) -> None:
    target_name = (
        f"{AUGMENTED_PREFIX}{source_image_path.stem}.{index:05d}"
        f"{source_image_path.suffix.lower()}"
    )
    target_path = class_dir / target_name
    cv2.imwrite(str(target_path), augmented)


def augment_class(
    class_dir: Path,
    target_count: int,
    rng: random.Random,
    dry_run: bool,
) -> None:
    original_images = list_images(class_dir)
    current_count = count_images(class_dir)

    if current_count >= target_count:
        print(f"{class_dir.name}: {current_count} images, no augmentation needed")
        return

    if not original_images:
        print(f"{class_dir.name}: no original images found, skipping")
        return

    needed = target_count - current_count
    print(f"{class_dir.name}: {current_count} -> {target_count} ({needed} new)")

    if dry_run:
        return

    created = 0
    while created < needed:
        source_image_path = rng.choice(original_images)
        image = cv2.imread(str(source_image_path), cv2.IMREAD_COLOR)

        if image is None:
            print(f"Skipping unreadable image: {source_image_path}")
            continue

        augmented = augment_image(image, rng)
        write_augmented_image(
            class_dir=class_dir,
            source_image_path=source_image_path,
            augmented=augmented,
            index=created + 1,
        )
        created += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create offline augmented training images for minority classes."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Dataset root containing train, val, and test folders.",
    )
    parser.add_argument(
        "--target-count",
        required=True,
        type=int,
        help="Target number of images per selected training class.",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        help="Specific training class folders to augment. Defaults to all below target.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned augmentation counts without writing images.",
    )
    args = parser.parse_args()

    train_dir = args.dataset / "train"
    if not train_dir.exists():
        raise FileNotFoundError(f"Missing train folder: {train_dir}")

    selected_classes = args.classes or [
        path.name for path in sorted(train_dir.iterdir())
        if path.is_dir() and count_images(path) < args.target_count
    ]
    rng = random.Random(args.seed)

    for class_name in selected_classes:
        class_dir = train_dir / class_name

        if not class_dir.exists():
            print(f"{class_name}: class folder not found, skipping")
            continue

        augment_class(
            class_dir=class_dir,
            target_count=args.target_count,
            rng=rng,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
