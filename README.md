# BNPL Advisor for SMEs (Malaysia) — AIC2026

End-to-end prototype: **FastAPI + PostgreSQL + scikit-learn / XGBoost** backend and **Flutter** mobile client for Malaysian SME financing decisions (BNPL vs micro-credit vs grants).

## Live demo (Render)

| | URL |
|---|-----|
| **Web app** | **https://sme-advisor-web-rk8t.onrender.com/** |
| **API (Swagger)** | https://sme-advisor-api.onrender.com/docs |
| **Health** | https://sme-advisor-api.onrender.com/health |

First visit may take ~30–60 s if the free tier was idle (cold start). In the app: menu → **Upload** → **Try sample data** before using Health / Simulate / Grants.

## Quick start (no Docker — SQLite)

If Docker/PostgreSQL are not installed:

```powershell
cd bnpl_advisor_mobile\backend
.\run_local.ps1
```

Uses `bnpl_local.db` in the backend folder. API: `http://127.0.0.1:8000/docs`

## Running with Docker (backend + PostgreSQL)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Compose v2.

```powershell
cd bnpl_advisor_mobile
copy .env.example .env
docker compose up --build
# or: make up
```

| Service | URL |
|---------|-----|
| **API / Swagger** | http://localhost:8000/docs |
| **Health** | http://localhost:8000/health |
| **PostgreSQL** | `localhost:5432` (user/pass/db from `.env`) |
| **pgAdmin** (optional) | `docker compose --profile tools up -d` → http://localhost:5050 |

**What happens on startup**

1. `db` starts and passes a healthcheck.
2. `backend` waits for Postgres (`scripts/wait_for_db.py`).
3. `scripts/init_db.py` creates tables and seeds 3 SMEs, **~6 months of transactions**, BNPL offers, micro-credit lines, and government schemes.
4. Uvicorn serves the API on port **8000**.

**Flutter connection**

| Target | API base URL |
|--------|----------------|
| Android emulator | `http://10.0.2.2:8000` |
| iOS simulator / desktop | `http://127.0.0.1:8000` |
| Physical phone (same Wi‑Fi) | `http://<your-PC-LAN-IP>:8000` |

```powershell
flutter run --dart-define=API_BASE=http://10.0.2.2:8000
```

**Makefile shortcuts:** `make up`, `make down`, `make logs`, `make health`, `make tools` (pgAdmin).

ML `.pkl` files are baked into the image at `backend/app/ml_models/` (also kept under `backend/ml_pipeline/models/` for training).

## Demo with web (recommended)

For **APC / judge demos**, a **website is easier than an APK**: one link, no install, no “unknown app” warnings, no rebuilding the APK when your API URL changes.

| Approach | Best for | Link you share |
|----------|----------|----------------|
| **Web + Render** | Judges anywhere (stable URL) | **https://sme-advisor-web-rk8t.onrender.com/** — see [`deploy/render/README.md`](deploy/render/README.md) |
| **Web + ngrok** | Quick test from your PC | `https://….ngrok-free.app` (Flutter web) |
| **Swagger only** | Backup / API-focused rubric | `https://….onrender.com/docs` or ngrok `/docs` |
| **Web on same Wi‑Fi** | Classroom, no ngrok | `http://<your-PC-IP>:8080` |
| **APK** | Optional “mobile app” proof | Install file or download link (more setup) |

### A0 — Render (recommended for submission — no ngrok)

Deploy API + Postgres on [Render](https://render.com). Full guide: **[`deploy/render/README.md`](deploy/render/README.md)**.

1. Create **PostgreSQL** + **Web Service** (Docker, `backend/Dockerfile.render` — slim, faster on free tier).
2. Set `DATABASE_URL` to `postgresql+psycopg2://...` (convert from Render’s `postgres://` URL).
3. Set `USE_VECTOR_RAG=false` on free tier for faster deploys.
4. Build web locally: `.\scripts\build_web.ps1 -ApiBase https://YOUR-SERVICE.onrender.com`
5. Host `mobile_app/build/web` on Render **Static Site**, Vercel, or Netlify.

Share: **https://sme-advisor-web-rk8t.onrender.com/** + https://sme-advisor-api.onrender.com/docs

### A — Public demo with ngrok (from your PC)

**Terminal 1 — API**

```powershell
cd bnpl_advisor_mobile
docker compose up -d --build
```

**Terminal 2 — expose API**

```powershell
ngrok http 8000
```

Copy the `https://….ngrok-free.app` URL (no trailing slash).

**Terminal 3 — build & serve web** (bake API URL into the build)

```powershell
cd bnpl_advisor_mobile
.\scripts\build_web.ps1 -ApiBase https://YOUR-NGROK-API-ID.ngrok-free.app
.\scripts\serve_web.ps1
```

**Terminal 4 — expose web**

```powershell
ngrok http 8080
```

Share the **8080** ngrok URL with judges (full app UI). Put the **8000** `/docs` URL in your report as the API link.

Shortcut that prints these steps after Docker starts:

```powershell
.\scripts\demo_web_public.ps1
```

### B — Same Wi‑Fi (no ngrok)

Phone and PC on the same network:

```powershell
cd bnpl_advisor_mobile
.\scripts\build_web.ps1
.\start_web_demo.ps1
```

Open the URL shown (e.g. `http://192.168.x.x:8080`) on the phone browser. Allow Windows Firewall for ports **8000** and **8080** if prompted.

### C — Local dev (your laptop only)

```powershell
docker compose up -d
cd mobile_app
flutter pub get
flutter run -d chrome
```

Chrome uses `http://127.0.0.1:8000` for the API automatically on web.

### Web vs APK

| | Web | APK |
|---|-----|-----|
| Judge opens link | Yes | Must install |
| API URL change | Re-run `build_web.ps1 -ApiBase …` | Rebuild APK |
| CSV upload | Yes (browser) | Yes |
| Biometrics | No | Yes (optional) |

APK build (optional): see `scripts/serve_apk.ps1` and `mobile_app/README.md`.

### Backend environment

| Variable | Default (`.env.example`) |
|----------|--------------------------|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@db:5432/bnpl_db` (in Compose) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `postgres` / `postgres` / `bnpl_db` |
| `ML_MODELS_DIR` | `/app/backend/app/ml_models` (container) |

## API overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload-csv` | Multipart: `sme_id`, `file` (CSV) |
| `GET` | `/sme/{id}/dashboard` | KPIs + monthly revenue/expense series |
| `POST` | `/predict` | Purchase simulation + ML/rule recommendation + SHAP-style factors |
| `GET` | `/gov-aid` | Government / agency schemes |
| `GET` | `/sme/{id}/predictions` | Prediction history |
| `GET` | `/predictions/{id}` | Single prediction detail |
| `GET` | `/model-metrics` | Demo transparency metrics for the Performance screen |
| `GET` | `/health` | Liveness + v2 feature flags |
| `POST` | `/chat` | **v2 RAG** — question over SME transactions + grants/BNPL catalog |
| `POST` | `/agent/advise` | **v2 LangChain multi-agent** — Grant, BNPL, Cash specialists |
| `POST` | `/chat/reindex` | Refresh BM25 index after CSV upload |

### v4: APC+ product upgrades

See **[docs/UPGRADES.md](docs/UPGRADES.md)** for the full list. Highlights:

- `POST /compare` — BNPL vs grant vs credit vs cash (+ SST, Islamic filter)
- Dashboard **alerts**, **runway forecast**, anomaly count
- **EN / MS** language, **dark mode**, onboarding, offline cache, PDF/share, biometrics
- Optional **JWT** (`POST /auth/token`, demo password `sme2026`), rate limits, audit log
- CI (`.github/workflows/ci.yml`), HTTPS nginx example, DB backup script

### v3: Vector DB, unsupervised, bandit, RL, OCR, fine-tune stub

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/sme/{id}/insights` | KMeans cluster + IsolationForest anomalies |
| `GET` | `/clusters` | All SME cluster assignments |
| `GET` | `/bandit/stats` | UCB multi-armed bandit arm statistics |
| `POST` | `/bandit/feedback` | Reward signal after simulation (thumbs up/down in app) |
| `POST` | `/rl/advise` | Tabular Q-learning policy + bandit blend |
| `POST` | `/rlhf/preference` | Human preference pair (chosen vs rejected) |
| `POST` | `/upload-invoice` | Tesseract OCR → parsed transaction rows |
| `GET` | `/llm/finetune/status` | Fine-tune adapter readiness |

- **Vector RAG:** Chroma + FastEmbed (`USE_VECTOR_RAG=true`, falls back to BM25).
- **Mobile:** Drawer → **AI Insights** (clusters, anomalies, bandit, invoice OCR).
- **Train:** optional LightGBM — `pip install lightgbm` then re-run `train_models.py`.
- **Fine-tune stub:** `python backend/ml_pipeline/scripts/finetune_sme_llm.py`

```powershell
pip install -r backend/requirements-v3.txt -r backend/requirements-v3-ocr.txt
docker compose up -d --build
```

### v2: RAG, LangChain agents, AWS

- **RAG:** BM25 retrieval (`rank-bm25`) over your DB; optional **OpenAI** generative answers when `OPENAI_API_KEY` is set.
- **Agents:** Three specialists + supervisor; uses existing ML/rules engine as tools.
- **Mobile:** AI Advisor tab → **RAG Chat** | **Agents** | **ML Insight**.
- **AWS:** See [`deploy/aws/README.md`](deploy/aws/README.md) and `deploy/aws/docker-compose.prod.yml`.

```powershell
pip install -r backend/requirements.txt -r backend/requirements-v2.txt
# Optional
$env:OPENAI_API_KEY="sk-..."
```

Production on EC2:

```bash
docker compose -f docker-compose.yml -f deploy/aws/docker-compose.prod.yml up -d --build
```

## Machine learning

```powershell
cd bnpl_advisor_mobile\backend
python ml_pipeline\scripts\generate_synthetic_data.py
python ml_pipeline\scripts\train_models.py
```

- Training data: `ml_pipeline/data/ml_training.csv` (synthetic scenarios + labels).
- Transactions sample: `ml_pipeline/data/sample_sme_transactions.csv` (640 rows across 3 SMEs).
- Saved models: `ml_pipeline/models/*.pkl` (used automatically by `/predict` when present).

**SHAP:** Optional. Core `requirements.txt` omits `shap` so Windows installs without C++ build tools. Docker installs `requirements-shap.txt`. The API falls back to heuristic attributions if SHAP is unavailable.

Notebook: `backend/ml_pipeline/notebooks/train_models.ipynb`.

## Flutter app

```powershell
cd bnpl_advisor_mobile\mobile_app
flutter create .   # generates android/ ios/ web/ if missing
flutter pub get
flutter run
```

- **Android emulator:** backend base URL defaults to `http://10.0.2.2:8000`.
- **iOS simulator / desktop:** defaults to `http://127.0.0.1:8000`.
- **Physical device:** `flutter run --dart-define=API_BASE=http://<your-LAN-IP>:8000`

See `mobile_app/README.md` for UI map (Health / Simulate / AI Advisor with RAG+Agents / Grants / Performance) and CSV format.

## Scripts

| Script | Purpose |
|--------|---------|
| `start.ps1` | Docker Compose for backend |
| `start.sh` | Same (Unix) |
| `scripts/build_web.ps1` | Build Flutter web (`-ApiBase` for ngrok) |
| `scripts/serve_web.ps1` | Serve `mobile_app/build/web` on port 8080 |
| `scripts/demo_web_public.ps1` | Start Docker API + print ngrok/web steps |
| `deploy/render/README.md` | **Deploy API + DB on Render** (no ngrok) |
| `start_web_demo.ps1` | API + web on LAN IP (same Wi‑Fi) |
| `scripts/serve_apk.ps1` | Optional APK download server |
| `start_phone_demo.ps1` | Optional APK + Docker checklist |

## Seeded SMEs

After first API boot, the database contains SMEs **1–3** (Kopi Maju, Harapan Agro, Urban Digital), BNPL offers, micro-credit lines, and government schemes. Upload CSV for an SME ID, then open the **Health** tab.

## Project layout

```
bnpl_advisor_mobile/
├── backend/              # FastAPI, SQLAlchemy, ML pipeline, Dockerfile
│   ├── app/ml_models/    # Bundled .pkl models (copied into Docker image)
│   └── docker-entrypoint.sh
├── mobile_app/           # Flutter client (not containerised)
├── scripts/              # wait_for_db.py, init_db.py
├── docker-compose.yml    # backend + db (+ optional pgAdmin)
├── .env.example
├── Makefile
├── start.ps1
└── README.md
```

## Competition demo flow (web)

1. **Share the web link:** **https://sme-advisor-web-rk8t.onrender.com/** (or ngrok `8080` / LAN `http://<IP>:8080` for local demos) — see [Demo with web (recommended)](#demo-with-web-recommended).
2. First launch: **5-question profile quiz** (or drawer → **Upload** → **Try sample data**).
3. **Health** — **SME Readiness Score** (0–100 + letter grade), compliance countdown, **Generate bank / grant PDF**.
4. Drawer → **Grant eligibility** (Budget 2026 rules) · **What-if planner** (sliders).
5. **Simulate** → recommendation → **Compare financing** if needed.
6. **AI Advisor** — pick persona (Puan Sarah / Uncle Ah Kow / Dr Aisha) · RAG chat / agents.
7. **Grants** · **Performance** · backup API: https://sme-advisor-api.onrender.com/docs


