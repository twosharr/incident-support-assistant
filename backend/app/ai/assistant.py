"""
Core AI Orchestrator - Mock LLM mode.
Uses intent classification + keyword routing to simulate LLM behavior.
In production, replace _classify_intent() with real GPT-4o function calls.
"""
import re
import uuid
from typing import List, Tuple, Optional
from app.tools.tool_registry import ToolRegistry, ToolResult
from app.models import ChatMessage, ChatRequest, ChatResponse


# Conversation store (in-memory; use Redis in production)
_conversations: dict = {}


class IntentClassifier:
    """Rule-based intent classifier (replace with LLM in production)."""

    PATTERNS = {
        "get_incident": [
            r"INC\d+",
            r"incident\s+(?:id\s+)?(?:number\s+)?(INC\d+|\d+)",
            r"status\s+of\s+(INC\d+)",
            r"what.*?(INC\d+)",
            r"tell me about (INC\d+)",
            r"details.*?(INC\d+)",
        ],
        "list_active_incidents": [
            r"active incidents",
            r"open incidents",
            r"ongoing incidents",
            r"current outages?",
            r"what.*?incidents.*?right now",
            r"incidents.*?affecting",
            r"any.*?issues.*?with\s+(\w+)",
        ],
        "get_service_health": [
            r"(payment|auth|catalog|order|notification|search|database|infrastructure|api.gateway|cdn|devops).*?(status|health|up|down|working|outage)",
            r"is there.*?outage.*?(payment|auth|catalog|order|notification|search|infrastructure)",
            r"(payment|auth|notification|catalog|order|search).*?(down|not working|failing|broken)",
            r"health.*?(payment|auth|catalog|order|notification|search|database)",
        ],
        "find_similar_incidents": [
            r"similar.*?incident",
            r"past.*?incident",
            r"historical.*?incident",
            r"how was.*?resolved",
            r"resolved in the past",
            r"previous.*?issue",
            r"happened before",
            r"same.*?issue.*?before",
        ],
        "get_troubleshooting_steps": [
            r"troubleshoot",
            r"debug",
            r"how to fix",
            r"steps to resolve",
            r"recommended.*?steps",
            r"what should I do",
            r"how do I",
            r"runbook",
            r"playbook",
        ],
        "search_knowledge_base": [
            r"how.*?work",
            r"documentation",
            r"knowledge base",
            r"what is",
            r"explain",
            r"guide",
            r"best practice",
        ],
        "get_all_services_status": [
            r"all services",
            r"system status",
            r"overall status",
            r"dashboard",
            r"what.*?down",
            r"service overview",
        ],
    }

    SERVICE_KEYWORDS = {
        "payment": ["payment", "checkout", "transaction", "billing", "stripe"],
        "auth": ["auth", "authentication", "login", "session", "token", "logout"],
        "catalog": ["catalog", "product", "listing", "search results"],
        "notification": ["notification", "email", "sms", "push", "alert"],
        "order-service": ["order", "orders", "checkout"],
        "user-service": ["user", "account", "profile", "registration"],
        "infrastructure": ["infrastructure", "kubernetes", "k8s", "load balancer", "cluster"],
        "database": ["database", "db", "postgresql", "postgres", "mysql"],
        "search": ["search", "elasticsearch", "index"],
        "data-pipeline": ["etl", "pipeline", "data warehouse", "analytics"],
        "devops": ["build", "ci/cd", "deployment", "pipeline"],
    }

    def classify(self, message: str) -> Tuple[str, dict]:
        """Returns (intent, params)."""
        msg_upper = message.upper()
        msg_lower = message.lower()

        # Check for incident ID first (highest priority)
        inc_match = re.search(r"INC\d+", msg_upper)
        if inc_match:
            return "get_incident", {"incident_id": inc_match.group()}

        # Check for all-services status
        for pattern in self.PATTERNS["get_all_services_status"]:
            if re.search(pattern, msg_lower):
                return "get_all_services_status", {}

        # Check for service health outage queries
        for pattern in self.PATTERNS["get_service_health"]:
            match = re.search(pattern, msg_lower)
            if match:
                service = self._extract_service(msg_lower)
                return "get_service_health", {"service_name": service or "payment"}

        # Check for active incidents
        for pattern in self.PATTERNS["list_active_incidents"]:
            match = re.search(pattern, msg_lower)
            if match:
                service = self._extract_service(msg_lower)
                params = {"service": service} if service else {}
                return "list_active_incidents", params

        # Check for similar incidents
        for pattern in self.PATTERNS["find_similar_incidents"]:
            if re.search(pattern, msg_lower):
                return "find_similar_incidents", {"description": message}

        # Check for troubleshooting
        for pattern in self.PATTERNS["get_troubleshooting_steps"]:
            if re.search(pattern, msg_lower):
                service = self._extract_service(msg_lower)
                return "get_troubleshooting_steps", {"service_or_issue": service or "general"}

        # Check for KB search
        for pattern in self.PATTERNS["search_knowledge_base"]:
            if re.search(pattern, msg_lower):
                return "search_knowledge_base", {"query": message}

        # Default: KB search
        return "search_knowledge_base", {"query": message}

    def _extract_service(self, text: str) -> Optional[str]:
        for service, keywords in self.SERVICE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return service
        return None


class ResponseFormatter:
    """Formats tool results into human-readable markdown responses."""

    def format(self, intent: str, result: ToolResult, original_query: str) -> Tuple[str, list]:
        """Returns (response_text, sources)."""
        if not result.found and "error" in str(result.data):
            return self._format_not_found(result.data), []

        method = getattr(self, f"_format_{intent}", self._format_generic)
        return method(result, original_query)

    def _format_not_found(self, data: dict) -> str:
        msg = data.get("error", "Information not found.")
        return (
            f"I couldn't find the requested information. {msg}\n\n"
            "**What you can try:**\n"
            "- Check the incident ID format (e.g., INC12345)\n"
            "- Ask about active incidents: *'Show me all active incidents'*\n"
            "- Ask about a service: *'What is the status of the payment service?'*"
        )

    def _format_get_incident(self, result: ToolResult, query: str) -> Tuple[str, list]:
        inc = result.data
        status_emoji = {"In Progress": "🔄", "Active": "🔴", "Resolved": "✅",
                        "Monitoring": "👀", "Open": "🟡", "Scheduled": "📅"}.get(inc["status"], "❓")
        priority_emoji = {"P1": "🚨", "P2": "⚠️", "P3": "📋", "P4": "📌"}.get(inc["priority"], "")

        response = f"## {status_emoji} Incident {inc['id']}: {inc['title']}\n\n"
        response += f"| Field | Value |\n|---|---|\n"
        response += f"| **Status** | {inc['status']} |\n"
        response += f"| **Priority** | {priority_emoji} {inc['priority']} — {inc['severity']} |\n"
        response += f"| **Service** | {inc['service']} |\n"
        response += f"| **Assigned To** | {inc['assigned_to']} |\n"
        response += f"| **Created** | {inc['created_at'][:10]} |\n"
        response += f"| **Last Updated** | {inc['updated_at'][:10]} |\n"

        if inc.get("estimated_resolution"):
            response += f"| **Estimated Resolution** | {inc['estimated_resolution'][:16].replace('T', ' ')} UTC |\n"

        response += f"\n**📋 Description:**\n{inc['description']}\n\n"
        response += f"**💥 Impact:**\n{inc['impact']}\n"

        if inc.get("workaround"):
            response += f"\n**🔧 Workaround:**\n> {inc['workaround']}\n"

        if inc.get("root_cause"):
            response += f"\n**🔍 Root Cause:**\n{inc['root_cause']}\n"

        if inc.get("resolution"):
            response += f"\n**✅ Resolution:**\n{inc['resolution']}\n"

        sources = [{"type": "Incident", "id": inc["id"], "title": inc["title"]}]
        return response, sources

    def _format_list_active_incidents(self, result: ToolResult, query: str) -> Tuple[str, list]:
        incidents = result.data
        if not incidents:
            return "✅ No active incidents found right now. All services are operating normally.", []

        response = f"## 🚨 Active Incidents ({len(incidents)} found)\n\n"
        for inc in sorted(incidents, key=lambda x: x["priority"]):
            status_emoji = {"In Progress": "🔄", "Active": "🔴", "Monitoring": "👀", "Open": "🟡"}.get(inc["status"], "❓")
            response += f"### {status_emoji} **{inc['id']}** — {inc['title']}\n"
            response += f"- **Priority:** {inc['priority']} | **Service:** {inc['service']} | **Status:** {inc['status']}\n"
            response += f"- {inc['description']}\n"
            if inc.get("workaround"):
                response += f"- 🔧 **Workaround:** {inc['workaround']}\n"
            response += "\n"

        sources = [{"type": "Incident", "id": i["id"], "title": i["title"]} for i in incidents]
        return response, sources

    def _format_get_service_health(self, result: ToolResult, query: str) -> Tuple[str, list]:
        svc = result.data
        status_emoji = {"healthy": "✅", "degraded": "⚠️", "down": "🔴"}.get(svc["status"], "❓")

        response = f"## {status_emoji} {svc['display_name']} — Status: {svc['status'].upper()}\n\n"
        response += f"| Metric | Value |\n|---|---|\n"
        response += f"| **Uptime** | {svc['uptime_percent']}% |\n"
        response += f"| **Error Rate** | {svc['error_rate_percent']}% |\n"

        if svc.get("p99_latency_ms"):
            response += f"| **P99 Latency** | {svc['p99_latency_ms']} ms |\n"

        response += f"| **Team** | {svc['team']} |\n"

        if svc["active_incidents"]:
            response += f"\n**🚨 Active Incidents:**\n"
            for inc_id in svc["active_incidents"]:
                response += f"- [{inc_id}] — ask me for details\n"

        if svc["dependencies"]:
            response += f"\n**🔗 Dependencies:** {', '.join(svc['dependencies'])}\n"

        if svc["status"] == "healthy":
            response += "\n✅ This service is operating normally."
        elif svc["status"] == "degraded":
            response += "\n⚠️ This service is **degraded**. Expect reduced performance or partial failures."
        else:
            response += "\n🔴 This service is **DOWN**. Engineers are actively working on restoration."

        sources = [{"type": "Service Health", "service": svc["name"], "status": svc["status"]}]
        return response, sources

    def _format_find_similar_incidents(self, result: ToolResult, query: str) -> Tuple[str, list]:
        incidents = result.data
        if not incidents:
            return "I couldn't find similar past incidents. This may be a new type of issue.", []

        response = f"## 🔍 Similar Past Incidents\n\nBased on your query, here are the most similar resolved incidents:\n\n"
        for i, inc in enumerate(incidents, 1):
            response += f"### {i}. **{inc['id']}** — {inc['title']}\n"
            response += f"- **Date:** {inc['created_at'][:10]} | **Service:** {inc['service']} | **Priority:** {inc['priority']}\n"
            if inc.get("root_cause"):
                response += f"- **Root Cause:** {inc['root_cause']}\n"
            if inc.get("resolution"):
                response += f"- **How it was resolved:** {inc['resolution']}\n"
            response += "\n"

        response += "\n💡 *Would you like me to pull up troubleshooting steps based on these patterns?*"
        sources = [{"type": "Resolved Incident", "id": i["id"], "title": i["title"]} for i in incidents]
        return response, sources

    def _format_get_troubleshooting_steps(self, result: ToolResult, query: str) -> Tuple[str, list]:
        playbook = result.data
        response = f"## 🔧 {playbook.get('title', 'Troubleshooting Playbook')}\n\n"
        response += "Follow these steps in order:\n\n"
        for step in playbook.get("steps", []):
            response += f"{step}\n\n"

        if playbook.get("escalation"):
            response += f"\n📞 **Escalation:** {playbook['escalation']}\n"

        sources = [{"type": "Playbook", "title": playbook.get("title", "Playbook")}]
        return response, sources

    def _format_search_knowledge_base(self, result: ToolResult, query: str) -> Tuple[str, list]:
        if not result.found:
            return "I couldn't find relevant knowledge base articles. Try rephrasing your query.", []

        articles = result.data
        response = f"## 📚 Knowledge Base Results\n\nFound {len(articles)} relevant article(s):\n\n"
        for art in articles:
            response += f"### 📄 {art['title']}\n"
            response += f"*Category: {art['category']}*\n\n"
            response += f"{art['content'][:400]}...\n\n"
            if art.get("steps"):
                response += "**Key Steps:**\n"
                for step in art["steps"][:4]:
                    response += f"- {step}\n"
            response += "\n---\n\n"

        sources = [{"type": "Knowledge Article", "id": a["id"], "title": a["title"]} for a in articles]
        return response, sources

    def _format_get_all_services_status(self, result: ToolResult, query: str) -> Tuple[str, list]:
        services = result.data
        healthy = [s for s in services if s["status"] == "healthy"]
        degraded = [s for s in services if s["status"] == "degraded"]
        down = [s for s in services if s["status"] == "down"]

        response = "## 📊 System-wide Service Status\n\n"
        overall = "✅ Operational" if not degraded and not down else ("🔴 Major Issues" if down else "⚠️ Partial Degradation")
        response += f"**Overall Status:** {overall}\n\n"

        if down:
            response += "### 🔴 Down\n"
            for s in down:
                response += f"- **{s['display_name']}** (Error Rate: {s['error_rate_percent']}%)\n"

        if degraded:
            response += "\n### ⚠️ Degraded\n"
            for s in degraded:
                response += f"- **{s['display_name']}** (Error Rate: {s['error_rate_percent']}%, Uptime: {s['uptime_percent']}%)\n"

        if healthy:
            response += "\n### ✅ Healthy\n"
            for s in healthy:
                response += f"- **{s['display_name']}** ({s['uptime_percent']}% uptime)\n"

        sources = [{"type": "Service Status", "service": s["name"]} for s in services]
        return response, sources

    def _format_generic(self, result: ToolResult, query: str) -> Tuple[str, list]:
        return str(result.data), []


class AIAssistant:
    """Main AI orchestrator for the Incident Support Assistant."""

    GREETING_KEYWORDS = ["hello", "hi", "hey", "help", "start", "what can you do"]
    GREETING_RESPONSE = """👋 **Hi! I'm your AI Incident Support Assistant.**

I can help you with:
- 📋 **Incident Status** — *"What is the status of INC12345?"*
- 🚨 **Active Outages** — *"Is there an outage affecting the payment service?"*
- 🔍 **Past Incidents** — *"How was a similar incident resolved in the past?"*
- 🔧 **Troubleshooting** — *"What are the troubleshooting steps for database issues?"*
- 📊 **Service Health** — *"Show me the status of all services"*
- 📚 **Knowledge Base** — *"How do I manage database connection pools?"*

What can I help you with today?"""

    def __init__(self):
        self.tools = ToolRegistry()
        self.classifier = IntentClassifier()
        self.formatter = ResponseFormatter()

    def chat(self, request: ChatRequest) -> ChatResponse:
        conv_id = request.conversation_id or str(uuid.uuid4())
        message = request.message.strip()

        # Handle greetings
        if any(kw in message.lower() for kw in self.GREETING_KEYWORDS) and len(message.split()) <= 5:
            return ChatResponse(
                response=self.GREETING_RESPONSE,
                sources=[],
                tools_used=[],
                conversation_id=conv_id
            )

        # Classify intent
        intent, params = self.classifier.classify(message)

        # Execute tool
        result = self.tools.execute(intent, **params)

        # Format response
        response_text, sources = self.formatter.format(intent, result, message)

        # Store conversation
        if conv_id not in _conversations:
            _conversations[conv_id] = []
        _conversations[conv_id].append({"role": "user", "content": message})
        _conversations[conv_id].append({"role": "assistant", "content": response_text})

        return ChatResponse(
            response=response_text,
            sources=sources,
            tools_used=[intent],
            conversation_id=conv_id
        )
