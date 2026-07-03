# Linguo: Intelligent EN ↔ FR Translation Hub

Linguo is a modern, feature-rich translation application featuring a beautiful, interactive frontend powered by an advanced FastAPI machine learning backend. Under the hood, Linguo uses local, pre-trained Hugging Face transformer models (`Helsinki-NLP/opus-mt`) for high-fidelity, bidirectional English-French translation, file parsing, and semantic rephrasing.

---

## 🚀 Key Features

*   **Bidirectional Text Translation**: Instantly translates between English and French. The backend automatically detects the source language, and the interface provides easy-to-use swap controls.
*   **Intelligent File Translation**: Upload **PDF, DOCX, or PPTX** files. The application extracts the text content, performs translation, and reconstructs the output paragraph-by-paragraph to preserve structural layout.
*   **Dynamic Document Export**: Download translated documents directly from the UI as professionally formatted **Word (.docx)** or **PDF (.pdf)** files.
*   **AI Rephrase**: Restructure sentences and improve copy using back-translation (e.g., `EN ➔ FR ➔ EN`). This classic NLP technique rewrites text while preserving core semantic meaning.
*   **Translation Journal**: Keep track of recent translations with an automatic local history widget, storing entries safely in your browser's local storage.
*   **Aesthetic Theme Engine**: Toggle between a vibrant dark mode and a clean, premium light mode with smooth transitions, customized glassmorphic blur effects, and responsive layout designs.

---

## 🛠️ Technology Stack

### Backend
*   **FastAPI**: High-performance web framework for building the translation REST APIs.
*   **Helsinki-NLP (MarianMT)**: Offline-first state-of-the-art machine translation models via Hugging Face's `transformers` library.
*   **PyTorch**: Engine for running model inference.
*   **Text Parsers**: `pdfplumber`, `python-docx`, and `python-pptx` for extraction from documents.
*   **Document Generators**: `python-docx` and `reportlab` for compiling and downloading output files.

### Frontend
*   **HTML5 & Vanilla CSS**: Dynamic modern layout utilizing flexbox/grid, custom variables, neon glow accents, and CSS keyframe animations.
*   **Vanilla JavaScript**: State management, speech synthesis (Web Speech API), asynchronous API interaction, translation history journal, and theme state persistence.

---

## 📁 Repository Structure

```
Translator/
├── app.py              # FastAPI Backend (APIs, Model Inference & File Parsers)
├── index.html          # Web Frontend (UI, Styles, App Controller)
├── requirements.txt    # Python dependencies
└── README.md           # Documentation (This file)
```

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

# Additional dependencies for document support (if not already installed)
pip install pdfplumber python-docx python-pptx reportlab
```

### 3. Run the Backend
Start the Uvicorn development server:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

> [!NOTE]
> On the first startup, the app will automatically download two pretrained Helsinki-NLP models (~300MB each) from Hugging Face. This will take a couple of minutes depending on your internet connection. Subsequent startups will load them instantly from the local cache.

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
| `POST` | `/translate` | Translate raw text. Auto-detects language if `source_lang` is omitted. |
| `POST` | `/translate-file` | Extract and translate text from uploaded `.pdf`, `.docx`, or `.pptx` files. |
| `POST` | `/rephrase` | Back-translate input text to restructure and rephrase. |
| `POST` | `/generate-docx` | Generates a formatted Word document (`.docx`) from text. |
| `POST` | `/generate-pdf` | Generates a styled, readable PDF (`.pdf`) from text. |
| `GET` | `/health` | Check backend availability and verify loaded models. |

### Example translation request:
```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world, how are you today?"}'
```

**Response:**
```json
{
  "translated_text": "Bonjour le monde, comment allez-vous aujourd'hui?",
  "source_lang": "en",
  "target_lang": "fr"
}
```

---

## 🛡️ Production & Deployment Recommendations

*   **CORS Configuration**: The current backend middleware permits all origins (`allow_origins=["*"]`). Restrict this to your specific production frontend URL in `app.py` before hosting publicly.
*   **Compute Power & Memory**: PyTorch models consume ~300MB RAM each (~600MB total). Ensure your hosting server has at least 1-2GB RAM.
*   **Cold Starts**: Avoid serverless endpoints (like AWS Lambda) that scale to 0. Loading the models on a cold start takes too long. Run the app on persistent containers/VMs.
*   **Rate Limiting**: Translation model execution is CPU/GPU-intensive. Protect endpoints using API rate limiters (e.g. `slowapi` or Cloudflare rules) in public environments.
