---
title: Linguo Translator
emoji: 🌍
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Linguo: Intelligent Multilingual Translation Hub

Linguo is a modern, feature-rich translation application featuring a beautiful, interactive frontend powered by an advanced FastAPI machine learning backend. Under the hood, Linguo uses Meta's **NLLB-200** (`facebook/nllb-200-distilled-600M`) — a single multilingual model that translates accurately between **100+ languages**, no per-pair models required.

---

## 🚀 Key Features

*   **100+ Language Translation**: Pick any source and target language from the dropdowns and translate between them directly — not just English and French. The backend auto-detects the source language if you don't set it explicitly.
*   **Intelligent File Translation**: Upload **PDF, DOCX, or PPTX** files. The application extracts the text content, auto-detects the source language, translates it into whichever target language you choose, and reconstructs the output paragraph-by-paragraph to preserve structural layout.
*   **Dynamic Document Export**: Download translated documents directly from the UI as professionally formatted **Word (.docx)** or **PDF (.pdf)** files.
*   **AI Rephrase**: Restructure sentences and improve copy using back-translation (e.g., `EN ➔ FR ➔ EN`). This classic NLP technique rewrites text while preserving core semantic meaning.
*   **Translation Journal**: Keep track of recent translations with an automatic local history widget, storing entries safely in your browser's local storage.
*   **Aesthetic Theme Engine**: Toggle between a vibrant dark mode and a clean, premium light mode with smooth transitions, customized glassmorphic blur effects, and responsive layout designs.

---

## 🛠️ Technology Stack

### Backend
*   **FastAPI**: High-performance web framework for building the translation REST APIs.
*   **NLLB-200 (Meta AI)**: Offline-first, state-of-the-art many-to-many machine translation model via Hugging Face's `transformers` library — covers 100+ languages with a single model.
*   **PyTorch**: Engine for running model inference.
*   **langdetect**: Auto-detects the source language of typed text or uploaded files.
*   **Text Parsers**: `pdfplumber`, `python-docx`, and `python-pptx` for extraction from documents.
*   **Document Generators**: `python-docx` and `reportlab` for compiling and downloading output files.

### Frontend
*   **HTML5 & Vanilla CSS**: Dynamic modern layout utilizing flexbox/grid, custom variables, neon glow accents, and CSS keyframe animations.
*   **Vanilla JavaScript**: State management, language-selector dropdowns populated from the backend, speech synthesis (Web Speech API), asynchronous API interaction, translation history journal, and theme state persistence.

---

## 📁 Repository Structure

```
translator/
├── app.py              # FastAPI Backend (APIs, Model Inference & File Parsers)
├── index.html          # Web Frontend (UI, Styles, App Controller)
├── requirements.txt    # Python dependencies
├── Dockerfile           # Container build definition
└── README.md            # Documentation (This file)
```

> Note: this project was previously named `eng-french-translator`. Rename your local/remote folder to `translator` to match — no code changes are needed for the rename itself.

---

## ⚡ Getting Started

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your machine.

### 2. Setup the Backend
Clone this repository (or navigate to its folder) and install the dependencies:

```bash
# Set up virtual environment
python -m venv venv
source venv/bin/activate          # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Backend
Start the Uvicorn development server:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

> [!NOTE]
> On the first startup, the app downloads the NLLB-200 distilled model (~2.4GB) from Hugging Face. This can take several minutes depending on your connection. Subsequent startups load it instantly from the local cache.
>
> The model runs on CPU by default. Translating a sentence typically takes 1-3 seconds on CPU; a GPU will make this noticeably faster if available.

### 4. Serve the Frontend
You can open `index.html` directly in your browser, or serve it using Python's built-in HTTP server:

```bash
python -m http.server 3000
```
Then visit `http://localhost:3000` in your web browser.

---

## 🔌 API Endpoints Reference

Linguo exposes the following FastAPI endpoints:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET`  | `/languages` | List of all supported language codes and display names. |
| `POST` | `/translate` | Translate raw text between any two supported languages. Auto-detects `source_lang` if omitted; defaults `target_lang` to French (or English if source is French). |
| `POST` | `/translate-file` | Extract and translate text from uploaded `.pdf`, `.docx`, or `.pptx` files. Source is auto-detected; pass `target_lang` to choose the output language. |
| `POST` | `/rephrase` | Back-translate input text (EN⇄FR pivot) to restructure and rephrase. |
| `POST` | `/generate-docx` | Generates a formatted Word document (`.docx`) from text. |
| `POST` | `/generate-pdf` | Generates a styled, readable PDF (`.pdf`) from text. |
| `GET` | `/health` | Check backend availability, model load status, and language count. |

### Example translation request:
```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world, how are you today?", "source_lang": "en", "target_lang": "de"}'
```

**Response:**
```json
{
  "translated_text": "Hallo Welt, wie geht es dir heute?",
  "source_lang": "en",
  "target_lang": "de"
}
```

---

## 🛡️ Production & Deployment Recommendations

*   **CORS Configuration**: The current backend middleware permits all origins (`allow_origins=["*"]`). Restrict this to your specific production frontend URL in `app.py` before hosting publicly.
*   **Compute Power & Memory**: The NLLB-200-distilled-600M model consumes roughly 2-3GB of RAM once loaded. Ensure your hosting server has at least 4GB RAM available.
*   **Cold Starts**: Avoid serverless endpoints (like AWS Lambda) that scale to 0. Loading the model on a cold start takes too long. Run the app on persistent containers/VMs.
*   **Rate Limiting**: Translation model execution is CPU/GPU-intensive. Protect endpoints using API rate limiters (e.g. `slowapi` or Cloudflare rules) in public environments.
*   **Language Detection Coverage**: automatic language detection (via `langdetect`) reliably covers ~55 major languages. For languages outside that set, users should pick the source language explicitly from the dropdown rather than relying on auto-detect.
