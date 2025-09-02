import re
import asyncio
import streamlit as st
import fitz
from streamlit_cropper import st_cropper

from src.config import RedactionConfig, DEFAULT_ENTITIES
from src.redact import auto_redact_pdf
from src.utils import page_to_image, bundle_zip
from src.manual import add_manual_redaction

st.set_page_config(page_title="PDF Redactor", layout="wide")
st.title("PDF PII Redaction – PoC")

mode = st.sidebar.radio("Redaction Mode", ["Auto (Presidio)", "Manual (Cropper)", "Combined (Auto + Manual)"])

# -------------------------
# MODE 1: AUTO
# -------------------------
if mode == "Auto (Presidio)":
    with st.sidebar:
        entities = st.multiselect("Entities", DEFAULT_ENTITIES,
                                  default=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"])
        conf = st.slider("Confidence threshold", 0.0, 1.0, 0.5, 0.05)
        placeholder = st.text_input("Placeholder", "[REDACTED]")
        remove_logo_px = st.number_input("Remove header px", min_value=0, max_value=500, value=0)
        rng = st.text_input("Page range", "")

        cfg = RedactionConfig(
            entities=entities,
            confidence_threshold=conf,
            placeholder_text=placeholder,
            remove_header_logo_px=remove_logo_px
        )

    files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

    if files:
        async def process_all():
            tasks = []
            for f in files:
                data = f.read()
                page_range = None
                m = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", rng)
                if m:
                    start, end = int(m.group(1)), int(m.group(2) or m.group(1))
                    page_range = (min(start, end), max(start, end))
                tasks.append(asyncio.to_thread(auto_redact_pdf, data, cfg, page_range))
            return await asyncio.gather(*tasks)

        results = asyncio.run(process_all())
        zip_data = {}
        for f, (redacted, rects) in zip(files, results):
            st.success(f"Redacted: {f.name}")
            with fitz.open(stream=redacted, filetype="pdf") as doc:
                st.image(page_to_image(doc.load_page(0)))
            st.download_button(f"⬇️ {f.name} redacted", data=redacted,
                               file_name=f.name.replace(".pdf", "_redacted.pdf"),
                               mime="application/pdf")
            zip_data[f.name.replace(".pdf", "_redacted.pdf")] = redacted
        st.download_button("Download all (ZIP)", data=bundle_zip(zip_data),
                           file_name="redacted_bundle.zip")

# -------------------------
# MODE 2: MANUAL
# -------------------------
elif mode == "Manual (Cropper)":
    file = st.file_uploader("Upload a PDF", type=["pdf"], accept_multiple_files=False)
    if file:
        data = file.read()
        doc = fitz.open(stream=data, filetype="pdf")
        total_pages = doc.page_count

        page_number = st.slider("Select Page", 1, total_pages, 1)
        page_index = page_number - 1
        page = doc.load_page(page_index)
        page_img = page_to_image(page, 1.5)

        st.markdown("### ✍️ Draw a rectangle to redact")
        crop_box = st_cropper(page_img, return_type="box", box_color="red", aspect_ratio=None)

        if crop_box and st.button("Apply Redaction"):
            doc = add_manual_redaction(doc, page_index, crop_box, page_img)
            st.success("Manual redaction applied!")
            st.image(page_to_image(doc.load_page(page_index), 1.5))

            redacted_bytes = doc.tobytes()
            st.download_button(
                "Download Redacted PDF",
                data=redacted_bytes,
                file_name=file.name.replace(".pdf", "_manual_redacted.pdf"),
                mime="application/pdf"
            )

# -------------------------
# MODE 3: COMBINED (AUTO + MANUAL)
# -------------------------
else:
    with st.sidebar:
        entities = st.multiselect("Entities", DEFAULT_ENTITIES,
                                  default=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"])
        conf = st.slider("Confidence threshold", 0.0, 1.0, 0.5, 0.05)
        placeholder = st.text_input("Placeholder", "[REDACTED]")
        remove_logo_px = st.number_input("Remove header px", min_value=0, max_value=500, value=0)

        cfg = RedactionConfig(
            entities=entities,
            confidence_threshold=conf,
            placeholder_text=placeholder,
            remove_header_logo_px=remove_logo_px
        )

    file = st.file_uploader("Upload a PDF", type=["pdf"], accept_multiple_files=False)

    if file:
        data = file.read()

        # Step 1: Auto-redact
        if "doc_bytes" not in st.session_state:
            st.info("Running auto-redaction with Presidio...")
            auto_bytes, rects = auto_redact_pdf(data, cfg)
            st.session_state["doc_bytes"] = auto_bytes
            st.session_state["doc"] = fitz.open(stream=auto_bytes, filetype="pdf")
        doc = st.session_state["doc"]

        total_pages = doc.page_count
        st.success("Auto-redaction done ✅ Now refine manually across pages")

        # Step 2: Manual refinement across multiple pages
        page_number = st.slider("Select Page", 1, total_pages, 1)
        page_index = page_number - 1
        page = doc.load_page(page_index)
        page_img = page_to_image(page, 1.5)

        st.markdown("✅ ###Refine: Draw extra rectangles to redact")
        crop_box = st_cropper(page_img, return_type="box", box_color="blue", aspect_ratio=None)

        if crop_box and st.button("Apply Manual Fix to Page"):
            st.session_state["doc"] = add_manual_redaction(doc, page_index, crop_box, page_img, placeholder)
            st.success(f"Manual fix applied on page {page_number}!")
            st.image(page_to_image(doc.load_page(page_index), 1.5))

        # Step 3: Final download after multiple fixes
        if st.button("Finalize & Download"):
            combined_bytes = st.session_state["doc"].tobytes()
            st.download_button(
                "Download Final (Auto+Manual) PDF",
                data=combined_bytes,
                file_name=file.name.replace(".pdf", "_final_redacted.pdf"),
                mime="application/pdf"
            )
