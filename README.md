# SME LLM BNPL Advisor — AI Marathon (AIC)

**Autonomous Sales Engineer + BNPL intelligence for Malaysian SMEs**

Flutter web/mobile client and FastAPI backend that help SMEs move from **client brief → designed solution → priced quote → BNPL / grant / credit advice**, grounded in transaction data and Malaysian financing schemes.

| | URL |
|---|-----|
| **Web app (GitHub Pages)** | https://mizn08.github.io/SME-LLM/ |
| **API (Render)** | https://sme-advisor-api-pp6d.onrender.com/docs |
| **Source** | https://github.com/mizn08/SME-LLM |

---

## Latest enhancements (AIC)

| Area | What's new |
|------|------------|
| **Autonomous Sales Engineer** | LLM-supervised agent (`sales_engineer_agent.py`) — workflow plan, tool loop (search → validate → ship → tax → quote), guardrails, DB-persisted quotes |
| **Unstructured input** | `POST /sales-agent/parse-client-transcript` — PDF, TXT, DOCX, MD, JSON, CSV → budget, location, category, constraints |
| **BNPL financing sync** | Quote grand total flows into RAG BNPL Chat via `financing_quote_advice` |
| **Business value metrics** | Cycle reduction %, time/cost saved, annual ROI on Sales Engineer tab |
| **Profile sync** | Active SME profile badge; quiz and advisor use session `sme_id` (not hardcoded) |
| **LLM stack** | DeepSeek-V3.2-TEE via Chutes (dual key rotation); shared `llm_client.py` with BM25 fallback |
| **OCR & insights** | Tesseract invoice/receipt pipeline with quality gates and normalized line items |
| **Branding** | App logo in header, drawer, onboarding, favicon, and PWA icons |
| **Guardrails** | Prompt injection detection, budget cap, illegal action block, tool prerequisites |

**User journey:** Home → Design & Finance → BNPL Advisor (Chat · Agents · ML · Guided · **Sales Engineer**) → Funding → History

---

## Architecture (high level)

```
Flutter Web/Mobile
       │
       ▼
   FastAPI
       ├── Sales Engineer agent (LLM plan + tools + guardrails)
       ├── RAG chat (BM25 / Chroma + optional DeepSeek)
       ├── Multi-agent orchestrator (Grant · BNPL · Cash)
       ├── ML predict (XGBoost + decision engine)
       └── PostgreSQL / SQLite ← transactions, quotes, schemes, catalog
```

Optional LLM answers are **grounded in retrieved documents**; quote line prices come from the **product catalog**, not the model.

---

## System requirements

| Component | Requirement |
|-----------|-------------|
| **Backend** | Python 3.11+ (3.13 tested locally) |
| **Database** | SQLite (local) or PostgreSQL 15+ (Docker / Render) |
| **Frontend** | Flutter 3.24+ — install via `scripts/install_flutter.ps1` or [flutter.dev](https://flutter.dev) |
| **OCR (optional)** | [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) on PATH (Windows: `winget install UB-Mannheim.TesseractOCR`) |
| **Docker (optional)** | Docker Desktop + Compose v2 |

---

## Quick start (local — recommended)

### 1. Clone and configure

```powershell
git clone https://github.com/mizn08/SME-LLM.git
cd SME-LLM
copy .env.example .env
```

Edit `.env` and set `CHUTES_API_KEY` (and optional `CHUTES_API_KEY_1`) for live LLM features. The app still runs offline with BM25 + rule fallbacks if keys are empty.

### 2. Start the API (SQLite)

```powershell
cd backend
pip install -r requirements.txt
.\run_local.ps1
```

API: http://127.0.0.1:8000/docs · Health: http://127.0.0.1:8000/health

### 3. Start the web app

In a **second terminal**:

```powershell
cd SME-LLM
.\scripts\run_local_web.ps1
```

This opens Flutter web in Chrome with `API_BASE=http://localhost:8000`.

**First run:** Drawer → **Upload** → **Try sample data**, then open **BNPL Advisor → Sales Engineer** and use **Run demo script mode**.

---

## Quick start (Docker + PostgreSQL)

```powershell
cd SME-LLM
copy .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| API / Swagger | http://localhost:8000/docs |
| PostgreSQL | `localhost:5432` (credentials in `.env`) |

Build web against local API:

```powershell
.\scripts\build_web.ps1 -ApiBase http://127.0.0.1:8000
.\scripts\serve_web.ps1
```

---

## Configuration

Copy `.env.example` → `.env` in the project root.

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres connection string, or leave unset for SQLite via `run_local.ps1` |
| `CHUTES_API_KEY` / `CHUTES_API_KEY_1` | Chutes.ai keys for DeepSeek-V3.2-TEE |
| `CHUTES_CHAT_MODEL` | Default: `deepseek-ai/DeepSeek-V3.2-TEE` |
| `OPENAI_API_KEY` | Fallback LLM if Chutes unset |
| `USE_VECTOR_RAG` | `true` = Chroma embeddings; `false` = BM25 only (faster on Render free tier) |
| `ML_MODELS_DIR` | Path to trained `.pkl` models |

Backend reads `.env` from the repo root (`backend/../.env`).

---

## Deploy to GitHub Pages + Render

### Web (automatic on push to `main`)

1. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**
2. Push to `main` — workflow `.github/workflows/deploy-gh-pages.yml` builds Flutter web and publishes to  
   **https://mizn08.github.io/SME-LLM/**

The workflow sets `API_BASE=https://sme-advisor-api-pp6d.onrender.com`.

Manual build (same as CI):

```powershell
cd mobile_app
flutter pub get
flutter build web --release --base-href /SME-LLM/ --web-renderer html --dart-define=API_BASE=https://sme-advisor-api-pp6d.onrender.com
```

Upload `mobile_app/build/web` to Pages, or rely on the GitHub Action.

### API (Render)

See [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md) and [`deploy/render/README.md`](deploy/render/README.md).

Set on Render: `DATABASE_URL`, `USE_VECTOR_RAG=false` (recommended on free tier), and `CHUTES_API_KEY`.

---

## Key API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness + feature flags |
| `GET` | `/sme/{id}/dashboard` | KPIs and charts |
| `GET` | `/sme/{id}/profile` | Active SME profile |
| `POST` | `/predict` | BNPL vs grant vs credit recommendation |
| `POST` | `/chat` | RAG BNPL chat (optional LLM) |
| `POST` | `/agent/advise` | Multi-agent Grant / BNPL / Cash |
| `POST` | `/sales-agent/run` | Autonomous Sales Engineer → quote + metrics |
| `POST` | `/sales-agent/parse-client-transcript` | Unstructured transcript → requirements |
| `GET` | `/business-value/metrics` | Quote ROI metrics |
| `GET` | `/quote/history/{sme_id}` | Saved agent quotes |
| `POST` | `/upload-csv` | Transaction CSV upload |
| `POST` | `/upload-invoice` | OCR invoice/receipt |

Full list: Swagger at `/docs`.

---

## Running tests

```powershell
cd backend
pip install -r requirements.txt
python -m pytest tests/ -q
```

---

## Project layout

```
SME-LLM/
├── backend/                 # FastAPI, agents, RAG, ML
│   ├── app/services/        # sales_engineer_agent, rag_service, llm_client, …
│   ├── run_local.ps1        # SQLite local API
│   └── tests/
├── mobile_app/              # Flutter client
│   ├── assets/images/       # app_logo.png
│   └── lib/widgets/         # sales_engineer_tab, app_logo, …
├── scripts/
│   ├── run_local_web.ps1    # Flutter web → local API
│   └── build_web.ps1        # Production web build
├── .github/workflows/       # CI + GitHub Pages deploy
├── docker-compose.yml
└── .env.example
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `backend/run_local.ps1` | Local API with SQLite |
| `scripts/run_local_web.ps1` | Flutter web in Chrome (local API) |
| `scripts/build_web.ps1` | Build web (`-ApiBase` for production API) |
| `scripts/serve_web.ps1` | Serve `build/web` on port 8080 |
| `scripts/install_flutter.ps1` | Install Flutter SDK into `./flutter` |
| `start.ps1` | Docker Compose (backend + Postgres) |

---

## Seeded demo data

After first API boot: SMEs **1–3** (Kopi Maju, Harapan Agro, Urban Digital), six months of transactions, BNPL offers, micro-credit lines, and government schemes.

---

## Synthetic datasets (AIC)

Generate **15+ demo datasets** (transactions, forecasts, OCR invoices, transcripts, ML rows):

```powershell
cd backend
python ml_pipeline/scripts/generate_aic_datasets.py
```

Output: `backend/ml_pipeline/data/datasets/` (see catalog in `datasets/README.md`)  
Bundled in the app: `mobile_app/assets/datasets/`

| Dataset | Use |
|---------|-----|
| `01_sme1_kopi_maju_12m_uplift.csv` | **Forecast demo** — 12-month revenue uplift → dashed forecast line on Home chart |
| `04` + `05` income/expense split | Multi-file upload test |
| `08_bnpl_simulation_scenarios.csv` | Simulator purchase scenarios |
| `ocr/invoices/*.png` | Insights → scan invoice (Tesseract) |
| `transcripts/*.txt` | Sales Engineer unstructured brief |

In the app: **Upload** → tap **12-month forecast demo** chip, then open **Home** for the chart.

**Manual demo files (tomorrow):** see [`demo_session/`](../demo_session/) — CSV + PNG + transcript ready to upload from File Explorer.

To refresh seeded DB transactions (SQLite):

```powershell
cd backend
python scripts/reinit_sqlite.py
.\run_local.ps1
```

---

## Machine learning (optional retrain)

```powershell
cd backend
python ml_pipeline/scripts/generate_synthetic_data.py
python ml_pipeline/scripts/train_models.py
```

Models load from `backend/app/ml_models/` when present.

---

## Further documentation

| Doc | Content |
|-----|---------|
| [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md) | Render API deployment |
| [`docs/UPGRADES.md`](docs/UPGRADES.md) | Feature changelog |
| [`docs/AI_ROADMAP.md`](docs/AI_ROADMAP.md) | AI layer roadmap |
| [`mobile_app/README.md`](mobile_app/README.md) | Flutter UI map |

---

## License

See repository license file. Built for **AI Marathon (AIC)** — LLM + agentic integration for Malaysian SME financing and solution design.
