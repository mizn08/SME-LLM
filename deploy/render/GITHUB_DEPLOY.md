# Deploy from GitHub → Render (step-by-step)

After you push to **https://github.com/mizn08/SME-LLM**, connect Render once; every push to `main` redeploys automatically.

## Part 1 — Push to GitHub

Your remote: `origin` → `https://github.com/mizn08/SME-LLM.git`

```powershell
cd c:\Users\mizn\Desktop\AIC\SME-LLM
git add -A
git status
git commit -m "Deploy: SME Advisor features + Render"
git push origin main
```

GitHub Actions (`.github/workflows/ci.yml`) will:

- Build `backend/Dockerfile.render` with Docker
- Smoke-test `/health` in a container
- Run Python import + Flutter analyze

Check: **GitHub repo → Actions** tab.

## Part 2 — Connect Render to GitHub

1. Go to [dashboard.render.com](https://dashboard.render.com) → sign in with **GitHub**.
2. **New +** → **PostgreSQL**
   - Name: `sme-advisor-db`
   - Region: Singapore (or closest to Malaysia)
   - Free plan → **Create**
3. **New +** → **Web Service** → **Build and deploy from a Git repository**
   - Connect **mizn08/SME-LLM**
   - **Root Directory:** leave blank (repo root contains `backend/` and `mobile_app/`)

| Setting | Value |
|---------|--------|
| **Branch** | `main` |
| **Runtime** | Docker |
| **Dockerfile Path** | `backend/Dockerfile.render` |
| **Docker build context** | `.` |
| **Instance** | Free (or Starter to avoid sleep) |

**Environment variables** (Web Service → Environment):

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Link from Postgres service **or** paste Internal URL and change `postgres://` → `postgresql+psycopg2://` |
| `ML_MODELS_DIR` | `/app/backend/app/ml_models` |
| `USE_VECTOR_RAG` | `false` |
| `APP_ENV` | `production` |

Entrypoint auto-fixes `postgres://` if you paste Render’s URL as-is.

4. **Create Web Service** — wait for build (8–15 min first time).
5. Open: `https://sme-advisor-api.onrender.com/health` and `/docs`.

**Auto-deploy:** Settings → **Auto-Deploy** = Yes → every `git push` to `main` triggers a new deploy.

## Part 3 — Blueprint (alternative)

**New +** → **Blueprint** → select repo → path: `render.yaml` (repo root) or `deploy/render/render.yaml`

Creates API + Postgres in one step. Then set `OPENAI_API_KEY` manually if needed.

## Part 4 — Flutter web (recommended for judges)

### Option A — Blueprint / `render.yaml` (easiest)

If you already use the Blueprint, **sync** it after pulling latest `main` — it adds **`sme-advisor-web`** (Static Site) that builds Flutter on Render.

Or create manually:

**New +** → **Static Site** → repo **mizn08/SME-LLM** → branch `main`

| Setting | Value |
|---------|--------|
| **Root Directory** | *(blank)* |
| **Build Command** | `chmod +x ./scripts/render_build_web.sh && ./scripts/render_build_web.sh` |
| **Publish Directory** | `mobile_app/build/web` |
| **Environment** | `API_BASE` = `https://sme-advisor-api.onrender.com` |

First build takes ~10–15 min (installs Flutter). Live URL: `https://sme-advisor-web.onrender.com`.

### Option B — Build on your PC

```powershell
.\scripts\build_web.ps1 -ApiBase https://sme-advisor-api.onrender.com
```

Then create Static Site with **Publish Directory** `mobile_app/build/web` and **empty build command** only if you commit `build/web` (not recommended).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on Render | Logs → check Docker; confirm `Dockerfile.render` path |
| CI fails on push | GitHub → Actions → open failed job |
| DB connection error | `DATABASE_URL` must use `postgresql+psycopg2://` |
| 502 cold start | Wait 60s; free tier sleeps when idle |

## Links for APC submission

- **API:** `https://<your-service>.onrender.com/docs`
- **GitHub:** `https://github.com/mizn08/SME-LLM`
- **Web:** Static site URL after step 4
