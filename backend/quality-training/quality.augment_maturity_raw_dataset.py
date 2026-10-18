import argparse
import random
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
AUGMENTED_PREFIX = "quality.aug."


@dataclass(frozen=True)
class AugmentationTarget:
    species: str
    maturity_stage: str
    target_count: int


DEFAULT_TARGETS = [
    AugmentationTarget("centella_asiatica", "Young", 54),
    AugmentationTarget("murraya_koenigii", "Young", 104),
]


def normalize_name(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def resolve_child_dir(parent: Path, requested_name: str) -> Path | None:
    if not parent.exists():
        return None

    requested_key = normalize_name(requested_name)
    for child in parent.iterdir():
        if child.is_dir() and normalize_name(child.name) == requested_key:
            return child
    return None


def list_original_images(stage_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in stage_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and not path.name.startswith(AUGMENTED_PREFIX)
    )


def count_images(stage_dir: Path) -> int:
    return sum(
        1
        for path in stage_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def augment_image(image: np.ndarray, rng: random.Random) -> np.ndarray:
    augmented = image.copy()
    height, width = augmented.shape[:2]

    if rng.random() < 0.5:
        augmented = cv2.flip(augmented, 1)

    angle = rng.uniform(-14, 14)
    scale = rng.uniform(0.94, 1.08)
    center = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, scale)
    augmented = cv2.warpAffine(
        augmented,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )

    brightness = rng.uniform(-14, 14)
    contrast = rng.uniform(0.92, 1.12)
    augmented = cv2.convertScaleAbs(augmented, alpha=contrast, beta=brightness)

    if rng.random() < 0.2:
        noise_rng = np.random.default_rng(rng.randint(0, 1_000_000))
        noise = noise_rng.normal(0, 2.5, augmented.shape)
        augmented = np.clip(augmented.astype(np.float32) + noise, 0, 255).astype(
            np.uint8
        )

    if rng.random() < 0.12:
        augmented = cv2.GaussianBlur(augmented, (3, 3), 0)

    return augmented


def write_augmented_image(
    stage_dir: Path,
    source_image_path: Path,
    augmented: np.ndarray,
    index: int,
) -> None:
    target_name = (
        f"{AUGMENTED_PREFIX}{source_image_path.stem}.{index:05d}"
        f"{source_image_path.suffix.lower()}"
    )
    cv2.imwrite(str(stage_dir / target_name), augmented)


def augment_stage(
    stage_dir: Path,
    target_count: int,
    rng: random.Random,
    dry_run: bool,
) -> None:
    current_count = count_images(stage_dir)
    original_images = list_original_images(stage_dir)

    if current_count >= target_count:
        print(f"{stage_dir}: {current_count} images, no augmentation needed")
        return

    if not original_images:
        print(f"{stage_dir}: no original images found, skipping")
        return

    needed = target_count - current_count
    print(f"{stage_dir}: {current_count} -> {target_count} ({needed} new)")

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
            stage_dir=stage_dir,
            source_image_path=source_image_path,
            augmented=augmented,
            index=created + 1,
        )
        created += 1


def parse_target(value: str) -> AugmentationTarget:
    try:
        species, maturity_stage, target_count = value.split(":", maxsplit=2)
        return AugmentationTarget(species, maturity_stage, int(target_count))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Targets must use species:maturity_stage:target_count"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create offline augmented images for selected raw maturity folders."
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Raw maturity dataset root: quality-maturity-raw-dataset.",
    )
    parser.add_argument(
        "--target",
        action="append",
        type=parse_target,
        help="Optional target in species:maturity_stage:target_count format.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned augmentation counts without writing images.",
    )
    args = parser.parse_args()

    if not args.source.exists():
        raise FileNotFoundError(f"Missing source folder: {args.source}")

    targets = args.target or DEFAULT_TARGETS
    rng = random.Random(args.seed)

    for target in targets:
        species_dir = resolve_child_dir(args.source, target.species)
        if species_dir is None:
            print(f"{target.species}: species folder not found, skipping")
            continue

        stage_dir = resolve_child_dir(species_dir, target.maturity_stage)
        if stage_dir is None:
            print(
                f"{species_dir.name}/{target.maturity_stage}: "
                "maturity stage folder not found, skipping"
            )
            continue

        augment_stage(
            stage_dir=stage_dir,
            target_count=target.target_count,
            rng=rng,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
