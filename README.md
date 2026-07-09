# AI-First CRM — HCP Module (Log Interaction)

**Round 1 Interview Assignment** · Principal Software Developer  

Dual-mode **Log HCP Interaction** screen for pharma / life-sciences field representatives:

| Mode | Description |
|------|-------------|
| **Structured form** (left) | Classic CRM form — fill fields manually |
| **AI Assistant** (right) | LangGraph agent chat — extracts fields and fills the form |

**Stack:** React + Redux · FastAPI · LangGraph · Groq · SQLite (default) / PostgreSQL  

> **Note on LLM:** The assignment specified `gemma2-9b-it`. That model was **decommissioned** on Groq. This project uses free-tier **`llama-3.1-8b-instant`** with **`llama-3.3-70b-versatile`** as fallback (same Groq stack).

---

## Features

- Dual-pane UI (form + chat), Google **Inter** font  
- **5 LangGraph tools:** `log_interaction`, `edit_interaction`, `search_hcp`, `get_interaction_history`, `schedule_follow_up`  
- Accurate HCP resolution from notes (primary doctor vs attendees)  
- Seeded sample HCP directory for demos  
- SQLite zero-config local run  

---

## Project structure

```
.
├── README.md
├── docker-compose.yml          # optional Postgres + services
├── backend/
│   ├── main.py                 # FastAPI entry
│   ├── requirements.txt
│   ├── .env.example
│   ├── agent/                  # LangGraph graph, tools, nodes, state
│   ├── api/routes/             # REST: hcps, interactions, agent
│   ├── db/                     # SQLAlchemy models, CRUD, seed
│   └── schemas/
└── frontend/
    ├── package.json
    └── src/                    # React + Redux Toolkit UI
```

---

## Prerequisites

- **Python 3.10+** (3.12 recommended)  
- **Node.js 18+**  
- Free [Groq API key](https://console.groq.com) (no paid plan required for the demo)  

---

## Setup & run

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set:
#   GROQ_API_KEY=gsk_your_key_here

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000  
- Swagger: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

On first start, tables are created and **12 sample HCPs** are seeded.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

- UI: http://localhost:5173  

---

## Environment variables

Copy `backend/.env.example` → `backend/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key | *(required for full LLM)* |
| `GROQ_MODEL` | Primary chat model | `llama-3.1-8b-instant` |
| `GROQ_FALLBACK_MODEL` | Fallback model | `llama-3.3-70b-versatile` |
| `DATABASE_URL` | SQLAlchemy URL | `sqlite:///./crm_hcp.db` |
| `CORS_ORIGINS` | Allowed frontends | `http://localhost:5173,...` |

**Never commit `.env`.** Only `.env.example` is in the repo.

---

## LangGraph agent (5 tools)

```
User message
  → agent node (tool-calling LLM)
  → tools node (execute tools, update form_data)
  → respond node (user-facing summary)
  → END
```

| Tool | Purpose |
|------|---------|
| `log_interaction` | Extract entities + summary from free text; persist interaction |
| `edit_interaction` | Update an existing interaction by id |
| `search_hcp` | Lookup HCP by name / specialty / location |
| `get_interaction_history` | Prior interactions for context |
| `schedule_follow_up` | Create follow-up action item (DB record) |

---

## Demo tips

1. Open http://localhost:5173  
2. Paste a natural-language note in the **AI Assistant** (right), e.g. meeting with a seeded doctor such as **Dr. Arun Chopra** or **Dr. Rajesh Kumar**  
3. Form fields on the **left** populate automatically  
4. Or fill the form manually and click **Save Interaction**  

Sample HCPs include: Dr. Arun Chopra, Dr. Rajesh Kumar, Dr. Anita Patel, Dr. Suresh Menon, and others (see `backend/seed.py`).

---

## Optional: Docker Compose

```bash
export GROQ_API_KEY=gsk_your_key
docker compose up --build
```

Runs Postgres, backend, and frontend. For the interview demo, **local SQLite + two terminals is enough**.

---

## API overview

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health + Groq status |
| GET | `/hcps?q=` | Search / list HCPs |
| POST | `/interactions` | Create interaction (form) |
| PATCH | `/interactions/{id}` | Update interaction |
| POST | `/agent/chat` | LangGraph conversational agent |
| GET | `/agent/tools` | List the 5 agent tools |
| POST | `/agent/chat/reset` | Clear chat session |

---

## License

Interview / assignment use only.
