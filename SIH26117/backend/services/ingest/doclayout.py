"""DocLayout-YOLO layout analysis — runs in the ingest worker on CPU.

Uses the official opendatalab/DocLayout-YOLO (DocStructBench, imgsz 1024)
weights baked at /app/models/, consumed through the `doclayout_yolo` runtime
(AGPL-3.0). Inference is CPU-only so the ollama GPU allocation is untouched.
Every failure degrades gracefully: layout is additive metadata, never fatal.
"""
from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from backend.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

IMGSZ = 1024
CONF_THRESHOLD = 0.25
MAX_BLOCKS_PER_PAGE = 220
MODEL_NAME = "DocLayout-YOLO-DocStructBench-imgsz1024"

_model_cache = None
_names_cache: list[str] | None = None

_PATH_CANDIDATES = (
    settings.doclayout_model_path,
    Path(__file__).resolve().parents[4] / "models" / "doclayout_yolo_docstructbench_imgsz1024.pt",
)


@dataclass
class Block:
    klass: str
    confidence: float
    bbox: list[float] = field(default_factory=list)  # [x1, y1, x2, y2] normalised 0..1


def _model_file() -> str:
    for p in _PATH_CANDIDATES:
        try:
            if p and p.exists():
                return str(p)
        except OSError:
            continue
    return ""


def layout_available() -> bool:
    if not _model_file():
        return False
    try:
        import doclayout_yolo  # noqa: F401
        return True
    except Exception:
        return False


def _load_runtime():
    from doclayout_yolo import YOLOv10  # vendored ultralytics port


def _get_model():
    """Lazily load and cache the DocLayout-YOLO model (CPU)."""
    global _model_cache, _names_cache
    if _model_cache is not None:
        return _model_cache
    path = _model_file()
    if not path:
        logger.warning("doclayout_model_missing")
        return None
    try:
        _load_runtime()
        from doclayout_yolo import YOLOv10
    except Exception as exc:  # pragma: no cover - import-shape fallback
        logger.warning("doclayout_runtime_import_failed", exc=str(exc))
        return None

    model = YOLOv10(path)
    _names_cache = None
    raw_names = getattr(model, "names", None)
    if isinstance(raw_names, dict):
        _names_cache = [raw_names[i] for i in sorted(raw_names)]
    elif isinstance(raw_names, list):
        _names_cache = [str(n) for n in raw_names]
    _model_cache = model
    logger.info("doclayout_model_loaded", path=path, classes=len(_names_cache or []))
    return model


def _predict_blocks(image) -> list[Block]:
    model = _get_model()
    names = _names_cache
    if model is None:
        return []
    results = model.predict(
        [image], device="cpu", imgsz=IMGSZ, conf=CONF_THRESHOLD, verbose=False
    )
    if not results:
        return []
    r = results[0]
    boxes = getattr(r, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    import numpy as np

    img_h, img_w = image.shape[:2]
    blocks: list[Block] = []
    for det in boxes:
        cls_id = int(det.cls[0])
        conf = float(det.conf[0])
        name = names[cls_id] if names and cls_id < len(names) else f"class_{cls_id}"
        x1, y1, x2, y2 = [float(v) for v in det.xyxy[0].tolist()]
        blocks.append(
            Block(
                klass=name,
                confidence=round(conf, 3),
                bbox=[
                    round(x1 / img_w, 4),
                    round(y1 / img_h, 4),
                    round(x2 / img_w, 4),
                    round(y2 / img_h, 4),
                ],
            )
        )
    blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
    return blocks[:MAX_BLOCKS_PER_PAGE]


def _page_to_rgb(pix):
    import numpy as np

    samples = np.frombuffer(pix.samples, dtype=np.uint8)
    if pix.n == 1:
        samples = samples.reshape(pix.height, pix.width)
        samples = np.stack([samples] * 3, axis=-1)
    elif pix.n == 4:
        samples = samples.reshape(pix.height, pix.width, 4)[:, :, :3]
    else:
        samples = samples.reshape(pix.height, pix.width, 3)
    return samples


def _analyze_pdf(raw: bytes) -> list[dict]:
    import fitz

    out: list[dict] = []
    with fitz.open(stream=raw, filetype="pdf") as doc:
        for pno in range(len(doc)):
            page = doc[pno]
            zoom = 2.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            blocks = _predict_blocks(_page_to_rgb(pix))
            out.append({"page": pno + 1, "blocks": [to_dict(b) for b in blocks]})
    return out


def _analyze_image(raw: bytes) -> list[dict]:
    import numpy as np
    from PIL import Image

    with Image.open(io.BytesIO(raw)) as im:
        img = np.asarray(im.convert("RGB"))
    blocks = _predict_blocks(img)
    return [{"page": 1, "blocks": [to_dict(b) for b in blocks]}]


def to_dict(b: Block) -> dict:
    return {"class": b.klass, "confidence": b.confidence, "bbox": b.bbox}


async def analyze_bytes(raw: bytes, mime: str, filename: str) -> list[dict]:
    """Run layout detection over a PDF or a single image.

    Returns [{"page": int, "blocks": [Block-as-dict, ...]}, ...].
    """
    if not layout_available():
        raise RuntimeError("DocLayout-YOLO model/runtime not available")

    lower = filename.lower()

    def _run():
        if lower.endswith(".pdf") or "pdf" in (mime or "").lower():
            return _analyze_pdf(raw)
        return _analyze_image(raw)

    return await asyncio.to_thread(_run)