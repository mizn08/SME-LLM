# Deploy SME Advisor on Render (instead of ngrok)

Render gives you a **stable HTTPS URL** for judges — no tunnels, no APK IP changes.

## Architecture on Render

| Service | Render type | URL example |
|---------|-------------|-------------|
| **API** | Web Service (Docker) | `https://sme-advisor-api.onrender.com` |
| **Database** | PostgreSQL | Internal `DATABASE_URL` (auto-linked) |
| **Flutter web** (optional) | Static Site | `https://sme-advisor-web.onrender.com` |

Judges open the **static site** URL (full app) or **`/docs`** on the API (backup).

---

## 1. Push code to GitHub

Render deploys from Git. Repo: **https://github.com/mizn08/SME-LLM**

Step-by-step (push + connect Render): **[GITHUB_DEPLOY.md](./GITHUB_DEPLOY.md)**

CI runs on every push (Docker build + health smoke test): `.github/workflows/ci.yml`

---

## 2. Create PostgreSQL on Render

1. [dashboard.render.com](https://dashboard.render.com) → **New +** → **PostgreSQL**
2. Name: `sme-advisor-db` (free tier OK for demo)
3. Copy the **Internal Database URL** (starts with `postgres://`)

Convert for SQLAlchemy (Render dashboard → add env var manually):

```text
postgres://USER:PASS@HOST/DB
```

becomes:

```text
postgresql+psycopg2://USER:PASS@HOST/DB
```

(Replace `postgres://` with `postgresql+psycopg2://` — same host, user, password, database.)

---

## 3. Create Web Service (API)

**New +** → **Web Service** → connect GitHub repo.

| Setting | Value |
|---------|--------|
| **Root Directory** | *(blank — repo root has `backend/` and `mobile_app/`)* |
| **Runtime** | **Docker** |
| **Dockerfile Path** | `backend/Dockerfile.render` (slim — faster on free tier) |
| **Docker Context** | `.` (repository root that contains `backend/` and `scripts/`) |
| **Instance type** | Free (demo) or Starter (faster, no cold sleep) |

**Environment variables**

| Key | Value |
|-----|--------|
| `DATABASE_URL` | `postgresql+psycopg2://...` (converted URL from step 2) |
| `ML_MODELS_DIR` | `/app/backend/app/ml_models` |
| `APP_ENV` | `production` |
| `USE_VECTOR_RAG` | `false` (recommended on free tier — faster build & boot; BM25/RAG still works) |
| `AUTH_REQUIRED` | `false` (demo) |
| `OPENAI_API_KEY` | optional |

**Health check path:** `/health`

First deploy takes about **8–15 minutes** with `Dockerfile.render` (skips Chroma, FastEmbed, Tesseract, SHAP). Check **Logs** if build fails.

**What `Dockerfile.render` omits (uses fallbacks instead)**

| Omitted | Still works via |
|---------|------------------|
| Chroma / FastEmbed | BM25 RAG (`USE_VECTOR_RAG=false`) |
| Tesseract OCR | `/upload-invoice` returns helpful error |
| SHAP C++ build | Heuristic SHAP-style factors on `/predict` |

Full local Docker image: `backend/Dockerfile` (all features).

Live API:

- Health: `https://YOUR-SERVICE.onrender.com/health`
- Swagger: `https://YOUR-SERVICE.onrender.com/docs`

**Free tier note:** Service sleeps after ~15 min idle; first request after sleep takes **30–60 s** (cold start). Mention this in your demo or use a paid instance.

---

## 4. Flutter web on Render (optional Static Site)

Build on your PC with the **Render API URL**:

```powershell
cd SME-LLM
.\scripts\build_web.ps1 -ApiBase https://YOUR-SERVICE.onrender.com
```

On Render: **New +** → **Static Site**

| Setting | Value |
|---------|--------|
| **Publish directory** | `mobile_app/build/web` |

**Option A — Manual:** Upload `build/web` via a small Git commit (not ideal for large builds).

**Option B — Git:** Commit `build/web` only for demo branch, or use GitHub Actions to build and push (recommended for production).

**Option C — Judges use Swagger only:** Skip static site; share `https://YOUR-SERVICE.onrender.com/docs` (always works).

Other hosts for the same `build/web` folder: **Vercel**, **Netlify**, **Cloudflare Pages** — all work with `API_BASE` pointing at Render.

---

## 5. Blueprint (optional)

From repo root, in Render: **New +** → **Blueprint** → point at `deploy/render/render.yaml` and fill secrets.

---

## Render vs ngrok

| | **Render** | **ngrok** |
|---|------------|-----------|
| URL | Permanent `*.onrender.com` | Changes each session (free) |
| HTTPS | Yes | Yes |
| Always on | Free tier sleeps | PC must stay on |
| Database | Managed Postgres | Local Docker |
| Cost | Free tier available | Free tier available |
| Best for | APC submission link | Quick local test |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Blueprint: **web service deploy failed** | Open **sme-advisor-api** → **Logs**. Usually DB SSL or build timeout. Latest `render.yaml` uses `internalConnectionString` + `sslmode=require` auto-fix. **Manual Deploy** after pulling latest `main`. |
| Build timeout | Use `backend/Dockerfile.render` (default in `render.yaml`), not full `Dockerfile` |
| `postgres://` driver error | Auto-fixed in entrypoint; or set `postgresql+psycopg2://...?sslmode=require` |
| 502 on first hit | Wait for cold start; open `/health` first |
| Web app blank / API errors | Rebuild web with correct `-ApiBase https://....onrender.com` |
| Uploads / Chroma lost | Free web disk is ephemeral — OK for demo; use Postgres for data |

### If Blueprint sync failed once

1. Render → **SME-Advisor** blueprint → **Manual sync** (or push latest `main` to GitHub).
2. Or delete failed **sme-advisor-api** web service → **New Web Service** from repo (Docker, `backend/Dockerfile.render`) and link existing **sme-advisor-db** `DATABASE_URL` (Internal URL).

---

## What to put in APC submission

- **Live app:** `https://sme-advisor-web.onrender.com` (static)  
- **API:** `https://sme-advisor-api.onrender.com/docs`  
- **GitHub:** your repo link  

No ngrok required.
