# AuthFlow Backend

AI-powered prior authorization form generation for medical practices. A staff member pastes a clinical note and selects an insurance payer — the backend generates a complete, policy-compliant PA form in seconds.

---

## What it does

- **PA Form Generation** — Takes a clinical note and payer, returns a fully structured prior authorization form with policy citations
- **Appeal Letter Generation** — Writes appeal letters that quote the payer's own policy language against their denial
- **RAG-powered payer policies** — Each payer's criteria are stored in a vector database and retrieved at query time for accurate, payer-specific output
- **5 major payers supported** — Blue Cross IL, Aetna, UnitedHealthcare, Cigna, Humana

---

## Tech stack

- **FastAPI** — REST API
- **Gemini 2.0 Flash** — LLM for form and appeal generation
- **LangChain** — LLM orchestration
- **ChromaDB** — Vector store for payer policy retrieval (RAG)
- **sentence-transformers** — Embeddings

---

## Getting started

### 1. Clone and install

```bash
git clone <repo-url>
cd authflow-backend
pip install -r requirements.txt
```

### 2. Set up environment

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

```
GOOGLE_API_KEY=your_gemini_api_key   # from aistudio.google.com (free)
OPENAI_API_KEY=optional_fallback
CHROMA_DB_PATH=./data/chroma_db
DEMO_MODE=0
```

### 3. Start the server

```bash
export $(grep -v "^#" .env | grep -v "^$" | xargs) && uvicorn app.main:app --port 8001
```

Server starts at `http://localhost:8001`. Interactive API docs at `http://localhost:8001/docs`.

---

## API endpoints

### `POST /generate-pa`
Generate a prior authorization form.

```json
{
  "clinical_note": "Patient: 52-year-old female with 4-week history of progressive lower back pain...",
  "payer": "bluecross_il",
  "procedure_type": "CT Myelogram"
}
```

### `POST /generate-appeal`
Generate an appeal letter for a denied PA.

```json
{
  "clinical_note": "...",
  "payer": "bluecross_il",
  "denial_reason": "Medical necessity not established"
}
```

### `GET /payers`
Returns the list of supported payers with display names.

### `GET /health`
Returns server status, RAG load state, and demo mode flag.

---

## Supported payers

| ID | Name |
|----|------|
| `bluecross_il` | Blue Cross Blue Shield of Illinois |
| `aetna` | Aetna |
| `unitedhealthcare` | UnitedHealthcare |
| `cigna` | Cigna |
| `humana` | Humana |

---

## Demo mode

Set `DEMO_MODE=1` in `.env` to return hardcoded responses without any API calls. Useful as a fallback during demos if the API is unavailable.

---

## Project structure

```
authflow-backend/
├── app/
│   ├── main.py              # FastAPI app, startup, CORS
│   ├── models.py            # Pydantic request/response models
│   ├── form_generator.py    # PA form generation logic
│   ├── appeal_generator.py  # Appeal letter generation logic
│   ├── rag_engine.py        # ChromaDB ingestion and retrieval
│   ├── payer_config.py      # Payer definitions and policy criteria
│   └── routes/
│       ├── pa.py            # /generate-pa endpoint
│       ├── appeal.py        # /generate-appeal endpoint
│       └── payers.py        # /payers endpoint
├── scripts/
│   └── ingest_policies.py   # Script to ingest payer policy PDFs
├── data/
│   └── payer_policies/      # Payer policy PDFs (not committed)
├── .env.example
└── requirements.txt
```
