"""
License plate detection (YOLO) + OCR (EasyOCR).

Logic mirrors the standalone License Plate/ project:
  detect → crop → preprocess variants → EasyOCR → validate → save snapshots.
"""
from __future__ import annotations

import csv
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_WEIGHTS = (
    BASE_DIR / "runs" / "train" / "stage3_finetune3" / "weights" / "best_number_plate_detection.pt"
)
OCR_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "

_engine: "PlateEngine | None" = None
_engine_lock = threading.Lock()


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def resolve_media_root() -> Path:
    """Django media root — defaults to backend/media next to ml_services."""
    override = os.getenv("ML_MEDIA_ROOT", "").strip()
    if override:
        return Path(override)
    return (BASE_DIR.parent / "backend" / "media").resolve()


def resolve_plate_media_dir() -> Path:
    """backend/media/licence plates/"""
    override = os.getenv("ML_PLATE_MEDIA_DIR", "").strip()
    if override:
        root = Path(override)
    else:
        root = resolve_media_root() / "licence plates"
    root.mkdir(parents=True, exist_ok=True)
    (root / "plates").mkdir(parents=True, exist_ok=True)
    (root / "frames").mkdir(parents=True, exist_ok=True)
    return root


def resolve_plate_weights() -> Path | None:
    env = os.getenv("ML_PLATE_WEIGHTS", "").strip()
    if env:
        path = Path(env)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path if path.is_file() else None
    if DEFAULT_WEIGHTS.is_file():
        return DEFAULT_WEIGHTS
    # Fallbacks
    legacy = BASE_DIR / "runs" / "plate_detect_v1" / "weights" / "best.pt"
    if legacy.is_file():
        return legacy
    sibling = (
        BASE_DIR.parent
        / "License Plate"
        / "runs"
        / "plate_detect_v1"
        / "weights"
        / "best.pt"
    )
    return sibling if sibling.is_file() else None


def clean_plate_text(text: str | list) -> str:
    if isinstance(text, list):
        text = " ".join(str(t) for t in text)
    text = str(text).upper().strip()
    text = re.sub(r"[^A-Z0-9 ]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def plate_key(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


_REGION_NOISE = (
    "ISLAMABAD",
    "ISLAMABA",
    "ISLAMAB",
    "ICT",
    "ISB",
    "PUNJAB",
    "SINDH",
    "KARACHI",
    "LAHORE",
    "PESHAWAR",
    "BALOCH",
    "PAKISTAN",
    "PAK",
    "CITY",
)


def _strip_region_noise(key: str) -> str:
    out = key
    for token in _REGION_NOISE:
        out = out.replace(token, "")
    return out


def canonicalize_plate(text: str) -> str:
    """Extract PK-style plate (BSD987) from OCR that often includes city text."""
    key = _strip_region_noise(plate_key(text))
    if not key:
        return ""
    candidates: list[str] = []
    candidates.extend(re.findall(r"[A-Z]{2,3}\d{3}", key))
    candidates.extend(re.findall(r"[A-Z]{2,3}\d{4}", key))
    if not candidates:
        m = re.search(r"([A-Z]{2,4})(\d{3,4})", key)
        if m:
            candidates.append(m.group(1) + m.group(2))
    if candidates:
        def rank(c: str) -> tuple[int, int, int]:
            letters = re.match(r"[A-Z]+", c)
            digits = re.search(r"\d+", c)
            la = letters.group(0) if letters else ""
            da = digits.group(0) if digits else ""
            style = 0 if len(la) == 3 and len(da) == 3 else 1
            return (style, 0 if len(da) == 3 else 1, len(c))

        return sorted(set(candidates), key=rank)[0]
    m = re.match(r"^([A-Z]{2,3})(\d{3,4})", key)
    if m:
        return m.group(1) + m.group(2)
    return ""


def format_plate_display(text: str) -> str:
    canon = canonicalize_plate(text) or plate_key(text)
    m = re.match(r"^([A-Z]+)(\d+)$", canon)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return clean_plate_text(text)


def is_valid_plate(text: str, min_len: int = 5) -> bool:
    canon = canonicalize_plate(text)
    key = canon or plate_key(text)
    if len(key) < min_len:
        return False
    if key in {"UNKNOWN", "PLATE", "LICENSEPLATE"}:
        return False
    if not canon:
        return False
    if not re.search(r"[A-Z]", key) or not re.search(r"\d", key):
        return False
    letters = re.sub(r"\d", "", canon)
    digits = re.sub(r"\D", "", canon)
    return len(letters) >= 2 and len(digits) >= 3


def _edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    if abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def plates_are_same_vehicle(a: str, b: str) -> bool:
    ca = canonicalize_plate(a) or plate_key(a)
    cb = canonicalize_plate(b) or plate_key(b)
    if not ca or not cb:
        return False
    if ca == cb:
        return True
    la, da = re.sub(r"\d", "", ca), re.sub(r"\D", "", ca)
    lb, db = re.sub(r"\d", "", cb), re.sub(r"\D", "", cb)
    digits_ok = da == db or (
        abs(len(da) - len(db)) == 1 and (da in db or db in da)
    ) or (len(da) == len(db) and _edit_distance(da, db) <= 1)
    if not digits_ok:
        return False
    if la == lb:
        return True
    if min(len(la), len(lb)) >= 2 and (
        la.endswith(lb) or lb.endswith(la) or la.startswith(lb) or lb.startswith(la)
    ):
        return True
    return _edit_distance(la, lb) <= 1


def reading_score(text: str, conf: float) -> float:
    canon = canonicalize_plate(text)
    key = canon or plate_key(text)
    # Prefer classic XXX999 and penalize long junk strings
    bonus = 0.25 if re.fullmatch(r"[A-Z]{3}\d{3}", key or "") else 0.0
    penalty = max(0, len(plate_key(text)) - 7) * 0.08
    return conf + min(len(key), 12) * 0.035 + bonus - penalty


def upscale(crop: np.ndarray, min_height: int = 120) -> np.ndarray:
    h, w = crop.shape[:2]
    scale = max(1.0, min_height / max(h, 1))
    if scale > 1.0:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return crop


def preprocess_variants(crop: np.ndarray) -> list[np.ndarray]:
    if crop.size == 0:
        return []
    crop = upscale(crop)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blur = cv2.bilateralFilter(enhanced, 9, 75, 75)
    sharp = cv2.filter2D(blur, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]))
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(binary) > 127:
        binary = cv2.bitwise_not(binary)
    return [
        cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR),
        cv2.cvtColor(blur, cv2.COLOR_GRAY2BGR),
        cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR),
        crop,
    ]


def merge_ocr_segments(results: list, min_conf: float = 0.1) -> tuple[str, float]:
    segments: list[dict] = []
    for item in results:
        if len(item) != 3:
            continue
        bbox, text, conf = item
        cleaned = clean_plate_text(text)
        if not cleaned or float(conf) < min_conf:
            continue
        xs = [p[0] for p in bbox]
        segments.append(
            {
                "left": min(xs),
                "right": max(xs),
                "text": cleaned.replace(" ", ""),
                "conf": float(conf),
            }
        )
    if not segments:
        return "", 0.0
    segments.sort(key=lambda s: s["left"])
    parts = [segments[0]["text"]]
    confs = [segments[0]["conf"]]
    for i in range(1, len(segments)):
        prev, curr = segments[i - 1], segments[i]
        gap = curr["left"] - prev["right"]
        avg_char_w = max((prev["right"] - prev["left"]) / max(len(prev["text"]), 1), 8.0)
        if gap > avg_char_w * 0.4:
            parts.append(" ")
        parts.append(curr["text"])
        confs.append(curr["conf"])
    return clean_plate_text("".join(parts)), sum(confs) / len(confs)


def draw_plate_box(frame: np.ndarray, box: tuple[int, int, int, int], text: str, ok: bool) -> None:
    x1, y1, x2, y2 = box
    color = (0, 255, 0) if ok else (0, 165, 255)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    label = text if text else "PLATE"
    (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
    y_text = max(y1 - 8, th + 8)
    cv2.rectangle(frame, (x1, y_text - th - 8), (x1 + tw + 8, y_text + baseline), color, -1)
    cv2.putText(frame, label, (x1 + 4, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)


class PlateEngine:
    """YOLO plate detector + EasyOCR reader with media snapshot saving."""

    def __init__(self):
        self.weights = resolve_plate_weights()
        self.detector = None
        self.reader = None
        self.available = False
        self._infer_lock = threading.Lock()
        self._save_lock = threading.Lock()
        self._last_saved: dict[str, float] = {}
        self._best_saved: dict[str, float] = {}  # plate_key → best ocr*det score already on disk
        self.conf = _env_float("ML_PLATE_CONF", 0.25)
        self.min_ocr_conf = _env_float("ML_PLATE_MIN_OCR_CONF", 0.25)
        self.min_det_conf = _env_float("ML_PLATE_MIN_DET_CONF", 0.20)
        self.min_plate_len = _env_int("ML_PLATE_MIN_LEN", 4)
        # Default: only one snapshot per plate unless a better OCR read appears
        self.save_interval = _env_float("ML_PLATE_SAVE_INTERVAL", 3600.0)
        # 4K cameras need larger imgsz — 640 misses small plates
        self.imgsz = max(640, _env_int("ML_PLATE_IMGSZ", 1280))
        self.device = os.getenv("ML_DEVICE", "0").strip() or "0"
        self._media_dir = resolve_plate_media_dir()
        self._load()

    def _load(self) -> None:
        if self.weights is None:
            print("[plate] Weights not found — plate detection disabled")
            return
        try:
            from ultralytics import YOLO

            self.detector = YOLO(str(self.weights))
            print(f"[plate] YOLO loaded: {self.weights}")
        except Exception as exc:
            print(f"[plate] Failed to load YOLO: {exc}")
            return

        try:
            import easyocr

            use_gpu = self.device.lower() != "cpu"
            self.reader = easyocr.Reader(["en"], gpu=use_gpu, verbose=False)
            print(f"[plate] EasyOCR ready (gpu={use_gpu})")
        except Exception as exc:
            print(f"[plate] Failed to load EasyOCR: {exc}")
            return

        self.available = True
        print(f"[plate] Media dir: {self._media_dir}")

    def ocr_plate(self, crop: np.ndarray) -> tuple[str, float]:
        if self.reader is None or crop is None or crop.size == 0:
            return "", 0.0
        best_text, best_conf, best_score = "", 0.0, -1.0
        for variant in preprocess_variants(crop):
            results = self.reader.readtext(
                variant,
                detail=1,
                paragraph=False,
                allowlist=OCR_ALLOWLIST,
                width_ths=0.5,
                height_ths=0.5,
            )
            candidates = [merge_ocr_segments(results)]
            for item in results:
                if len(item) == 3:
                    cleaned = clean_plate_text(item[1])
                    if cleaned:
                        candidates.append((cleaned, float(item[2])))
            for text, conf in candidates:
                if not text:
                    continue
                canon = canonicalize_plate(text)
                if not canon:
                    continue
                display = format_plate_display(canon)
                score = reading_score(text, conf)
                if score > best_score:
                    best_text, best_conf, best_score = display, conf, score
        return best_text, best_conf

    def save_snapshot(
        self,
        frame: np.ndarray,
        crop: np.ndarray,
        plate_text: str,
        det_conf: float,
        ocr_conf: float,
        *,
        camera_key: str = "",
        force: bool = False,
    ) -> dict[str, str] | None:
        """Save plate crop + annotated frame under media/licence plates/."""
        if not is_valid_plate(plate_text, min_len=self.min_plate_len):
            return None
        key = canonicalize_plate(plate_text) or plate_key(plate_text)
        if not key:
            return None
        plate_text = format_plate_display(key)
        score = float(ocr_conf) * float(det_conf) + float(ocr_conf) * 0.5
        now = time.time()
        with self._save_lock:
            # Collapse OCR variants of the same physical plate per camera
            slot = f"{camera_key}:{key}"
            for existing_slot, prev_best in list(self._best_saved.items()):
                if not existing_slot.startswith(f"{camera_key}:"):
                    continue
                existing_key = existing_slot.split(":", 1)[-1]
                if not plates_are_same_vehicle(key, existing_key):
                    continue
                last = self._last_saved.get(existing_slot, 0.0)
                if not force:
                    if score <= prev_best * 1.05:
                        return None
                    if now - last < self.save_interval and score <= prev_best:
                        return None
                slot = existing_slot
                break
            if not force:
                prev_best = self._best_saved.get(slot, 0.0)
                last = self._last_saved.get(slot, 0.0)
                if prev_best > 0 and score <= prev_best * 1.05:
                    return None
                if now - last < self.save_interval and score <= prev_best:
                    return None
            self._last_saved[slot] = now
            self._best_saved[slot] = max(self._best_saved.get(slot, 0.0), score)

        media = resolve_plate_media_dir()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        safe = key
        cam_prefix = plate_key(camera_key)[:24] if camera_key else "cam"
        plate_name = f"{stamp}_{cam_prefix}_{safe}.jpg"
        frame_name = f"{stamp}_{cam_prefix}_{safe}.jpg"
        plate_path = media / "plates" / plate_name
        frame_path = media / "frames" / frame_name

        annotated = frame.copy()
        # Prefer drawing using crop location if present in detections later;
        # for now draw nothing extra if box unknown — frame already annotated by caller.
        cv2.imwrite(str(plate_path), crop)
        cv2.imwrite(str(frame_path), annotated)

        log_path = media / "captures.csv"
        write_header = not log_path.exists()
        with self._save_lock:
            with log_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp",
                        "camera_key",
                        "plate_number",
                        "det_conf",
                        "ocr_conf",
                        "plate_image",
                        "frame_image",
                    ],
                )
                if write_header:
                    writer.writeheader()
                writer.writerow(
                    {
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "camera_key": camera_key,
                        "plate_number": plate_text,
                        "det_conf": round(det_conf, 4),
                        "ocr_conf": round(ocr_conf, 4),
                        "plate_image": f"licence plates/plates/{plate_name}",
                        "frame_image": f"licence plates/frames/{frame_name}",
                    }
                )
            numbers_path = media / "numbers.txt"
            with numbers_path.open("a", encoding="utf-8") as f:
                prefix = f"[{camera_key}] " if camera_key else ""
                f.write(f"{datetime.now().isoformat(timespec='seconds')}  {prefix}{plate_text}\n")

        return {
            "plate_image": f"licence plates/plates/{plate_name}",
            "frame_image": f"licence plates/frames/{frame_name}",
            "plate_image_abs": str(plate_path),
            "frame_image_abs": str(frame_path),
        }

    def detect_and_read(
        self,
        frame: np.ndarray,
        *,
        camera_key: str = "",
        conf: float | None = None,
        save: bool = True,
        force_save: bool = False,
    ) -> list[dict[str, Any]]:
        """Run plate YOLO + OCR on a BGR frame. Optionally save accepted plates to media."""
        if not self.available or self.detector is None or frame is None or frame.size == 0:
            return []

        height, width = frame.shape[:2]
        det_conf_thresh = conf if conf is not None else self.conf
        detections: list[dict[str, Any]] = []

        with self._infer_lock:
            results = self.detector.predict(
                frame,
                conf=det_conf_thresh,
                imgsz=self.imgsz,
                device=self.device,
                verbose=False,
            )

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(width, x2), min(height, y2)
                det_conf = float(box.conf[0])
                crop = frame[y1:y2, x1:x2]
                if crop.size == 0:
                    continue

                plate_text, ocr_conf = self.ocr_plate(crop)
                accepted = (
                    is_valid_plate(plate_text, self.min_plate_len)
                    and ocr_conf >= self.min_ocr_conf
                    and det_conf >= self.min_det_conf
                )

                saved: dict[str, str] | None = None
                # Save accepted OCR reads, or any strong YOLO hit (crop) so media fills
                should_save = save and (accepted or det_conf >= 0.35)
                if should_save:
                    annotated = frame.copy()
                    label = plate_text if plate_text else "PLATE"
                    draw_plate_box(annotated, (x1, y1, x2, y2), label, accepted)
                    saved = self.save_snapshot(
                        annotated,
                        crop,
                        plate_text or "UNKNOWN",
                        det_conf,
                        ocr_conf,
                        camera_key=camera_key,
                        force=force_save,
                    )

                det: dict[str, Any] = {
                    "class_id": 0,
                    "class_name": "license_plate",
                    "label": plate_text if plate_text else "license_plate",
                    "plate_number": plate_text,
                    "confidence": round(det_conf, 4),
                    "ocr_confidence": round(ocr_conf, 4),
                    "bbox": [x1, y1, x2, y2],
                    "alert": False,
                    "priority": "high",
                    "model": "plate",
                    "accepted": accepted,
                }
                if saved:
                    det["plate_image"] = saved["plate_image"]
                    det["frame_image"] = saved["frame_image"]
                detections.append(det)

        return detections


def get_plate_engine() -> PlateEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = PlateEngine()
    return _engine
