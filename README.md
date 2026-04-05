# AutoBrief — Automated Daily Briefing Bot

A full-stack application that sends you a daily briefing with weather, news headlines, and your class schedule. **100% free** — no paid APIs required.

## Architecture

```
AutoBrief/
├── .env                        # Telegram token & schedule config
├── .env.example                # Template for .env
├── autobrief_doc.tex           # Full LaTeX documentation
├── backend/
│   ├── main.py                 # FastAPI app, routes, lifespan
│   ├── models.py               # SQLAlchemy ORM models
│   ├── database.py             # Engine, session, init
│   ├── briefing.py             # BriefingEngine (weather, news, Telegram)
│   ├── scheduler.py            # APScheduler cron job (daily 7 AM)
│   ├── config.py               # Env-var loader
│   ├── tests.py                # 23 automated tests
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js           # Vite + proxy to backend
    ├── tailwind.config.js
    ├── postcss.config.js
    └── src/
        ├── main.jsx
        ├── index.css
        └── App.jsx              # Dashboard (Preferences, Schedule, Trigger)
```

## External APIs (All Free, No Payment Required)

| Service            | Purpose           | API Key Required? |
|--------------------|-------------------|-------------------|
| **Open-Meteo**     | Weather data      | No — completely free |
| **Google News RSS**| News headlines    | No — completely free |
| **Telegram Bot**   | Message delivery  | Free token from BotFather (optional) |

The app works in **preview mode** without any API keys at all. Telegram is only needed to actually send messages.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**

## Setup & Run

### 1. (Optional) Configure Telegram

Only needed if you want to *send* briefings to Telegram. For preview-only, skip this.

Edit `.env` in the project root:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
BRIEFING_HOUR=7
BRIEFING_MINUTE=0
```

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API runs at `http://127.0.0.1:8000`. Docs at `http://127.0.0.1:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI runs at `http://localhost:5173` and proxies `/api/*` to the backend.

### 4. Run Tests

```bash
cd backend
source venv/bin/activate
python -m pytest tests.py -v
```

## API Endpoints

| Method | Path                     | Description                              |
|--------|--------------------------|------------------------------------------|
| GET    | `/api/preferences`       | Get saved preferences                    |
| POST   | `/api/preferences`       | Create/update preferences                |
| GET    | `/api/schedule`          | List all schedule entries                |
| POST   | `/api/schedule`          | Add a schedule entry                     |
| PUT    | `/api/schedule/{id}`     | Update a schedule entry                  |
| DELETE | `/api/schedule/{id}`     | Delete a schedule entry                  |
| POST   | `/api/trigger`           | Run briefing + send via Telegram         |
| POST   | `/api/preview`           | Run briefing in preview mode (no send)   |

## How It Works

1. User configures city, news topics, and (optionally) Telegram chat ID via the web UI.
2. User adds their weekly class schedule.
3. Every day at 7:00 AM (configurable), APScheduler fires the `BriefingEngine`:
   - Fetches weather from **Open-Meteo** (free, no key)
   - Fetches top 3 headlines from **Google News RSS** (free, no key)
   - Reads today's classes from SQLite
   - Builds a Markdown message and sends it via Telegram Bot API
4. The **Preview Briefing** button renders a full, beautifully styled briefing card on the dashboard.
5. The **Send via Telegram** button delivers it to your Telegram chat.
