import fitz  # PyMuPDF
import pdfplumber
import logging
from presidio_analyzer import AnalyzerEngine, RecognizerResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedactionEngine:
    def __init__(self, language="en"):
        self.analyzer = AnalyzerEngine()
        self.language = language

    def analyze_text(self, text: str) -> list[RecognizerResult]:
        """Run Presidio on given text."""
        return self.analyzer.analyze(text=text, language=self.language)

    def extract_rects_from_page(self, page, results: list[RecognizerResult]):
        """Map Presidio results to word bounding boxes using pdfplumber."""
        rects = []
        words = page.extract_words()

        if not words or not results:
            return rects

        page_text = page.extract_text()

        for r in results:
            entity_text = page_text[r.start:r.end].strip()
            matched_rects = [
                fitz.Rect(w["x0"], w["top"], w["x1"], w["bottom"])
                for w in words if entity_text in w["text"]
            ]

            if matched_rects:
                # Merge multiple word boxes into one rect if entity spans multiple words
                union = matched_rects[0]
                for rect in matched_rects[1:]:
                    union |= rect
                rects.append(union)

        return rects

    def extract_rects_from_tables(self, page, results: list[RecognizerResult]):
        """Special handling for tables using pdfplumber's table extraction."""
        rects = []
        tables = page.find_tables()

        if not tables or not results:
            return rects

        for table in tables:
            for row in table.cells:
                for cell in row:
                    if cell is None:
                        continue
                    cell_text = page.within_bbox(cell).extract_text()
                    if not cell_text:
                        continue

                    # Run Presidio on the cell text
                    cell_results = self.analyzer.analyze(text=cell_text, language=self.language)

                    if cell_results:
                        rects.append(fitz.Rect(cell[0], cell[1], cell[2], cell[3]))

        return rects

    def map_entities_to_rects(self, pdf_path: str) -> dict[int, list[fitz.Rect]]:
        """Return dictionary of page -> redaction rects."""
        rects_by_page = {}

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                results = self.analyze_text(page_text)

                word_rects = self.extract_rects_from_page(page, results)
                table_rects = self.extract_rects_from_tables(page, results)

                rects_by_page[page_num] = word_rects + table_rects

        return rects_by_page

    def redact_pdf(self, pdf_path: str, output_path: str):
        """Perform redaction using PyMuPDF."""
        rects_by_page = self.map_entities_to_rects(pdf_path)

        doc = fitz.open(pdf_path)
        for page_num, rects in rects_by_page.items():
            page = doc[page_num]
            for rect in rects:
                page.add_redact_annot(rect, fill=(0, 0, 0))  # Black box
            page.apply_redactions()

        doc.save(output_path, garbage=4, deflate=True)
        logger.info(f"Redacted PDF saved: {output_path}")
