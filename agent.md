# Fashion Trend Intelligence Agent

## Overview
This repository combines a Python-based ingestion and enrichment pipeline with a React (Vite + Tailwind) dashboard to surface AI-derived insights about runway fashion collections. The agent workflow:
- Scrapes runway look imagery from the web.
- Uploads images to an S3 bucket that backs the fashion analysis pipeline.
- Calls AWS Bedrock (Claude 3 Haiku) to extract garment metadata, colors, and materials from each look.
- Stores the structured results in a DynamoDB table.
- Serves an interactive UI that fetches the DynamoDB aggregate via an API Gateway endpoint for exploration, statistics, and forecasting visualisations.

## Project Layout
```
.
├── final.py                 # End-to-end Bedrock -> DynamoDB ingestion pipeline
├── webscrapper.py           # Image scraper for runway collections
├── s3bucketinjector.py      # Bulk upload tool to push local images to S3
├── requirements.txt         # Python dependencies for the ingestion tooling
├── project/                 # React + Vite + Tailwind dashboard
│   ├── src/pages            # Overview, Data, Statistics, Forecasting screens
│   ├── src/components       # Reusable UI elements (navigation, charts, tables)
│   └── testDynamo.*         # Node scripts for quick DynamoDB connectivity checks
├── node_modules/, package*.json
└── notebooks (*.ipynb)      # Exploratory modelling and analysis experiments
```

## Data & Model Flow
1. `webscrapper.py` harvests runway look images into `images/<designer-season>/`.
2. `s3bucketinjector.py` uploads those images to the `runwayimages` S3 bucket (region `eu-west-2`).
3. `final.py` runs the Bedrock-powered enrichment loop:
   - Generates metadata (designer, collection, season, event) from the filename.
   - Sends each image to Claude 3 Haiku for garment, material, and colour extraction.
   - Writes per-item rows to the `FashionAnalysis` DynamoDB table, including a normalized ISO runway timestamp.
4. The frontend hits `https://tr6nsuekii.execute-api.eu-west-2.amazonaws.com/default/fetchFashionAnalysis` to retrieve aggregated results for visualisation.

> **AWS Credentials**  
> The Python tools expect standard AWS authentication (environment variables, shared credentials file, or AWS SSO). Ensure the IAM role or user has S3, DynamoDB, and Bedrock permissions in `eu-west-2`.

## Local Development

### Python Tooling
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
- Configure AWS credentials locally before running `final.py` or the S3/Dynamo helpers.
- Optional: install `beautifulsoup4` if you plan to modify or extend `webscrapper.py`.

### Frontend Dashboard
```bash
cd project
npm install
npm run dev
```
- The dev server defaults to `http://localhost:5173/`.
- TailwindCSS is already wired via `postcss.config.js` and `tailwind.config.js`.
- The UI consumes the live API Gateway endpoint; swap it for a local mock if needed.

## Testing & Verification
- Python: run targeted scripts manually (`python final.py`) after setting `RUNWAY_DATE` and S3 path constants.
- Frontend: `npm run build` validates the Vite production build; `npm run lint` runs ESLint with the provided configs.
- DynamoDB connectivity: `node project/testDynamo.js` (requires AWS SDK credentials).

## Extending the Agent
- **Alternate Designers/Shows:** Update the `bucket_name` and `RUNWAY_DATE` constants in `final.py`, then rerun the pipeline.
- **Custom Forecasting:** Replace the placeholder trend data in `project/src/pages/Forecasting.tsx` with model-driven predictions or backend calls.
- **New Visualisations:** Reuse `project/src/components/PieChart.tsx` and the Tailwind utility classes to add charts on additional pages.

## Operational Checklist
- [ ] Verify AWS credentials and regional settings.
- [ ] Ensure the target S3 bucket contains the latest runway imagery.
- [ ] Run `final.py` to refresh DynamoDB after new uploads.
- [ ] Redeploy or restart the frontend if API schemas change.
- [ ] Monitor API Gateway/CloudWatch logs for ingestion or fetch failures.
