import os
import sys
import csv
import logging
import glob
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/yolo_detect.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("yolo_detect")

OUTPUT_CSV = os.path.join("data", "yolo_detections.csv")
IMAGES_DIR = os.path.join("data", "raw", "images")

# Object classes used for categorization
PERSON_CLASSES = {"person"}
PRODUCT_CLASSES = {"bottle", "cup", "vase", "bowl", "book", "box", "container", "toothbrush", "scissors"}


def classify_image(detected_objects):
    """Classify image based on detected objects."""
    classes_detected = {obj["class_name"].lower() for obj in detected_objects}
    has_person = bool(classes_detected & PERSON_CLASSES)
    has_product = bool(classes_detected & PRODUCT_CLASSES)

    if has_person and has_product:
        return "promotional"
    elif has_product and not has_person:
        return "product_display"
    elif has_person and not has_product:
        return "lifestyle"
    else:
        return "other"


def run_yolo_detection():
    """Run YOLOv8 on all downloaded images and save results to CSV."""
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        use_mock = False
        logger.info("YOLOv8 model loaded successfully.")
    except ImportError:
        logger.warning("ultralytics not installed. Falling back to mock detection mode.")
        use_mock = True

    image_paths = glob.glob(os.path.join(IMAGES_DIR, "**", "*.jpg"), recursive=True)
    image_paths += glob.glob(os.path.join(IMAGES_DIR, "**", "*.png"), recursive=True)

    if not image_paths:
        logger.warning(f"No images found in {IMAGES_DIR}. Run scraper first.")
        return

    logger.info(f"Found {len(image_paths)} images to process.")

    rows = []
    for img_path in image_paths:
        parts = Path(img_path).parts
        # Extract channel_name and message_id from path structure
        try:
            images_idx = [i for i, p in enumerate(parts) if p == "images"][0]
            channel_name = parts[images_idx + 1]
            message_id = Path(img_path).stem
        except (IndexError, ValueError):
            channel_name = "unknown"
            message_id = Path(img_path).stem

        if use_mock:
            # Generate mock detections for pipeline testing
            mock_detections = [
                {"class_name": "bottle", "confidence": 0.82},
                {"class_name": "person", "confidence": 0.76},
            ]
            detections = mock_detections
        else:
            try:
                results = model(img_path, verbose=False)
                detections = []
                for result in results:
                    for box in result.boxes:
                        class_id = int(box.cls)
                        class_name = model.names[class_id]
                        confidence = float(box.conf)
                        detections.append({"class_name": class_name, "confidence": round(confidence, 4)})
            except Exception as e:
                logger.error(f"Detection failed for {img_path}: {e}")
                detections = []

        image_category = classify_image(detections)

        if detections:
            for det in detections:
                rows.append({
                    "message_id": message_id,
                    "channel_name": channel_name,
                    "image_path": img_path.replace("\\", "/"),
                    "detected_class": det["class_name"],
                    "confidence_score": det["confidence"],
                    "image_category": image_category
                })
        else:
            rows.append({
                "message_id": message_id,
                "channel_name": channel_name,
                "image_path": img_path.replace("\\", "/"),
                "detected_class": "none",
                "confidence_score": 0.0,
                "image_category": "other"
            })

        logger.info(f"Processed {img_path}: category={image_category}, detections={len(detections)}")

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["message_id", "channel_name", "image_path", "detected_class", "confidence_score", "image_category"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"YOLO detection complete. {len(rows)} records saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    run_yolo_detection()
