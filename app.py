"""
English <-> French Translator — Backend API
=============================================
Bidirectional, open-vocabulary translation using pretrained Helsinki-NLP
opus-mt models (via Hugging Face transformers). No training required —
these models already know general English and French.

Endpoints:
  POST /translate          - Translate text (auto-detects language)
  POST /translate-file     - Upload PDF / DOCX / PPTX, get translated text
  POST /rephrase           - AI rephrase via back-translation (EN→FR→EN)
  GET  /health             - Health check

Run:
    pip install -r requirements.txt
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""

from contextlib import asynccontextmanager
from functools import lru_cache
import re
import io

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import MarianMTModel, MarianTokenizer
from langdetect import detect, DetectorFactory, LangDetectException

# Make langdetect deterministic
DetectorFactory.seed = 0

MODEL_NAMES = {
    "en": "Helsinki-NLP/opus-mt-en-fr",  # English -> French
    "fr": "Helsinki-NLP/opus-mt-fr-en",  # French  -> English
}

MAX_INPUT_LENGTH = 500        # chars for /translate
MAX_FILE_TEXT    = 15_000     # chars extracted from uploaded files

# ── Model loading ──────────────────────────────────────────────────────
models: dict[str, tuple[MarianTokenizer, MarianMTModel]] = {}


def load_models():
    for lang, name in MODEL_NAMES.items():
        tokenizer = MarianTokenizer.from_pretrained(name)
        model = MarianMTModel.from_pretrained(name)
        model.eval()
        models[lang] = (tokenizer, model)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading translation models... (first run downloads ~300MB per model)")
    load_models()
    print("Models loaded. Ready to translate.")
    yield
    models.clear()


app = FastAPI(title="EN<->FR Translator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import FileResponse

@app.get("/")
def serve_index():
    return FileResponse("index.html")


# ── Schemas ────────────────────────────────────────────────────────────
class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_INPUT_LENGTH)
    source_lang: str | None = Field(
        default=None,
        description="'en' or 'fr'. Omit to auto-detect.",
    )


class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str


class RephraseResponse(BaseModel):
    original: str
    rephrased: str


class FileTranslateResponse(BaseModel):
    filename: str
    source_lang: str
    target_lang: str
    translated_text: str
    char_count: int


# ── Language detection ─────────────────────────────────────────────────
def detect_language(text: str) -> str:
    try:
        code = detect(text)
    except LangDetectException:
        return "en"
    return "fr" if code == "fr" else "en"


from fastapi.responses import StreamingResponse

# ── Core translation helpers ───────────────────────────────────────────
@lru_cache(maxsize=512)
def translate_cached(text: str, source_lang: str) -> str:
    tokenizer, model = models[source_lang]
    batch = tokenizer([text], return_tensors="pt", padding=True, truncation=True)
    generated = model.generate(**batch, max_new_tokens=512)
    return tokenizer.decode(generated[0], skip_special_tokens=True)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def translate_full(text: str, source_lang: str) -> str:
    """Translate by splitting into sentences so nothing is silently dropped."""
    sentences = split_sentences(text)
    if len(sentences) <= 1:
        return translate_cached(text, source_lang)
    return " ".join(translate_cached(s, source_lang) for s in sentences)


def translate_preserving_layout(text: str, source_lang: str) -> str:
    """Translates paragraph-by-paragraph and line-by-line to preserve layout,
    line breaks, and document flow."""
    paragraphs = text.split("\n\n")
    translated_paragraphs = []
    for para in paragraphs:
        if not para.strip():
            translated_paragraphs.append("")
            continue
        lines = para.split("\n")
        translated_lines = []
        for line in lines:
            if not line.strip():
                translated_lines.append("")
                continue
            translated_lines.append(translate_full(line, source_lang))
        translated_paragraphs.append("\n".join(translated_lines))
    return "\n\n".join(translated_paragraphs)


# ── File text extraction ───────────────────────────────────────────────
def extract_pdf(data: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n\n".join(pages).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {e}")


def extract_docx(data: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read DOCX: {e}")


def extract_pptx(data: bytes) -> str:
    try:
        from pptx import Presentation
        prs = Presentation(io.BytesIO(data))
        slides = []
        for slide in prs.slides:
            texts = [shape.text for shape in slide.shapes if hasattr(shape, "text") and shape.text.strip()]
            if texts:
                slides.append("\n".join(texts))
        return "\n\n".join(slides).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read PPTX: {e}")


EXTRACTORS = {
    ".pdf":  extract_pdf,
    ".docx": extract_docx,
    ".pptx": extract_pptx,
}


# ── Endpoints ──────────────────────────────────────────────────────────
@app.post("/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text must not be empty.")

    source_lang = request.source_lang
    if source_lang is None:
        source_lang = detect_language(text)
    elif source_lang not in MODEL_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"source_lang must be one of {list(MODEL_NAMES)}, got '{source_lang}'.",
        )

    target_lang = "fr" if source_lang == "en" else "en"

    try:
        translated = translate_full(text, source_lang)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {e}")

    return TranslateResponse(
        translated_text=translated,
        source_lang=source_lang,
        target_lang=target_lang,
    )


@app.post("/translate-file", response_model=FileTranslateResponse)
async def translate_file(
    file: UploadFile = File(...),
    source_lang: str | None = Form(default=None),
):
    """Accept a PDF, DOCX or PPTX file and return the translated text."""
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in EXTRACTORS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Supported: .pdf, .docx, .pptx",
        )

    data = await file.read()
    raw_text = EXTRACTORS[ext](data)

    if not raw_text:
        raise HTTPException(status_code=422, detail="No text found in the file.")

    # Truncate to avoid huge latency
    if len(raw_text) > MAX_FILE_TEXT:
        raw_text = raw_text[:MAX_FILE_TEXT] + "\n\n[Truncated — file too large]"

    # Detect / validate language
    if source_lang is None:
        source_lang = detect_language(raw_text[:500])
    elif source_lang not in MODEL_NAMES:
        raise HTTPException(status_code=400, detail=f"Invalid source_lang '{source_lang}'.")

    target_lang = "fr" if source_lang == "en" else "en"

    try:
        translated = translate_preserving_layout(raw_text, source_lang)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {e}")

    return FileTranslateResponse(
        filename=filename,
        source_lang=source_lang,
        target_lang=target_lang,
        translated_text=translated,
        char_count=len(raw_text),
    )


class DocumentGenerateRequest(BaseModel):
    text: str
    filename: str


@app.post("/generate-docx")
def generate_docx(request: DocumentGenerateRequest):
    try:
        from docx import Document
        doc = Document()
        
        # Style the docx neatly
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Arial'
        font.size = 11
        
        paragraphs = request.text.split("\n\n")
        for para in paragraphs:
            if para.strip():
                p = doc.add_paragraph()
                lines = para.split("\n")
                for idx, line in enumerate(lines):
                    if idx > 0:
                        p.add_run("\n")
                    p.add_run(line)
            else:
                doc.add_paragraph()
                
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        headers = {
            "Content-Disposition": f"attachment; filename={request.filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Word doc: {e}")


@app.post("/generate-pdf")
def generate_pdf(request: DocumentGenerateRequest):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'ElegantBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10.5,
            leading=15,
            textColor='#453F57',
            alignment=TA_LEFT,
            spaceAfter=10
        )
        
        story = []
        paragraphs = request.text.split("\n\n")
        for para in paragraphs:
            if para.strip():
                formatted_text = para.replace("\n", "<br/>")
                p = Paragraph(formatted_text, body_style)
                story.append(p)
            else:
                story.append(Spacer(1, 10))
                
        doc.build(story)
        buffer.seek(0)
        
        headers = {
            "Content-Disposition": f"attachment; filename={request.filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")


@app.post("/rephrase")
def rephrase(request: TranslateRequest):
    """Rephrase text via back-translation: EN→FR→EN (or FR→EN→FR).
    This is a classic NLP paraphrasing technique that naturally
    restructures phrasing while preserving meaning."""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text must not be empty.")

    source_lang = request.source_lang or detect_language(text)
    if source_lang not in MODEL_NAMES:
        raise HTTPException(status_code=400, detail=f"Invalid source_lang '{source_lang}'.")

    pivot_lang = "fr" if source_lang == "en" else "en"

    try:
        pivot     = translate_full(text, source_lang)   # EN → FR
        rephrased = translate_full(pivot, pivot_lang)   # FR → EN
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rephrase failed: {e}")

    return RephraseResponse(original=text, rephrased=rephrased)


@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": list(models.keys())}
