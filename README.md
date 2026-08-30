# FashionTrendyfor.fi

An AI-powered fashion trend intelligence platform that scrapes runway imagery, analyzes garments using AWS Bedrock (Claude), and surfaces insights through an interactive web dashboard.

---

## How It Works

### High-Level Flow

```
URLs (urls.txt)
    ↓
webscrapper.py      → downloads runway images into images/<designer-season>/
    ↓
runway_segmentation.py  → removes backgrounds, saves to segmented/
    ↓
s3bucketinjector.py → uploads segmented images to S3 (runwayimages, eu-west-2)
    ↓
final.py / fashion_agent/ → calls Claude via AWS Bedrock to extract garment metadata
    ↓
DynamoDB (FashionAnalysis table)
    ↓
API Gateway → Lambda functions → React frontend (project/)
```

### Pipeline (`pipeline.py`)

Orchestrates the scrape → segment steps end-to-end. Skips S3 folders that already exist to avoid reprocessing.

```bash
python pipeline.py                  # full run: scrape + segment
python pipeline.py --skip-scrape    # segment already-downloaded images only
python pipeline.py --skip-segment   # scrape only
python pipeline.py --alpha-matting  # higher quality segmentation (slower)
python pipeline.py --dry-run        # preview what would be processed
```

---

## Project Layout

```
.
├── pipeline.py              # Orchestrates scrape → segment pipeline
├── webscrapper.py           # Scrapes runway images from URLs in urls.txt
├── runway_segmentation.py   # Background removal (rembg)
├── s3bucketinjector.py      # Bulk uploads images to the runwayimages S3 bucket
├── final.py / final.ipynb   # Bedrock → DynamoDB ingestion script
├── urls.txt                 # List of runway collection URLs to scrape
├── requirements.txt         # Python dependencies
│
├── fashion_agent/           # Agentic AI pipeline (alternate/advanced ingestion)
│   ├── agent.py             # Main agent orchestrator
│   ├── analyst.py           # Bedrock-powered garment analysis
│   ├── chat.py              # Conversational interface for the agent
│   ├── scraper.py           # Image scraping utilities
│   ├── dynamo_client.py     # DynamoDB read/write helpers
│   ├── cache_schema.py      # Schema and caching logic
│   ├── pipeline.py          # Agent-side ingestion pipeline
│   ├── s3bucketinjector.py  # S3 upload helper
│   └── runway_segmentation.py
│
├── lamdbas/                 # AWS Lambda function source code
│   ├── chatbot/             # AI chatbot (Claude via Bedrock)
│   ├── fetchArticles/       # Fetches fashion news articles
│   ├── fetchFashionAnalysis/ # Returns aggregated DynamoDB data to the frontend
│   ├── getlooks/            # Retrieves saved looks per user
│   ├── google_trends/       # Proxies Google Trends data for designer comparisons
│   ├── lists3Folder/        # Lists available collections in S3
│   ├── moonboard_patch_looks/ # Updates looks on a user's moonboard
│   └── save_looks/          # Saves looks to a user's profile in DynamoDB
│
├── project/                 # React frontend (separate git repo: cozy-repo-hub)
│   ├── src/pages/
│   │   ├── Landing.tsx      # Homepage
│   │   ├── Data.tsx         # Fashion data explorer
│   │   ├── Moonboard.tsx    # User's saved looks board
│   │   └── OAuthCallback.tsx
│   └── src/components/
│       ├── FashionDashboard.tsx
│       ├── TrendsDashboard.tsx
│       ├── ArticlesDashboard.tsx
│       ├── DesignerGoogleTrends.tsx
│       ├── ChatDrawer.tsx   # Floating AI chatbot UI
│       └── AuthModal.tsx    # Cognito login/signup
│
└── *.ipynb                  # Exploratory notebooks
```

---

## AWS Infrastructure

| Service | Usage |
|---|---|
| S3 (`runwayimages`, `eu-west-2`) | Stores runway imagery |
| DynamoDB (`FashionAnalysis`) | Stores AI-extracted garment metadata |
| Bedrock (Claude 3 Haiku) | Garment, material, and colour extraction from images |
| Lambda | Backend functions (see `lamdbas/`) |
| API Gateway | Exposes Lambda functions to the frontend |
| Cognito | User authentication (login, Google OAuth, forgot password) |

---

## Local Setup

### Python Ingestion Pipeline

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure AWS credentials first, then:
python pipeline.py        # scrape + segment
python final.py           # analyze with Bedrock → write to DynamoDB
```

### React Frontend

The `project/` folder is a separate git repository (`cozy-repo-hub`).

```bash
cd project
npm install
npm run dev        # http://localhost:5173
npm run build      # production build
npm run lint       # ESLint check
```

The frontend calls API Gateway endpoints directly. No local backend server is needed for development.

---

## AWS Credentials

All Python tools and Lambda functions expect standard AWS authentication. The IAM role/user needs:
- `s3:GetObject`, `s3:PutObject` on the `runwayimages` bucket
- `dynamodb:PutItem`, `dynamodb:Query`, `dynamodb:Scan` on `FashionAnalysis`
- `bedrock:InvokeModel` for Claude 3 Haiku in `eu-west-2`

Configure via environment variables, `~/.aws/credentials`, or AWS SSO.
