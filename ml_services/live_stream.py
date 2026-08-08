"""
Live RTSP streams with multi-model YOLO inference + optional plate OCR.
COCO / custom / smoke / weapon / face / plate all run when weights are available.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote

os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")

_DEFAULT_FFMPEG_CAPTURE_OPTIONS = (
    "rtsp_transport;tcp|"
    "fflags;nobuffer+discardcorrupt|"
    "flags;low_delay|"
    "err_detect;ignore_err|"
    "probesize;500000|"
    "analyzeduration;500000|"
    "max_delay;0|"
    "reorder_queue_size;0|"
    "stimeout;5000000"
)
if "OPENCV_FFMPEG_CAPTURE_OPTIONS" not in os.environ:
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = os.getenv(
        "ML_RTSP_FFMPEG_OPTIONS",
        _DEFAULT_FFMPEG_CAPTURE_OPTIONS,
    )

import cv2
import numpy as np

from face_recognizer import KnownFaceDB
from inference_engine import (
    ALLOWED_COCO_CLASS_IDS,
    SMOKE_FIRE_MIN_CONF,
    WEAPON_MIN_CONF,
    custom_only_class_ids,
    get_cuda_status,
    get_face_db,
    get_yolo_coco_model,
    get_yolo_custom_model,
    get_yolo_smoke_model,
    get_yolo_weapon_model,
    keep_custom_classes_only,
    merge_triple_detections,
    parse_yolo_result,
    resolve_coco_weights_path,
    resolve_custom_weights_path,
    resolve_ml_device,
    resolve_smoke_weights_path,
    resolve_weapon_weights_path,
)
from plate_recognizer import PlateEngine, get_plate_engine


def build_rtsp_url(
    ip: str,
    user: str = "admin",
    password: str = "",
    port: str | int = "554",
    path: str = "/Streaming/Channels/101",
) -> str:
    encoded_password = quote(password, safe="")
    if password:
        return f"rtsp://{user}:{encoded_password}@{ip}:{port}{path}"
    return f"rtsp://{user}@{ip}:{port}{path}"


def _rtsp_config() -> dict[str, str]:
    return {
        "user": os.getenv("CAMERA_RTSP_USER", "admin"),
        "password": os.getenv("CAMERA_RTSP_PASSWORD", ""),
        "port": os.getenv("CAMERA_RTSP_PORT", "554"),
        "path": os.getenv("CAMERA_RTSP_PATH", "/Streaming/Channels/101"),
    }


def _boot_camera_ips() -> list[str]:
    raw = os.getenv("ML_LIVE_BOOT_IPS", "").strip()
    if not raw:
        return []
    return [ip.strip() for ip in raw.split(",") if ip.strip()]


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


def _resolve_ffmpeg_path() -> str | None:
    custom = os.getenv("FFMPEG_PATH", "").strip()
    if custom and os.path.isfile(custom):
        return custom
    found = shutil.which("ffmpeg")
    if found:
        return found
    base = Path(__file__).resolve().parent.parent / "tools" / "ffmpeg" / "bin"
    for name in ("ffmpeg.exe", "ffmpeg"):
        candidate = base / name
        if candidate.is_file():
            return str(candidate)
    return None


def _rtsp_decode_backend() -> str:
    return os.getenv("ML_RTSP_DECODE", "ffmpeg").strip().lower()


class CameraStream:
    """Background reader that keeps the newest frame; reconnects on decode failures."""

    def __init__(self, rtsp_url: str, label: str, drain_reads: int = 2):
        self.rtsp_url = rtsp_url
        self.label = label
        self.drain_reads = max(1, drain_reads)
        self.lock = threading.Lock()
        self.frame: np.ndarray | None = None
        self.running = True
        self.connected = False
        self.cap: cv2.VideoCapture | None = None
        self._fail_streak = 0
        self._max_fail_before_reconnect = max(5, _env_int("ML_RTSP_MAX_FAILS", 30))
        self._reconnect_delay = max(0.5, _env_float("ML_RTSP_RECONNECT_SEC", 2.0))
        self._open_retry_delay = max(0.5, _env_float("ML_RTSP_OPEN_RETRY_SEC", 3.0))
        self._logged_res = False
        self.thread = threading.Thread(target=self._run, daemon=True, name=f"cam-{label}")

    @staticmethod
    def _open(source: str):
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open RTSP stream: {source}")
        if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    @staticmethod
    def _valid_frame(frame: np.ndarray | None) -> bool:
        if frame is None or not hasattr(frame, "size") or frame.size == 0:
            return False
        if len(frame.shape) < 2:
            return False
        h, w = frame.shape[:2]
        return h >= 32 and w >= 32

    def _release_cap(self) -> None:
        cap = self.cap
        self.cap = None
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

    def _open_cap(self) -> bool:
        self._release_cap()
        try:
            self.cap = self._open(self.rtsp_url)
            self._fail_streak = 0
            return True
        except Exception as exc:
            print(f"[live] Failed to open {self.label}: {exc}")
            self.connected = False
            return False

    def _read_frame(self) -> np.ndarray | None:
        cap = self.cap
        if cap is None:
            return None
        try:
            for _ in range(self.drain_reads):
                if not cap.grab():
                    return None
            ret, frame = cap.retrieve()
            if ret and self._valid_frame(frame):
                return frame
            ret, frame = cap.read()
            if ret and self._valid_frame(frame):
                return frame
        except cv2.error:
            return None
        except Exception:
            return None
        return None

    def _run(self):
        while self.running:
            if self.cap is None:
                if not self._open_cap():
                    time.sleep(self._open_retry_delay)
                    continue

            frame = self._read_frame()
            if frame is not None:
                if not self._logged_res:
                    h, w = frame.shape[:2]
                    self._logged_res = True
                    print(f"[live] {self.label} native stream {w}x{h} (opencv)")
                with self.lock:
                    self.frame = frame
                    self.connected = True
                self._fail_streak = 0
                continue

            self._fail_streak += 1
            self.connected = False
            if self._fail_streak >= self._max_fail_before_reconnect:
                print(
                    f"[live] Reconnecting {self.label} after "
                    f"{self._fail_streak} failed frame read(s)"
                )
                self._release_cap()
                self._fail_streak = 0
                time.sleep(self._reconnect_delay)
            else:
                time.sleep(0.02)

    def get_frame(self) -> np.ndarray | None:
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self):
        self.running = False
        self.thread.join(timeout=2.0)
        self._release_cap()


class FfmpegCameraStream:
    """Native-resolution RTSP reader via ffmpeg MJPEG pipe (no scale/crop)."""

    def __init__(self, rtsp_url: str, label: str, ffmpeg_path: str):
        self.rtsp_url = rtsp_url
        self.label = label
        self.ffmpeg_path = ffmpeg_path
        self.lock = threading.Lock()
        self.frame: np.ndarray | None = None
        self.running = True
        self.connected = False
        self._proc: subprocess.Popen | None = None
        self._fail_streak = 0
        self._max_fail_before_reconnect = max(5, _env_int("ML_RTSP_MAX_FAILS", 30))
        self._reconnect_delay = max(0.5, _env_float("ML_RTSP_RECONNECT_SEC", 2.0))
        self._open_retry_delay = max(0.5, _env_float("ML_RTSP_OPEN_RETRY_SEC", 3.0))
        self._logged_res = False
        self.thread = threading.Thread(target=self._run, daemon=True, name=f"cam-{label}")

    def _ffmpeg_cmd(self) -> list[str]:
        return [
            self.ffmpeg_path,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-fflags",
            "+discardcorrupt+genpts",
            "-err_detect",
            "ignore_err",
            "-i",
            self.rtsp_url,
            "-an",
            "-f",
            "mjpeg",
            "-q:v",
            "2",
            "-",
        ]

    def _stop_proc(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            proc.kill()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _decode_mjpeg_buffer(self, buffer: bytearray) -> np.ndarray | None:
        while True:
            start = buffer.find(b"\xff\xd8")
            end = buffer.find(b"\xff\xd9")
            if start == -1 or end == -1 or end < start:
                return None
            jpg = bytes(buffer[start : end + 2])
            del buffer[: end + 2]
            arr = np.frombuffer(jpg, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is not None and CameraStream._valid_frame(frame):
                return frame
            if not buffer:
                return None

    def _run(self) -> None:
        while self.running:
            self._stop_proc()
            try:
                self._proc = subprocess.Popen(
                    self._ffmpeg_cmd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=0,
                )
            except OSError as exc:
                print(f"[live] Failed to open {self.label} (ffmpeg): {exc}")
                self.connected = False
                time.sleep(self._open_retry_delay)
                continue

            if not self._proc.stdout:
                self._stop_proc()
                time.sleep(self._open_retry_delay)
                continue

            buffer = bytearray()
            self._fail_streak = 0
            while self.running and self._proc.poll() is None:
                try:
                    chunk = self._proc.stdout.read(8192)
                except Exception:
                    chunk = b""
                if not chunk:
                    self._fail_streak += 1
                    if self._fail_streak >= self._max_fail_before_reconnect:
                        break
                    time.sleep(0.02)
                    continue

                buffer.extend(chunk)
                while True:
                    frame = self._decode_mjpeg_buffer(buffer)
                    if frame is None:
                        break
                    if not self._logged_res:
                        h, w = frame.shape[:2]
                        self._logged_res = True
                        print(f"[live] {self.label} native stream {w}x{h} (ffmpeg)")
                    with self.lock:
                        self.frame = frame
                        self.connected = True
                    self._fail_streak = 0

            self.connected = False
            if self.running:
                print(f"[live] Reconnecting {self.label} (ffmpeg)")
                self._stop_proc()
                time.sleep(self._reconnect_delay)

    def get_frame(self) -> np.ndarray | None:
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self) -> None:
        self.running = False
        self._stop_proc()
        self.thread.join(timeout=2.0)


def create_camera_stream(rtsp_url: str, label: str) -> CameraStream | FfmpegCameraStream:
    if _rtsp_decode_backend() == "opencv":
        return CameraStream(rtsp_url, label)
    ffmpeg = _resolve_ffmpeg_path()
    if ffmpeg:
        return FfmpegCameraStream(rtsp_url, label, ffmpeg)
    print(f"[live] ffmpeg not found — falling back to OpenCV for {label}")
    return CameraStream(rtsp_url, label)


def draw_detections(frame: np.ndarray, detections: list[dict[str, Any]], label_scale: float = 0.55) -> np.ndarray:
    if not detections:
        return frame
    output = frame.copy()
    h, _ = output.shape[:2]
    font_scale = max(0.32, label_scale * (h / 720))
    thickness = max(1, int(font_scale * 1.5))
    box_thickness = max(1, int(font_scale * 1.2))
    font = cv2.FONT_HERSHEY_SIMPLEX

    for det in detections:
        name = str(det.get("label", ""))
        conf = float(det.get("confidence", 0))
        x1, y1, x2, y2 = det.get("bbox", [0, 0, 0, 0])
        is_unknown = name.lower() == "unknown" or name.lower().startswith("unknown:")
        is_alert = bool(det.get("alert"))
        if is_alert:
            color = (0, 0, 255)
        elif is_unknown:
            color = (0, 140, 255)
        else:
            color = (0, 220, 0)
        cv2.rectangle(output, (int(x1), int(y1)), (int(x2), int(y2)), color, box_thickness)
        label = f"{name} {conf:.2f}"
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
        text_x = int(x1)
        text_y = max(text_h + 4, int(y1) - 4)
        cv2.rectangle(
            output,
            (text_x, text_y - text_h - 3),
            (text_x + text_w + 4, text_y + baseline + 2),
            (0, 0, 0),
            -1,
        )
        cv2.putText(output, label, (text_x + 2, text_y), font, font_scale, color, thickness, cv2.LINE_AA)
    return output


_GENERIC_FACE_LABELS = frozenset({"", "unknown", "person", "face"})


def _is_generic_face_label(label: str) -> bool:
    value = (label or "").strip().lower()
    if not value or value in _GENERIC_FACE_LABELS:
        return True
    return value.startswith("unknown:")


def filter_enrolled_staff_detections(detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Only show boxes/labels for recognized enrolled staff (attendance-eligible identities)."""
    kept: list[dict[str, Any]] = []
    for det in detections or []:
        if det.get("alert"):
            kept.append(det)
            continue
        # Always keep license-plate OCR overlays
        if str(det.get("model") or "").strip().lower() == "plate":
            kept.append(det)
            continue
        cls = str(det.get("class_name") or det.get("label") or "").strip().lower()
        if cls in ("license_plate", "license plate", "number_plate", "number plate"):
            kept.append(det)
            continue
        if cls not in ("person", "face"):
            continue
        label = str(det.get("label") or "").strip()
        if not label or _is_generic_face_label(label):
            continue
        kept.append(det)
    return kept


def filter_osd_detections(
    detections: list[dict[str, Any]],
    frame_h: int,
    frame_w: int,
    *,
    top_frac: float = 0.14,
    left_frac: float = 0.30,
) -> list[dict[str, Any]]:
    """Drop boxes in the top-left OSD band (typical CCTV date/time overlay)."""
    if not detections or frame_h <= 0 or frame_w <= 0:
        return detections
    x_limit = frame_w * left_frac
    y_limit = frame_h * top_frac
    kept: list[dict[str, Any]] = []
    for det in detections:
        x1, y1, x2, y2 = det.get("bbox", [0, 0, 0, 0])
        cx = (float(x1) + float(x2)) / 2.0
        cy = (float(y1) + float(y2)) / 2.0
        if cx <= x_limit and cy <= y_limit:
            continue
        kept.append(det)
    return kept


def encode_jpeg(frame: np.ndarray, quality: int) -> bytes | None:
    ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return jpeg.tobytes() if ret else None


class _CameraSession:
    def __init__(self, ip: str, stream: CameraStream, rtsp_url: str):
        self.ip = ip
        self.stream = stream
        self.rtsp_url = rtsp_url
        self.lock = threading.Lock()
        self.latest_jpeg: bytes | None = None
        self.latest_detections: list[dict[str, Any]] = []

    def set_frame(self, jpeg: bytes | None, detections: list[dict[str, Any]]):
        with self.lock:
            if jpeg is not None:
                self.latest_jpeg = jpeg
            self.latest_detections = detections


class LiveStreamManager:
    """Runs triple-model inference and serves annotated MJPEG per camera key."""

    def __init__(self):
        self._sessions: dict[str, _CameraSession] = {}
        self._registry: dict[str, str] = {}
        self._purposes: dict[str, str] = {}
        self._lock = threading.Lock()
        self._infer_thread: threading.Thread | None = None
        self._render_thread: threading.Thread | None = None
        self._running = False
        self._face_db: KnownFaceDB | None = None
        self._plate_engine: PlateEngine | None = None
        self._coco_model = None
        self._custom_model = None
        self._smoke_model = None
        self._weapon_model = None
        self._device: str | int = 0
        self._conf = 0.12
        self._iou = 0.45
        self._imgsz = 1280
        self._max_det = 300
        self._osd_filter = True
        self._osd_top = 0.14
        self._osd_left = 0.30
        self._infer_interval = 0.15
        self._jpeg_quality = 92
        self._face_threshold = 0.28
        # Plate OCR: on for purpose=anpr by default; set ML_PLATE_ON_ALL=true for every camera.
        self._plate_on_all = os.getenv("ML_PLATE_ON_ALL", "false").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        self._plate_ocr_every = max(1, _env_int("ML_PLATE_OCR_EVERY", 3))
        self._plate_frame_counters: dict[str, int] = {}
        # 0 = native camera resolution (no downscale). Set ML_LIVE_MAX_WIDTH/HEIGHT to cap (e.g. 3840/2160).
        self._max_width = 0
        self._max_height = 0
        self._stream_fps = max(5, min(_env_int("ML_LIVE_STREAM_FPS", 20), 30))
        self._frame_interval = 1.0 / self._stream_fps
        self._detections: dict[str, list[dict[str, Any]]] = {}
        self._det_lock = threading.Lock()
        self._start_lock = threading.Lock()

    def configure_from_env(self):
        boot_ips = _boot_camera_ips()
        for ip in boot_ips:
            threading.Thread(
                target=self.ensure_camera,
                args=(ip,),
                daemon=True,
                name=f"live-boot-{ip}",
            ).start()

    def _load_infer_settings(self):
        try:
            self._conf = float(os.getenv("ML_YOLO_CONF", str(self._conf)))
        except (TypeError, ValueError):
            pass
        try:
            self._iou = float(os.getenv("ML_YOLO_IOU", str(self._iou)))
        except (TypeError, ValueError):
            pass
        try:
            self._imgsz = max(320, int(os.getenv("ML_YOLO_IMGSZ", str(self._imgsz))))
        except (TypeError, ValueError):
            pass
        try:
            self._max_det = max(1, int(os.getenv("ML_YOLO_MAX_DET", str(self._max_det))))
        except (TypeError, ValueError):
            pass
        self._osd_filter = os.getenv("ML_OSD_FILTER", "true").lower() in ("true", "1", "yes")
        self._osd_enrolled_staff_only = os.getenv("ML_OSD_ENROLLED_STAFF_ONLY", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        try:
            self._osd_top = float(os.getenv("ML_OSD_TOP", str(self._osd_top)))
        except (TypeError, ValueError):
            pass
        try:
            self._osd_left = float(os.getenv("ML_OSD_LEFT", str(self._osd_left)))
        except (TypeError, ValueError):
            pass
        self._max_width = _env_int("ML_LIVE_MAX_WIDTH", self._max_width)
        self._max_height = _env_int("ML_LIVE_MAX_HEIGHT", self._max_height)
        self._jpeg_quality = max(50, min(100, _env_int("ML_LIVE_JPEG_QUALITY", self._jpeg_quality)))

    def _close_session(self, key: str) -> None:
        session = self._sessions.pop(key, None)
        self._detections.pop(key, None)
        if session is not None:
            session.stream.stop()

    def resolve_rtsp_url(self, key: str, rtsp_url: str | None = None) -> str | None:
        key = key.strip()
        explicit = (rtsp_url or "").strip()
        if explicit:
            return explicit
        registered = self._registry.get(key, "").strip()
        if registered:
            return registered
        if not key:
            return None
        cfg = _rtsp_config()
        return build_rtsp_url(key, cfg["user"], cfg["password"], cfg["port"], cfg["path"])

    def register_camera(self, key: str, rtsp_url: str, purpose: str = "") -> bool:
        key = (key or "").strip()
        url = (rtsp_url or "").strip()
        if not key or not url:
            return False
        with self._lock:
            self._registry[key] = url
            if purpose:
                self._purposes[key] = purpose.strip()
            existing = self._sessions.get(key)
            if existing is not None and existing.rtsp_url != url:
                self._close_session(key)
        return True

    def register_cameras_bulk(self, entries: list[dict[str, str]]) -> dict[str, int]:
        registered = 0
        for item in entries:
            key = str(item.get("key") or "").strip()
            url = str(item.get("rtsp_url") or "").strip()
            purpose = str(item.get("purpose") or "").strip()
            if self.register_camera(key, url, purpose=purpose):
                registered += 1
        self.ensure_started()
        return {"registered": registered, "total": len(entries)}

    def get_raw_frame(self, key: str):
        """Latest decoded frame from an existing live RTSP session (no extra connection)."""
        key = (key or "").strip()
        if not key:
            return None
        with self._lock:
            session = self._sessions.get(key)
        if session is None:
            return None
        return session.stream.get_frame()

    def ensure_started(self) -> bool:
        """Start infer/render threads if YOLO is available but loops are not running."""
        self.start()
        return self._running

    def unregister_camera(self, key: str) -> bool:
        key = (key or "").strip()
        if not key:
            return False
        with self._lock:
            self._registry.pop(key, None)
            self._purposes.pop(key, None)
            self._close_session(key)
        return True

    def ensure_camera(self, key: str, rtsp_url: str | None = None) -> bool:
        key = key.strip()
        if not key:
            return False
        url = self.resolve_rtsp_url(key, rtsp_url)
        if not url:
            return False
        with self._lock:
            existing = self._sessions.get(key)
            if existing is not None:
                if existing.rtsp_url == url:
                    return True
                self._close_session(key)
            stream = create_camera_stream(url, key)
            stream.thread.start()
            self._sessions[key] = _CameraSession(key, stream, url)
            self._detections[key] = []
            print(f"[live] Opening: {key}")
            return True

    def start(self):
        with self._start_lock:
            if self._running:
                return
            try:
                self._load_infer_settings()
                coco_weights = resolve_coco_weights_path()
                custom_weights = resolve_custom_weights_path()
                smoke_weights = resolve_smoke_weights_path()
                weapon_weights = resolve_weapon_weights_path()
                if not any([coco_weights, custom_weights, smoke_weights, weapon_weights]):
                    print("[live] No YOLO weights — live annotated streams disabled.")
                    return

                self._coco_model = get_yolo_coco_model()
                self._custom_model = get_yolo_custom_model()
                self._smoke_model = get_yolo_smoke_model()
                self._weapon_model = get_yolo_weapon_model()
                if (
                    self._coco_model is None
                    and self._custom_model is None
                    and self._smoke_model is None
                    and self._weapon_model is None
                ):
                    print("[live] YOLO models unavailable.")
                    return

                self._device = resolve_ml_device()
                cuda = get_cuda_status()
                self._face_db = get_face_db()
                if hasattr(self._face_db, "threshold"):
                    self._face_db.threshold = self._face_threshold
                try:
                    self._plate_engine = get_plate_engine()
                except Exception as exc:
                    print(f"[live] Plate engine unavailable: {exc}")
                    self._plate_engine = None
                plate_ok = bool(self._plate_engine and self._plate_engine.available)
                self._running = True
                self._infer_thread = threading.Thread(target=self._infer_loop, daemon=True, name="live-infer")
                self._render_thread = threading.Thread(target=self._render_loop, daemon=True, name="live-render")
                self._infer_thread.start()
                self._render_thread.start()
                max_label = (
                    "native"
                    if self._max_width <= 0 and self._max_height <= 0
                    else f"{self._max_width}x{self._max_height}"
                )
                print(
                    "[live] Started multi-model streams "
                    f"(device={self._device}, gpu={cuda.get('cuda_device_name') or 'n/a'}, "
                    f"fps={self._stream_fps}, infer_interval={self._infer_interval}s, "
                    f"conf={self._conf}, imgsz={self._imgsz}, display={max_label}, "
                    f"osd_enrolled_staff_only={self._osd_enrolled_staff_only}, "
                    f"rtsp_decode={_rtsp_decode_backend()}, "
                    f"coco={coco_weights or 'off'}, custom={custom_weights or 'off'}, "
                    f"smoke={smoke_weights or 'off'}, weapon={weapon_weights or 'off'}, "
                    f"plate={'on' if plate_ok else 'off'}, plate_on_all={self._plate_on_all})"
                )
            except Exception as exc:
                print(f"[live] start failed: {exc}")
                self._running = False

    def stop(self):
        self._running = False
        if self._infer_thread:
            self._infer_thread.join(timeout=2.0)
        if self._render_thread:
            self._render_thread.join(timeout=2.0)
        with self._lock:
            for session in self._sessions.values():
                session.stream.stop()
            self._sessions.clear()

    def status(self) -> dict[str, Any]:
        with self._lock:
            cameras = []
            for ip, session in self._sessions.items():
                with session.lock:
                    det_count = len(session.latest_detections)
                    has_frame = session.latest_jpeg is not None
                cameras.append(
                    {
                        "ip": ip,
                        "connected": session.stream.connected,
                        "has_frame": has_frame,
                        "detections": det_count,
                    }
                )
        return {
            "running": self._running,
            "inference_device": self._device,
            "plate_only_mode": False,
            "plate_model_loaded": bool(self._plate_engine and self._plate_engine.available),
            "triple_model_mode": (
                self._coco_model is not None
                and self._custom_model is not None
                and self._smoke_model is not None
            ),
            "quad_model_mode": (
                self._coco_model is not None
                and self._custom_model is not None
                and self._smoke_model is not None
                and self._weapon_model is not None
            ),
            "coco_model_loaded": self._coco_model is not None,
            "custom_model_loaded": self._custom_model is not None,
            "smoke_model_loaded": self._smoke_model is not None,
            "weapon_model_loaded": self._weapon_model is not None,
            "dual_model_mode": self._coco_model is not None and self._smoke_model is not None,
            "general_model_loaded": self._coco_model is not None,
            "camera_count": len(cameras),
            "cameras": cameras,
        }

    def get_latest_jpeg(self, ip: str) -> bytes | None:
        session = self._sessions.get(ip)
        if not session:
            return None
        with session.lock:
            return session.latest_jpeg

    def get_detections(self, ip: str) -> list[dict[str, Any]]:
        return list(self.get_detection_snapshot(ip).get("detections") or [])

    def get_detection_snapshot(self, ip: str) -> dict[str, Any]:
        session = self._sessions.get(ip)
        if not session:
            return {
                "detections": [],
                "frame_width": 0,
                "frame_height": 0,
                "display_width": 0,
                "display_height": 0,
            }
        with self._det_lock:
            detections = list(self._detections.get(ip, []))
        raw = session.stream.get_frame()
        if raw is not None:
            infer_h, infer_w = raw.shape[:2]
            limited = self._limit_size(raw)
            display_h, display_w = limited.shape[:2]
        else:
            infer_w, infer_h = 0, 0
            display_w, display_h = 0, 0
        return {
            "detections": detections,
            "frame_width": int(infer_w),
            "frame_height": int(infer_h),
            "display_width": int(display_w),
            "display_height": int(display_h),
        }

    def iter_mjpeg(self, key: str) -> Iterator[bytes]:
        boundary = b"--frame\r\n"
        while True:
            frame = self.get_latest_jpeg(key)
            if frame:
                yield boundary
                yield b"Content-Type: image/jpeg\r\n"
                yield f"Content-Length: {len(frame)}\r\n\r\n".encode()
                yield frame
                yield b"\r\n"
            time.sleep(self._frame_interval)

    def iter_mjpeg_raw(self, key: str) -> Iterator[bytes]:
        session = self._sessions.get(key)
        if session is None:
            return
        boundary = b"--frame\r\n"
        quality = max(70, min(self._jpeg_quality, 98))
        while True:
            raw = session.stream.get_frame()
            if raw is not None:
                jpeg = encode_jpeg(self._limit_size(raw), quality)
                if jpeg:
                    yield boundary
                    yield b"Content-Type: image/jpeg\r\n"
                    yield f"Content-Length: {len(jpeg)}\r\n\r\n".encode()
                    yield jpeg
                    yield b"\r\n"
            time.sleep(self._frame_interval)

    def _prepare_frame(self, frame: np.ndarray):
        """Keep full resolution; YOLO letterboxes via imgsz."""
        return frame, 1.0, 1.0

    def _predict(self, model, frame: np.ndarray, *, min_conf: float | None = None, classes=None):
        use_half = self._device != "cpu"
        conf = max(self._conf, min_conf) if min_conf is not None else self._conf
        kwargs = {
            "device": self._device,
            "conf": conf,
            "iou": self._iou,
            "imgsz": self._imgsz,
            "max_det": self._max_det,
            "half": use_half,
            "verbose": False,
        }
        if classes is not None:
            kwargs["classes"] = list(classes)
        return model.predict(frame, **kwargs)

    def _should_run_plates(self, camera_key: str) -> bool:
        if self._plate_engine is None or not self._plate_engine.available:
            return False
        if self._plate_on_all:
            return True
        purpose = (self._purposes.get(camera_key) or "").strip().lower()
        return purpose == "anpr"

    def _infer_frame(
        self,
        frame: np.ndarray,
        *,
        camera_key: str = "",
        run_plates: bool = False,
    ) -> list[dict[str, Any]]:
        infer_frame, sx, sy = self._prepare_frame(frame)
        coco_detections: list[dict[str, Any]] = []
        custom_detections: list[dict[str, Any]] = []
        smoke_detections: list[dict[str, Any]] = []
        weapon_detections: list[dict[str, Any]] = []

        if self._coco_model is not None:
            results = self._predict(self._coco_model, infer_frame, classes=ALLOWED_COCO_CLASS_IDS)
            coco_detections = parse_yolo_result(
                frame,
                results[0],
                sx=sx,
                sy=sy,
                recognize_faces=True,
                smoke_model=False,
                model_tag="coco",
                face_db=self._face_db,
            )

        if self._custom_model is not None:
            custom_ids = custom_only_class_ids(self._custom_model)
            results = self._predict(
                self._custom_model,
                infer_frame,
                classes=custom_ids or None,
            )
            custom_detections = keep_custom_classes_only(
                parse_yolo_result(
                    frame,
                    results[0],
                    sx=sx,
                    sy=sy,
                    recognize_faces=False,
                    smoke_model=False,
                    model_tag="custom",
                    face_db=None,
                )
            )

        if self._smoke_model is not None:
            results = self._predict(self._smoke_model, infer_frame, min_conf=SMOKE_FIRE_MIN_CONF)
            smoke_detections = parse_yolo_result(
                frame,
                results[0],
                sx=sx,
                sy=sy,
                recognize_faces=False,
                smoke_model=True,
                model_tag="smoke",
                face_db=None,
            )

        if self._weapon_model is not None:
            results = self._predict(self._weapon_model, infer_frame, min_conf=WEAPON_MIN_CONF)
            weapon_detections = parse_yolo_result(
                frame,
                results[0],
                sx=sx,
                sy=sy,
                recognize_faces=False,
                weapon_model=True,
                model_tag="weapon",
                face_db=None,
            )

        detections = merge_triple_detections(coco_detections, custom_detections, smoke_detections)
        detections.extend(weapon_detections)

        if run_plates and self._plate_engine is not None:
            counter = self._plate_frame_counters.get(camera_key, 0) + 1
            self._plate_frame_counters[camera_key] = counter
            if counter % self._plate_ocr_every == 0:
                try:
                    plate_dets = self._plate_engine.detect_and_read(
                        frame,
                        camera_key=camera_key,
                        save=True,
                    )
                    detections.extend(plate_dets)
                except Exception as exc:
                    print(f"[live] Plate OCR error [{camera_key}]: {exc}")

        if self._osd_filter:
            h, w = frame.shape[:2]
            detections = filter_osd_detections(
                detections,
                h,
                w,
                top_frac=self._osd_top,
                left_frac=self._osd_left,
            )
        return detections

    def _infer_loop(self):
        while self._running:
            loop_start = time.time()
            with self._lock:
                sessions = list(self._sessions.values())
            for session in sessions:
                if not self._running:
                    break
                raw = session.stream.get_frame()
                if raw is None:
                    continue
                frame = raw.copy()
                try:
                    detections = self._infer_frame(
                        frame,
                        camera_key=session.ip,
                        run_plates=self._should_run_plates(session.ip),
                    )
                    fh, fw = frame.shape[:2]
                    for det in detections:
                        det["frame_width"] = int(fw)
                        det["frame_height"] = int(fh)
                    with self._det_lock:
                        self._detections[session.ip] = detections
                except Exception as exc:
                    print(f"[live] Inference error [{session.ip}]: {exc}")
            elapsed = time.time() - loop_start
            wait = self._infer_interval - elapsed
            if wait > 0:
                time.sleep(wait)

    def _limit_size(self, frame: np.ndarray) -> np.ndarray:
        """Downscale only when ML_LIVE_MAX_WIDTH/HEIGHT cap is set; 0 = native passthrough."""
        h, w = frame.shape[:2]
        max_w = self._max_width
        max_h = self._max_height
        if max_w <= 0 and max_h <= 0:
            return frame
        if max_w <= 0:
            max_w = w
        if max_h <= 0:
            max_h = h
        if w <= max_w and h <= max_h:
            return frame
        scale = min(max_w / w, max_h / h)
        return cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    def _prepare_attendance_frame(self, frame: np.ndarray, target_width: int) -> np.ndarray:
        """Native main-stream frame; only downscale when wider than target (never upscale)."""
        h, w = frame.shape[:2]
        if w <= 0 or h <= 0:
            return frame
        target_width = max(640, min(4096, int(target_width or 3840)))
        if w <= target_width:
            return frame
        scale = target_width / float(w)
        return cv2.resize(
            frame,
            (target_width, max(1, int(h * scale))),
            interpolation=cv2.INTER_AREA,
        )

    def iter_mjpeg_attendance(self, key: str, *, target_width: int = 3840) -> Iterator[bytes]:
        """Full main-stream MJPEG for attendance clips (higher quality than raw preview)."""
        session = self._sessions.get(key)
        if session is None:
            return
        boundary = b"--frame\r\n"
        quality = 98 if target_width >= 2560 else max(90, min(self._jpeg_quality, 98))
        while True:
            raw = session.stream.get_frame()
            if raw is not None:
                prepared = self._prepare_attendance_frame(raw, target_width)
                jpeg = encode_jpeg(prepared, quality)
                if jpeg:
                    yield boundary
                    yield b"Content-Type: image/jpeg\r\n"
                    yield f"Content-Length: {len(jpeg)}\r\n\r\n".encode()
                    yield jpeg
                    yield b"\r\n"
            time.sleep(self._frame_interval)

    def _render_loop(self):
        while self._running:
            with self._lock:
                sessions = list(self._sessions.values())
            for session in sessions:
                live = session.stream.get_frame()
                if live is None:
                    continue
                with self._det_lock:
                    boxes = list(self._detections.get(session.ip, []))
                if self._osd_enrolled_staff_only:
                    boxes = filter_enrolled_staff_detections(boxes)
                annotated = draw_detections(live, boxes)
                annotated = self._limit_size(annotated)
                jpeg = encode_jpeg(annotated, self._jpeg_quality)
                session.set_frame(jpeg, boxes)
            time.sleep(self._frame_interval)


_manager: LiveStreamManager | None = None
_manager_lock = threading.Lock()


def get_live_manager() -> LiveStreamManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = LiveStreamManager()
        return _manager
