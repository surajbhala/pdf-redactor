This project is a Python-based Proof of Concept (PoC) for secure PII redaction in PDF documents.
It supports both automatic redaction (via Microsoft Presidio) and manual redaction (via interactive UI with Streamlit).
Designed for scalability, modularity, and cloud-readiness (AWS / container-based deployments).

✨ Features

🔒 Automatic Redaction using Presidio
 for PII entities

✍️ Manual Redaction (draw rectangles or crop regions interactively)

📑 Table-aware Redaction using pdfplumber for accurate cell-level redaction (**TBD under development**)

🖼️ Logo/Object Removal via manual drawing tools

📥 Bulk Upload Support for PDFs up to ~300 pages

📤 Downloadable Redacted Outputs as new PDFs

🧩 Modular design (RedactionEngine) for easy integration into other apps (FastAPI, Celery, AWS Lambda)

☁️ Cloud Deployment Ready with AWS S3, ECS, API Gateway, and IAM

📂 Project Structure
project-root/
│── app/
│   ├── main.py              # Streamlit entrypoint
│   ├── redaction_engine.py  # Core redaction engine (Presidio + pdfplumber + PyMuPDF)
│   ├── utils.py             # Shared helper functions
│
│── requirements.txt         # Python dependencies
│── .gitignore               # Ignore venv, cache, temp files
│── README.md                # Project documentation

⚙️ Installation
1. Clone the repo
git clone https://github.com/surajbhala/pdf-redactor.git
cd pdf-redactor


2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate     # Linux/Mac
.venv\Scripts\activate        # Windows

3. Install dependencies
pip install -r requirements.txt

🚀 Usage
Run the Streamlit app
streamlit run app/main.py

Workflow

Upload a PDF (up to ~300 pages).

Choose Auto Redaction (Presidio) or Manual Redaction (draw boxes).

Preview the result.

Download the redacted PDF.
