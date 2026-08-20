# IndiaJob — Government Job Portal

India's government job aggregator with a modern UI — vacancies, eligibility, exam dates and official apply links in one place.

## Features

- **Government Job Aggregation** — Fetches from UPSC, SSC, Employment News, and more
- **AI/ML Date Extraction** — Automatically extracts and verifies last dates, exam dates from notifications
- **Smart Category Classification** — Auto-classifies jobs into Notifications, Admit Cards, Results, Answer Keys, Syllabus, Education
- **State-wise Organization** — Browse jobs by all 30+ Indian states and union territories
- **Closing Soon Alerts** — Highlights jobs with deadlines within 7 days
- **Important News Section** — Curated news from PIB, Employment News RSS feeds
- **Beautiful Modern UI** — Clean, responsive design with Tailwind CSS
- **Auto-refresh** — Backend scheduler fetches new jobs every hour

## Architecture

```
jobalert/
├── frontend/          # Next.js 16 + Tailwind CSS
├── backend/           # FastAPI + SQLAlchemy + APScheduler
│   ├── app/
│   │   ├── scrapers/  # Government site fetchers
│   │   ├── services/  # AI date extraction & ingestion
│   │   ├── models/    # Database models
│   │   └── routers/   # API endpoints
└── docker-compose.yml
```

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+

### 1. Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

### Using Docker

```bash
docker-compose up --build
```

## Operations CLI (`jbcli`)

From the project root:

```bash
chmod +x jbcli
./jbcli help
```

| Command | Description |
|---------|-------------|
| `./jbcli info` | Full system + database overview |
| `./jbcli config` | Backend configuration (SMTP, Twilio, CORS, etc.) |
| `./jbcli db` | Database statistics |
| `./jbcli users` | List registered users (`--limit 20`) |
| `./jbcli fetch` | Fetch latest jobs from all portals |
| `./jbcli cleanup` | Post-fetch cleanup |
| `./jbcli enrich` | Deep-enrich job PDF sections |
| `./jbcli verify all` | Health checks (API, DB, CORS, SMTP, Twilio) |
| `./jbcli pull` | `git pull origin main` |
| `./jbcli update` | pull + fix .env + `docker compose up -d --build` + verify |
| `./jbcli fix-env` | Fix backend/.env typos / create from template |
| `./jbcli docker build` | Build Docker images |
| `./jbcli docker up` | Build and start containers |
| `./jbcli docker ps` | Container status |
| `./jbcli docker logs backend` | Tail logs |

On the GCP VM (Docker running), `jbcli` runs commands inside the backend container automatically.

**Production deploy:** `git pull origin main && ./jbcli update`

## New Features (v2)

### More Scrapers
- **RRB** — Railway Recruitment Board
- **IBPS** — Banking recruitment
- **10 State PSCs** — UPPSC, MPPSC, RPSC, BPSC, TNPSC, KPSC, MPSC, WBPSC, GPSC, HPSC

### AI Enrichment (LLM)
Set `OPENAI_API_KEY` in `backend/.env` to enable GPT-powered:
- Date parsing (last date, exam date)
- Job summarization
- Qualification extraction
- Auto-categorization

Falls back to regex when no API key is set.

### User Accounts
- Register / login at `/register` and `/login`
- Save favorite jobs (heart icon on listings)
- Set alert preferences at `/account`

### Email & WhatsApp Alerts
Configure in `backend/.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_USER=your@gmail.com
SMTP_PASSWORD=app-password

TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
```

Users choose states, categories, qualifications and receive alerts when new matching jobs are found.

## API Endpoints (new)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Sign in |
| GET | `/api/auth/me` | Current user |
| GET/PUT | `/api/users/preferences` | Alert settings |
| GET/POST/DELETE | `/api/users/favorites/{id}` | Saved jobs |


### Query Parameters for `/api/jobs`

- `category` — notification, admit_card, result, answer_key, syllabus, education
- `state` — Filter by state name
- `scope` — all_india, central, state
- `search` — Full-text search
- `closing_soon` — true to show jobs closing within 7 days
- `limit` — Max results (default 50)

## Data Sources

- employmentnews.gov.in (Official Government Portal)
- upsc.gov.in
- ssc.nic.in
- freejobalert.com (Aggregator reference)
- PIB RSS feeds for news

## Tech Stack

**Frontend:** Next.js 16, TypeScript, Tailwind CSS, Lucide Icons
**Backend:** FastAPI, SQLAlchemy, BeautifulSoup, APScheduler
**AI/ML:** Regex + dateutil for date extraction, keyword scoring for classification

## License

MIT
