# Deploy SME-LLM on Render

Your repo: **https://github.com/mizn08/SME-LLM**

Render gives you stable HTTPS URLs for the API and Flutter web app.

## Quick deploy (Blueprint — recommended)

1. **Push latest code to GitHub**

   ```powershell
   cd c:\Users\mizn\Desktop\AIC\SME-LLM
   git add -A
   git commit -m "Deploy: 18 features + Render ready"
   git push origin main
   ```

2. Open [dashboard.render.com](https://dashboard.render.com) → sign in with **GitHub**.

3. **New +** → **Blueprint** → connect **`mizn08/SME-LLM`**.

4. Blueprint file: **`render.yaml`** (repo root — leave **Root Directory** blank).

5. When prompted, set optional secret:
   - `OPENAI_API_KEY` — only if you want LLM-generated chat (otherwise template RAG answers work).

6. Click **Apply**. Render creates:
   - `sme-advisor-db` (PostgreSQL)
   - `sme-advisor-api` (Docker API)
   - `sme-advisor-web` (Flutter static site)

7. Wait **15–25 minutes** for the first deploy (API Docker ~10 min, web Flutter build ~15 min).

8. Verify:
   - API health: `https://sme-advisor-api.onrender.com/health`
   - Swagger: `https://sme-advisor-api.onrender.com/docs`
   - Web app: `https://sme-advisor-web.onrender.com`

> **Free tier:** Services sleep after ~15 min idle. First request after sleep can take **30–60 seconds**.

---

## Manual deploy (if Blueprint fails)

### Step 1 — PostgreSQL

**New +** → **PostgreSQL** → name `sme-advisor-db`, region **Singapore**, free plan.

### Step 2 — API (Web Service)

**New +** → **Web Service** → repo `mizn08/SME-LLM`, branch `main`.

| Setting | Value |
|---------|--------|
| Root Directory | *(blank)* |
| Runtime | **Docker** |
| Dockerfile Path | `backend/Dockerfile.render` |
| Docker Context | `.` |
| Health Check Path | `/health` |

**Environment variables:**

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Link from `sme-advisor-db` (Internal URL) — entrypoint auto-fixes `postgres://` |
| `ML_MODELS_DIR` | `/app/backend/app/ml_models` |
| `USE_VECTOR_RAG` | `false` |
| `APP_ENV` | `production` |
| `AUTH_REQUIRED` | `false` |

### Step 3 — Flutter web (Static Site)

**New +** → **Static Site** → same repo.

| Setting | Value |
|---------|--------|
| Build Command | `chmod +x ./scripts/render_build_web.sh && ./scripts/render_build_web.sh` |
| Publish Directory | `mobile_app/build/web` |
| `API_BASE` | `https://sme-advisor-api.onrender.com` |

Or build locally and skip Render Flutter install:

```powershell
cd c:\Users\mizn\Desktop\AIC\SME-LLM
.\scripts\build_web.ps1 -ApiBase https://sme-advisor-api.onrender.com
```

Then Static Site with **empty** build command and publish `mobile_app/build/web` (only if you commit `build/web`).

---

## After deploy — test new features

Open Swagger on the API and try:

- `GET /sme/1/nudges`
- `GET /sme/1/lead-scores`
- `GET /sme/1/benchmark`
- `GET /sme/1/digest`
- `GET /lenders`
- `POST /guided-advisory`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Blueprint sync failed | **Manual Deploy** on each service, or delete failed service and recreate |
| Build timeout | Confirm `Dockerfile.render` (not full `Dockerfile`) |
| `postgres://` driver error | Fixed in `docker-entrypoint.sh`; or set `postgresql+psycopg2://...` |
| 502 / slow first load | Cold start on free tier — open `/health` first, wait 60s |
| Web app can't reach API | Rebuild web with `API_BASE=https://sme-advisor-api.onrender.com` |
| Application tracker 500 | Redeploy API after latest push (creates `application_tracker` table on boot) |

More detail: [`deploy/render/README.md`](deploy/render/README.md)

---

## Links for submission

- **Web:** `https://sme-advisor-web.onrender.com` (or your Render-assigned name)
- **API docs:** `https://sme-advisor-api.onrender.com/docs`
- **GitHub:** `https://github.com/mizn08/SME-LLM`
