# Demo session — manual upload files (AIC)

Use these files tomorrow when presenting live. Keep them on your desktop or USB — no need to dig through the repo.

## Files in this folder

| File | Upload where | What judges see |
|------|----------------|-----------------|
| **DEMO_01_forecast_transactions_kopi_maju.csv** | Drawer → Upload → Choose file | Home chart: 12 months revenue/expense + **Forecast net** dashed line |
| **DEMO_02_invoice_kopi_maju_supplies.png** | AI Insights → Scan invoice | OCR line items: Subtotal, SST, Grand total |
| **DEMO_03_client_transcript_pos.txt** | BNPL Advisor → Sales Engineer → Parse client transcript (or paste text) | Unstructured brief → quote → BNPL sync |

## Step-by-step (5 min demo)

1. **Start stack:** `backend\run_local.ps1` + `scripts\run_local_web.ps1`
2. **Profile:** Drawer → select **Kopi Maju Enterprise**
3. **Transactions:** Upload → **DEMO_01_forecast_transactions_kopi_maju.csv** → Home → show chart + runway KPIs
4. **OCR:** Insights → upload **DEMO_02_invoice_kopi_maju_supplies.png**
5. **Sales Engineer:** Sales Engineer tab → upload **DEMO_03_client_transcript_pos.txt** (or Run demo script mode) → show quote + workflow timeline

## Regenerate

```powershell
cd backend
python ml_pipeline/scripts/generate_aic_datasets.py
python -c "from pathlib import Path; import pandas as pd, shutil; ..."
```

Full catalog: `backend/ml_pipeline/data/datasets/README.md`
