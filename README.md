# AI Incident Support Assistant 🤖

A full end-to-end AI-powered incident support chatbot for **Microsoft Teams**, built with:
- **FastAPI** backend with Bot Framework integration
- **React + TailwindCSS** Teams-like web UI
- **Mock LLM** (zero API keys needed) with intent classification & tool routing
- **13 rich mock incidents**, 15 KB articles, service health dashboard
- **Docker Compose** for one-command startup

---

## 🚀 Quick Start

### Option 1: Web UI (No Teams registration needed)

```bash
# 1. Clone or open the project
cd incident-support-assistant

# 2. Start backend
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload

# 3. In a new terminal, start frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** → Start chatting!

---

### Option 2: Docker Compose (Production build)

```bash
cp .env.example .env
docker-compose up --build
```

Open **http://localhost:3000**

---

### Option 3: Docker Compose Dev (Hot-reload)

```bash
cp .env.example .env
docker-compose -f docker-compose.dev.yml up
```

---

## 💬 Sample Queries to Try

| Query | What happens |
|---|---|
| `What is the status of INC12345?` | Fetches incident details + impact + workaround |
| `Is there an outage affecting the payment service?` | Returns service health + active incidents |
| `Show me all active incidents` | Lists all open/in-progress incidents |
| `How was a similar incident resolved in the past?` | Historical incident search via keyword matching |
| `What are the troubleshooting steps for payment issues?` | Returns step-by-step playbook |
| `Show me the status of all services` | System-wide service health overview |
| `How do I manage database connection pools?` | Knowledge base article search |

---

## 🏗️ Project Structure

```
incident-support-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + Teams webhook
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── ai/
│   │   │   └── assistant.py     # Intent classifier + response formatter
│   │   ├── tools/
│   │   │   └── tool_registry.py # MCP-style tools (7 tools)
│   │   ├── integrations/
│   │   │   └── data_store.py    # Mock data layer
│   │   ├── models/
│   │   │   └── __init__.py      # Pydantic models
│   │   ├── bot/
│   │   │   └── bot_handler.py   # Teams Bot Framework handler
│   │   └── api/
│   │       ├── chat.py          # POST /api/chat
│   │       ├── incidents.py     # GET /api/incidents/*
│   │       └── health.py        # GET /health
│   ├── data/
│   │   ├── incidents.json       # 13 mock incidents
│   │   ├── knowledge_base.json  # 15 KB articles
│   │   ├── services.json        # 12 service health records
│   │   └── playbooks.json       # 6 troubleshooting playbooks
│   ├── tests/
│   │   └── test_assistant.py    # 30+ unit tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Root: Sidebar + ChatWindow
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx   # Main chat UI
│   │   │   ├── MessageBubble.tsx # User/AI message rendering
│   │   │   ├── QuickActions.tsx  # Suggested query chips
│   │   │   └── StatusSidebar.tsx # Live service status panel
│   │   ├── hooks/
│   │   │   └── useChat.ts       # Chat state + API calls
│   │   └── api/
│   │       └── client.ts        # Axios API client
│   └── package.json
├── teams-manifest/
│   └── manifest.json            # Teams app package
├── docker-compose.yml           # Production compose
├── docker-compose.dev.yml       # Dev compose with hot-reload
└── README.md
```

---

## 🔌 API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Send a message, get AI response |
| `GET` | `/api/incidents` | List all incidents |
| `GET` | `/api/incidents/active` | List active incidents |
| `GET` | `/api/incidents/{id}` | Get specific incident |
| `GET` | `/api/incidents/services/health` | All service health |
| `POST` | `/api/messages` | Teams Bot Framework webhook |
| `GET` | `/health` | App health check |
| `GET` | `/docs` | Swagger UI |

---

## 🧪 Running Tests

```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/ -v
```

Expected: **30+ tests**, all passing.

---

## 🤝 Connecting to Real Microsoft Teams

### Prerequisites
- **Azure Bot Service** registration (free)
- Public HTTPS URL (use [ngrok](https://ngrok.com) for local dev)

### Steps

1. **Register a bot** in [Azure Portal](https://portal.azure.com) → Azure Bot
2. Copy `Microsoft App ID` and generate a `Client Secret`
3. Update your `.env`:
   ```
   MICROSOFT_APP_ID=your-app-id
   MICROSOFT_APP_PASSWORD=your-client-secret
   ```
4. Set the messaging endpoint in Azure Bot:
   ```
   https://your-ngrok-url.ngrok-free.app/api/messages
   ```
5. Enable the **Microsoft Teams channel** in Azure Bot
6. Package the Teams manifest:
   - Edit `teams-manifest/manifest.json` → set `"id"` to your App ID
   - Add `color.png` (192×192) and `outline.png` (32×32) icons
   - Zip: `manifest.json + color.png + outline.png`
7. Upload to Teams: Teams → Apps → Upload a custom app

---

## 🔧 Extending to Real ITSM

Replace the mock data layer with real API clients:

```python
# backend/app/integrations/servicenow_client.py
import httpx

class ServiceNowClient:
    def __init__(self, instance_url, username, password):
        self.base = f"https://{instance_url}.service-now.com/api/now"
        self.auth = (username, password)

    async def get_incident(self, inc_id: str):
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base}/table/incident?sysparm_query=number={inc_id}",
                auth=self.auth
            )
            return resp.json()["result"][0]
```

Then swap `DataStore` in `tool_registry.py` with the real client.

---

## 🔐 Security Notes

- All responses cite their source (no hallucination in production RAG mode)
- RBAC: Tie incident data access to Azure AD group membership
- Audit log: All chat queries logged via FastAPI middleware
- PII: Mask sensitive fields before sending to any external LLM

---

## 📈 Upgrading to Real LLM (OpenAI GPT-4o)

Replace `IntentClassifier.classify()` in `assistant.py` with OpenAI function calling:

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

response = await client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": user_message}],
    tools=[...],  # ToolRegistry.TOOLS converted to OpenAI schema
    tool_choice="auto"
)
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, uvicorn |
| Teams Integration | botbuilder-python (Bot Framework SDK) |
| Frontend | React 18, TypeScript, TailwindCSS, Vite |
| AI (Mock) | Keyword-based intent classifier + rule engine |
| AI (Production) | OpenAI GPT-4o / Azure OpenAI (drop-in swap) |
| Data | JSON mock files (swap with real DB/APIs) |
| Containerization | Docker, docker-compose |
