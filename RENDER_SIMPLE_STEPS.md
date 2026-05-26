# Render deploy — simple steps

If builds keep failing, use **GitHub Pages** (easier) or fix Render with the checklist below.

## Option A — GitHub Pages (recommended if Render fails)

1. Push this repo to GitHub (verify email at https://github.com/settings/emails first).
2. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. **Actions** tab → run **Deploy Web to GitHub Pages** (or push to `main`).
4. When green, open: `https://mizn08.github.io/SME-LLM/` (or your Pages URL from Settings).
5. Set workflow env `API_BASE` in `.github/workflows/deploy-gh-pages.yml` to your real API URL if different.

## Option B — Render static site

### Static site settings (copy exactly)

| Field | Value |
|-------|--------|
| Root Directory | *(blank)* |
| Build Command | `chmod +x ./scripts/render_build_web.sh && ./scripts/render_build_web.sh` |
| Publish Directory | `mobile_app/build/web` |

### Environment variable

| Key | Value |
|-----|--------|
| `API_BASE` | `https://sme-advisor-api-pp6d.onrender.com` |

### API service (`sme-advisor-api-...`)

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Postgres **Internal** URL from Render (full host, not `dpg-xxxxx` placeholder) |
| `CHUTES_API_KEY` | your `cpk_...` key |
| `CHUTES_BASE_URL` | `https://llm.chutes.ai/v1` |

### Wrong URL → 404

Do **not** use `sme-llm.onrender.com` unless you created that service. Use the URL shown on your **static site** dashboard (e.g. `sme-advisor-web-pp6d.onrender.com`).

### After deploy

- Web: your static site URL  
- API health: `https://sme-advisor-api-pp6d.onrender.com/health`

## Can't push from PC?

Edit on GitHub in the browser:

1. https://github.com/mizn08/SME-LLM  
2. Open `scripts/render_build_web.sh` → pencil icon → save (commits on GitHub).  
3. Render → **Manual Deploy** → latest commit.
