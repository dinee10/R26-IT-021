"""Create a bootstrap YOLO dataset from the existing classification images.

Each source image receives a nearly full-frame bounding box. This is useful for
an initial organ detector because the source photos are object-centred, but
manually drawn boxes should replace these labels for production accuracy.
"""

import argparse
import os
import random
import shutil
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
SOURCES = {
    0: BACKEND_DIR / "ml" / "dataset" / "Leaf_dataset",
    1: BACKEND_DIR / "ml" / "dataset" / "seed_dataset",
    2: BACKEND_DIR / "ml" / "dataset" / "flowers_dataset",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".webp"}
SEED = 22168986


def link_or_copy(source, target):
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="yolo_dataset")
    parser.add_argument("--max-per-class", type=int, default=300)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = BACKEND_DIR / output
    for split in ("train", "val"):
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    totals = {"train": 0, "val": 0}
    for class_id, source_dir in SOURCES.items():
        images = sorted(
            path for path in source_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
        rng.shuffle(images)
        images = images[: args.max_per_class]
        validation_count = max(1, round(len(images) * args.validation_fraction))
        for index, source in enumerate(images):
            split = "val" if index < validation_count else "train"
            stem = f"c{class_id}_{index:04d}"
            target_image = output / "images" / split / f"{stem}{source.suffix.lower()}"
            target_label = output / "labels" / split / f"{stem}.txt"
            if not target_image.exists():
                link_or_copy(source, target_image)
            target_label.write_text(
                f"{class_id} 0.500000 0.500000 0.940000 0.940000\n",
                encoding="utf-8",
            )
            totals[split] += 1
        print(f"class {class_id}: {len(images) - validation_count} train, {validation_count} val")

    dataset_path = output.resolve().as_posix()
    (output / "data.yaml").write_text(
        f'path: "{dataset_path}"\n'
        "train: images/train\nval: images/val\n\n"
        "names:\n  0: leaf\n  1: seed\n  2: flower\n",
        encoding="utf-8",
    )
    print(f"Prepared {totals['train']} training and {totals['val']} validation images.")


if __name__ == "__main__":
    main()
