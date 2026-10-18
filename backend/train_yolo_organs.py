import argparse
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Train a leaf/seed/flower YOLO detector.")
    parser.add_argument("--data", default="yolo_dataset/data.yaml")
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default=None, help="Examples: 0 or cpu")
    args = parser.parse_args()
    data_path = Path(args.data)
    if not data_path.is_absolute():
        data_path = BACKEND_DIR / data_path
    if not data_path.exists():
        raise SystemExit(f"Dataset config not found: {data_path}")

    from ultralytics import YOLO
    output_root = BACKEND_DIR / "ml" / "exports"
    options = dict(data=str(data_path), epochs=args.epochs, imgsz=args.imgsz,
                   batch=args.batch, project=str(output_root), name="yolo_organ",
                   exist_ok=True, seed=22168986)
    if args.device is not None:
        options["device"] = args.device
    YOLO(args.model).train(**options)
    source = output_root / "yolo_organ" / "weights" / "best.pt"
    target = output_root / "yolo_organ" / "best.pt"
    if source.exists():
        target.write_bytes(source.read_bytes())
        print(f"Live detector ready at {target}")


if __name__ == "__main__":
    main()
