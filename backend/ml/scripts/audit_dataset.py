import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


REPO_ROOT = Path(__file__).resolve().parents[3]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MIN_IMAGES_PER_CLASS = 50


def parse_args():
    parser = argparse.ArgumentParser(description="Audit the herbal image dataset.")
    parser.add_argument(
        "--data-dir",
        default="backend/ml/dataset/plant_dataset_raw",
        help="Folder containing one subfolder per plant class.",
    )
    parser.add_argument(
        "--min-images-per-class",
        type=int,
        default=MIN_IMAGES_PER_CLASS,
        help="Minimum recommended images per class.",
    )
    return parser.parse_args()


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_image(path):
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        width, height = image.size
        image.verify()
    return {"width": width, "height": height}


def main():
    args = parse_args()
    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = REPO_ROOT / data_dir

    if not data_dir.exists():
        raise SystemExit(f"Dataset folder not found: {data_dir}")

    classes = []
    invalid_images = []
    hashes = defaultdict(list)

    for class_dir in sorted(path for path in data_dir.iterdir() if path.is_dir()):
        images = [
            path
            for path in class_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ]
        small_images = []

        for image_path in images:
            try:
                info = audit_image(image_path)
                hashes[file_hash(image_path)].append(str(image_path.relative_to(data_dir)))
                if info["width"] < 224 or info["height"] < 224:
                    small_images.append(str(image_path.relative_to(data_dir)))
            except (OSError, UnidentifiedImageError) as exc:
                invalid_images.append(
                    {
                        "path": str(image_path.relative_to(data_dir)),
                        "error": str(exc),
                    }
                )

        count = len(images)
        classes.append(
            {
                "class_name": class_dir.name,
                "image_count": count,
                "needs_more_images": count < args.min_images_per_class,
                "small_images": small_images,
            }
        )

    duplicates = [
        paths
        for paths in hashes.values()
        if len(paths) > 1
    ]

    report = {
        "dataset": str(data_dir),
        "total_classes": len(classes),
        "total_images": sum(item["image_count"] for item in classes),
        "minimum_recommended_images_per_class": args.min_images_per_class,
        "classes": classes,
        "duplicates": duplicates,
        "invalid_images": invalid_images,
    }

    output_path = REPO_ROOT / "backend" / "ml" / "metadata" / "dataset_audit.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print(json.dumps(report, indent=2))
    print(f"Saved audit report to {output_path}")


if __name__ == "__main__":
    main()
