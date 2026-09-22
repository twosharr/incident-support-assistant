# 🚨 AI Incident Support Assistant & Lifecycle Manager

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.109-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_18_TypeScript-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org)
[![Vite](https://img.shields.io/badge/Build-Vite_5-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)
[![TailwindCSS](https://img.shields.io/badge/UI-TailwindCSS_3.4-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Jira Cloud](https://img.shields.io/badge/Integration-Jira_Cloud_REST_v3-0052CC?style=flat&logo=jira&logoColor=white)](https://www.atlassian.com/software/jira)
[![Web Speech API](https://img.shields.io/badge/Voice-Web_Speech_API-FF6B6B?style=flat)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)

An intelligent, full-stack incident management platform designed for enterprise DevOps, SRE, and support teams. Combines **real-time Jira Cloud synchronization**, an **interactive Incident Kanban Lifecycle board**, **multimodal voice-to-text & speech synthesis**, **smart weighted diagnostic algorithms**, and **Microsoft Teams Bot Framework readiness**.

---

## 🌟 Key Features

```
                                  ┌────────────────────────────────┐
                                  │   AI Incident Support System   │
                                  └───────────────┬────────────────┘
                                                  │
         ┌────────────────────────┬───────────────┴───────────────┬────────────────────────┐
         ▼                        ▼                               ▼                        ▼
┌──────────────────┐    ┌──────────────────┐            ┌──────────────────┐    ┌──────────────────┐
│  📋 Kanban Board  │    │  🎙️ Voice Engine │            │  🔗 Jira Cloud   │    │  🧠 Diagnostics  │
│  • 4-Stage Flow  │    │  • Speech-to-Text│            │  • Live REST v3  │    │  • Weighted Rank │
│  • Live MTTR     │    │  • 2s Silence Cut│            │  • Changelog Log │    │  • Composite Tool│
│  • Ticket Modal  │    │  • TTS Readout   │            │  • ADF Text Parse│    │  • 4-Part Cards  │
└──────────────────┘    └──────────────────┘            └──────────────────┘    └──────────────────┘
```

### 1. 📋 Incident Kanban Board & Lifecycle
* **4-Column Lifecycle:** Organize and triage incidents across `Open / Active`, `In Progress`, `Monitoring`, and `Resolved / Closed`.
* **Live MTTR Analytics:** Automatically calculates Mean Time to Resolution for closed tickets and tracks live outage duration timers for ongoing incidents.
* **Deep Inspection Modal:** Click any ticket card to inspect root causes, active workarounds, affected microservices, and audit event logs.
* **"Ask AI" Context Bridge:** One-click shortcut on every card to immediately pipe ticket metadata into the AI diagnostic assistant.

### 2. 🔗 Real-Time Jira Cloud Integration
* **Synchronous REST API v3 Client:** Thread-safe `httpx` client eliminates asyncio event loop contention inside FastAPI routes.
* **Live JQL Querying:** Pulls tickets directly from Atlassian Jira Cloud projects (e.g. `SCRUM`) in real time.
* **Changelog Reconstruction:** Automatically turns Jira transition history into a chronological audit timeline (status changes, assignee handoffs, resolution stamps).
* **ADF Text Extraction:** Recursively parses Atlassian Document Format blocks into clean, human-readable text.

### 3. 🎙️ Multimodal Voice Engine (Copilot Style)
* **Hands-Free Speech-to-Text:** Built on the browser-native Web Speech API (`SpeechRecognition`).
* **2-Second Silence Auto-Submit:** Debounce timer automatically commits the voice transcript and dispatches the query once speaking stops for 2 seconds — zero keystrokes required.
* **Natural Speech Synthesis:** Converts AI responses to speech with regular expression sanitization (strips markdown fences, tables, and emoji codes before speaking).
* **Per-Message Audio Controls:** Dedicated "🔊 Listen" action on every message bubble and a global voice toggle in the navigation bar.

### 4. 🧠 Smart Investigation & Diagnostic Engine
* **Multi-Tier Weighted Search Scoring:**
  * `+50 pts` Exact Category Match
  * `+20 pts` Category Token Overlap
  * `+15 pts` Service Name & Tag Match
  * `+10 pts` Linked Incident Associations
  * `+5 pts`  Title Keyword Match
  * `+1 pt`   Content Full-Text Match
* **Composite Troubleshooting (`get_comprehensive_troubleshooting`):** Aggregates playbooks, active workarounds, historical post-mortems, and telemetry into a single structured diagnostic response:
  - 🔧 **Recommended Steps**
  - ⚡ **Known Workarounds**
  - 📖 **Similar Past Resolutions**
  - 📚 **Knowledge Base Citations**

### 5. ⚡ Real-Time Streaming UI
* **ChatGPT-Style Typewriter Effect:** Progressively streams response text character-by-character (8ms/tick) with a blinking cursor `▍` to minimize perceived latency.
* **Audio Synchronization:** Speech synthesis synchronously waits for the typewriter animation to conclude before reading aloud, preventing audio-visual race conditions.

---

## 🏗️ Architecture & Tech Stack

| Layer | Technologies | Details |
|---|---|---|
| **Backend** | Python 3.10+, FastAPI, Pydantic v2, HTTPX, Uvicorn | High-performance async REST API + Bot Framework endpoint |
| **Frontend** | React 18, TypeScript, Vite 5, TailwindCSS, Axios | Teams-themed dark UI with smooth transitions and audio hooks |
| **Integrations** | Atlassian Jira Cloud REST API v3, Web Speech API | Synchronous live Jira client + native browser speech synthesis/recognition |
| **Testing** | Pytest, React Testing Library | 40+ unit tests covering tools, classifiers, MTTR math, and Jira parsers |

---

## 📁 Repository Structure

```
incident-support-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI server & route orchestration
│   │   ├── config.py                # Environment configuration (Pydantic Settings)
│   │   ├── ai/
│   │   │   └── assistant.py         # Intent classifier, formatter, AI orchestrator
│   │   ├── tools/
│   │   │   └── tool_registry.py     # Diagnostic tool suite & MTTR calculator
│   │   ├── integrations/
│   │   │   ├── jira_client.py       # Live Jira Cloud REST API v3 client
│   │   │   └── data_store.py        # Central data store & weighted ranking engine
│   │   ├── models/
│   │   │   └── __init__.py          # Pydantic schemas (Incident, ServiceHealth, KB)
│   │   ├── bot/
│   │   │   └── bot_handler.py       # Microsoft Teams Bot Framework adapter
│   │   └── api/
│   │       ├── chat.py              # POST /api/chat
│   │       ├── incidents.py         # GET /api/incidents, /api/incidents/jira
│   │       └── health.py            # GET /api/health
│   ├── data/
│   │   ├── incidents.json           # Historical incidents & post-mortem catalog
│   │   ├── knowledge_base.json      # Standard operating procedures & KB docs
│   │   ├── services.json            # Microservice health telemetry & error rates
│   │   └── playbooks.json           # Step-by-step troubleshooting playbooks
│   ├── tests/
│   │   └── test_assistant.py        # Unit test suite (40+ test cases)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # Main layout & segmented view toggle
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx       # Copilot-style chat interface with voice controls
│   │   │   ├── KanbanBoard.tsx      # 4-stage Incident Kanban lifecycle board
│   │   │   ├── MessageBubble.tsx    # Markdown bubble with typewriter cursor & audio button
│   │   │   ├── QuickActions.tsx     # Collapsible one-click suggested queries
│   │   │   └── StatusSidebar.tsx    # Live service health monitor drawer
│   │   ├── hooks/
│   │   │   ├── useChat.ts           # Chat state, conversation ID, typewriter animator
│   │   │   └── useSpeech.ts         # Web Speech API recognition, silence timer, TTS
│   │   └── api/
│   │       └── client.ts            # Axios client & TypeScript models
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── teams-manifest/                  # Microsoft Teams App Package & Icons
│   ├── manifest.json
│   ├── color.png
│   └── outline.png
├── docker-compose.yml               # Production multi-container definition
└── docker-compose.dev.yml           # Local dev container with hot reloading
```

---

## 🚀 Quick Start Guide

### Prerequisites
* **Python 3.10+**
* **Node.js 18+** & `npm`

---

### Step 1: Clone & Configure Backend

```bash
cd backend

# Copy environment template
copy .env.example .env

# Install Python dependencies
pip install -r requirements.txt
```

#### Jira Cloud Setup (Optional but Recommended)
Add your Atlassian credentials in `backend/.env`:
```ini
JIRA_DOMAIN=yourcompany.atlassian.net
JIRA_EMAIL=engineer@yourcompany.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=SCRUM
```

---

### Step 2: Start the Servers

#### Terminal 1 — Backend (FastAPI):
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
* Backend API: `http://localhost:8000`
* Interactive API Docs (Swagger): `http://localhost:8000/docs`

#### Terminal 2 — Frontend (React / Vite):
```bash
cd frontend
npm install
npm run dev
```
* Web Application: `http://localhost:5173`

---

### Option 2: Run with Docker Compose

```bash
docker-compose up --build
```
Access the application at `http://localhost:3000`.

---

## 💬 Sample Queries to Test

| Query | Feature Triggered | Description |
|---|---|---|
| *"What is the status of INC12345?"* | 📋 **Incident Lookup** | Returns priority, assignee, workaround, and service impact |
| *"Show me the timeline for INC12345"* | ⏱️ **Timeline & MTTR** | Reconstructs step-by-step audit trail and calculates resolution duration |
| *"What is the status of Jira ticket SCRUM-5?"* | 🔗 **Live Jira Sync** | Fetches live ticket data, changelog history, and assignee from Jira Cloud |
| *"What are the troubleshooting steps for payment issues?"* | 🧠 **Smart Investigation** | Weighted multi-tier retrieval returning steps, workarounds, and past resolutions |
| *"Is there an outage affecting the auth service?"* | 📊 **Service Health** | Live uptime, error rate %, and active incident dependencies |
| *"Show me the status of all services"* | 🗺️ **System Health** | Global overview across all registered microservices |
| *"What is our average MTTR across incidents?"* | 📈 **MTTR Analytics** | Computes average resolution time across the entire incident catalog |

---

## 🧪 Running Tests

Run the complete test suite (40 unit tests):

```bash
cd backend
pytest tests/ -v
```

```
tests/test_assistant.py::test_incident_status PASSED
tests/test_assistant.py::test_comprehensive_troubleshooting PASSED
tests/test_assistant.py::test_jira_integration PASSED
tests/test_assistant.py::test_mttr_calculation PASSED
...
========================== 40 passed in 0.85s ==========================
```

---

## 🔮 Future Roadmap & Enterprise Scope

1. **Microsoft Teams Sandbox Deployment:**
   - Deploying into an isolated **Microsoft 365 Developer Sandbox** (to satisfy enterprise security policies).
   - Sending interactive **Adaptive Cards** directly into Teams incident war rooms.
2. **Proactive PagerDuty Webhooks:**
   - Automatically triggering AI diagnostic workflows and posting root-cause summaries whenever a P1 ticket is created.
3. **LLM Vector Embeddings:**
   - Vector similarity search (ChromaDB / Pinecone) for multi-language runbook semantic retrieval.

---

## 👥 Contributors

Built with ❤️ for incident response teams and DevOps engineers.
* **Tushar** — Incident Kanban Lifecycle System & Real-Time Jira Cloud Integration
* **Sanjay** — Multimodal Voice Engine, Silence Detection & Streaming UI
* **Manasi** — Smart Investigation Workflow & Multi-Tier Weighted Scoring Algorithm
