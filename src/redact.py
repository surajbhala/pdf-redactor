import fitz
from typing import Dict, List, Optional, Tuple
from .config import RedactionConfig
from .logger import get_logger
from .analyzer import build_presidio_analyzer
from typing import List
from presidio_analyzer import RecognizerResult
from redaction_engine import RedactionEngine
log = get_logger(__name__)
def map_entities_to_rects(page: fitz.Page, results: List[RecognizerResult]) -> List[fitz.Rect]:
    """
    Map Presidio-detected entities to bounding boxes in a PDF page
    using word-level coordinates. Works well for tables & multi-column layouts.
    """
    rects = []
    words = page.get_text("words")  # [x0, y0, x1, y1, word, block_no, line_no, word_no]
    if not words:
        return rects

    # Flatten words into (start_idx, end_idx, bbox, text)
    text = " ".join([w[4] for w in words])
    word_positions = []
    offset = 0
    for w in words:
        word = w[4]
        start = text.find(word, offset)
        if start == -1:
            continue
        end = start + len(word)
        word_positions.append((start, end, fitz.Rect(w[0], w[1], w[2], w[3]), word))
        offset = end

    for r in results:
        entity_text = text[r.start:r.end].strip()
        if not entity_text:
            continue

        # Collect words that fall inside this entity span
        matched_rects = [
            wp[2] for wp in word_positions if not (wp[1] <= r.start or wp[0] >= r.end)
        ]

        if matched_rects:
            # Merge all bounding boxes covering the entity
            union = matched_rects[0]
            for rect in matched_rects[1:]:
                union |= rect
            rects.append(union)

    return rects
# def map_entities_to_rects(page: fitz.Page, page_text: str, entities) -> List[fitz.Rect]:
#     rects: List[fitz.Rect] = []
#     for ent in entities:
#         substr = page_text[ent.start:ent.end]
#         if not substr.strip():
#             continue
#         try:
#             rects.extend(page.search_for(substr))
#         except Exception:
#             pass
#     return rects

def apply_redactions(doc: fitz.Document,
                     rects_per_page: Dict[int, List[fitz.Rect]],
                     placeholder: Optional[str],
                     remove_header_logo_px: int = 0) -> None:
    for i, page in enumerate(doc):
        if remove_header_logo_px and page.rect.height > 0:
            bar = fitz.Rect(page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y0 + remove_header_logo_px)
            page.add_redact_annot(bar, text=placeholder or "", fill=(1, 1, 1))
        for r in rects_per_page.get(i, []):
            page.add_redact_annot(r, text=placeholder or "", fill=(0, 0, 0))
        page.apply_redactions()

def auto_redact_pdf(file_bytes: bytes,
                    cfg: RedactionConfig,
                    page_range: Optional[Tuple[int, int]] = None) -> Tuple[bytes, Dict[int, List[fitz.Rect]]]:
    analyzer = build_presidio_analyzer(cfg)
    rects_per_page: Dict[int, List[fitz.Rect]] = {}
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc):
            page_num = i + 1
            if page_range and not (page_range[0] <= page_num <= page_range[1]):
                continue
            text = page.get_text("text") or ""
            if text.strip():
                ents = analyzer.analyze(text=text, entities=cfg.entities, language="en")
                ents = [r for r in ents if r.score >= cfg.confidence_threshold]
                rects = map_entities_to_rects(page,  ents)
                if rects:
                    rects_per_page[i] = rects
        out_doc = fitz.open()
        out_doc.insert_pdf(doc)
        apply_redactions(out_doc, rects_per_page, cfg.placeholder_text, cfg.remove_header_logo_px)
        out_bytes = out_doc.tobytes()
    return out_bytes, rects_per_page
