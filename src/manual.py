import fitz
from typing import Dict, List
from PIL import Image
from .utils import page_to_image
from .logger import get_logger

log = get_logger(__name__)

def add_manual_redaction(doc: fitz.Document,
                         page_index: int,
                         crop_box: Dict,
                         page_img: Image.Image,
                         placeholder: str = "[REDACTED]") -> fitz.Document:
    """Apply a manual crop-box redaction to the given PDF document."""

    page = doc[page_index]

    # Scale crop box back to PDF coordinates
    img_w, img_h = page_img.size
    page_rect = page.rect

    x0 = crop_box['left'] * (page_rect.width / img_w)
    y0 = crop_box['top'] * (page_rect.height / img_h)
    x1 = (crop_box['left'] + crop_box['width']) * (page_rect.width / img_w)
    y1 = (crop_box['top'] + crop_box['height']) * (page_rect.height / img_h)

    rect = fitz.Rect(x0, y0, x1, y1)
    log.info("Manual redaction added on page %d: %s", page_index+1, rect)

    page.add_redact_annot(rect, text=placeholder, fill=(0, 0, 0))
    page.apply_redactions()

    return doc
