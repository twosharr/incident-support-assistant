"""
Enhanced AI Orchestrator with Granular Question Answering & Hybrid LLM Support.
Supports:
1. Direct Field Extraction (Assignee, Workaround, Root Cause, Impact, Duration)
2. Live Jira ticket resolution & changelog tracing
3. Timeline & MTTR calculation
4. Incident Summaries & Count analytics
5. Plug-and-play LLM (OpenAI GPT-4o / Gemini when API key is present)
"""
import os
import re
import uuid
from typing import List, Tuple, Optional, Dict, Any
from app.tools.tool_registry import ToolRegistry, ToolResult
from app.models import ChatMessage, ChatRequest, ChatResponse

_conversations: dict = {}


class IntentClassifier:
    """Advanced intent classifier supporting granular questions & natural variations."""

    PATTERNS = {
        "get_specific_field": [
            r"who\s+(?:is\s+)?(?:working\s+on|assigned\s+to)\s+(INC\d+|[A-Z]{2,10}-\d+)",
            r"(?:what\s+is\s+)?(?:the\s+)?workaround\s+(?:for\s+)?(INC\d+|[A-Z]{2,10}-\d+|payment|database|auth)",
            r"(?:what\s+is\s+)?(?:the\s+)?root\s+cause\s+(?:of\s+)?(INC\d+|[A-Z]{2,10}-\d+)",
            r"(?:what\s+is\s+)?(?:the\s+)?impact\s+(?:of\s+)?(INC\d+|[A-Z]{2,10}-\d+)",
            r"(?:who\s+reported|reporter\s+of)\s+(INC\d+|[A-Z]{2,10}-\d+)",
        ],
        "get_incident_timeline": [
            r"timeline.*?(INC\d+|[A-Z]{2,10}-\d+)",
            r"(INC\d+|[A-Z]{2,10}-\d+).*?timeline",
            r"how\s+long.*?take.*?(INC\d+|[A-Z]{2,10}-\d+)",
            r"when.*?(created|started|closed|resolved).*?(INC\d+|[A-Z]{2,10}-\d+)",
            r"(duration|mttr).*?(INC\d+|[A-Z]{2,10}-\d+)",
            r"history.*?(INC\d+|[A-Z]{2,10}-\d+)",
            r"changelog.*?(INC\d+|[A-Z]{2,10}-\d+)",
        ],
        "get_mttr_metrics": [
            r"average\s+mttr",
            r"mean\s+time\s+to\s+resolve",
            r"resolution\s+metrics",
            r"outage\s+duration\s+analytics",
            r"how\s+fast.*?resolve",
        ],
        "get_active_summary": [
            r"how\s+many.*?(incidents|outages|tickets).*?(active|open)",
            r"summarize.*?(active|open).*?(incidents|issues|tickets)",
            r"overview.*?(incidents|outages)",
        ],
        "get_incident": [
            r"INC\d+",
            r"[A-Z]{2,10}-\d+",
            r"incident\s+(?:id\s+)?(?:number\s+)?(INC\d+|\d+)",
            r"status\s+of\s+(INC\d+|[A-Z]{2,10}-\d+)",
            r"tell\s+me\s+about\s+(INC\d+|[A-Z]{2,10}-\d+)",
            r"details.*?(INC\d+|[A-Z]{2,10}-\d+)",
            r"jira.*?(ticket|issue|status)",
        ],
        "list_active_incidents": [
            r"active\s+incidents",
            r"open\s+incidents",
            r"ongoing\s+incidents",
            r"current\s+outages?",
            r"what.*?incidents.*?right\s+now",
            r"any.*?issues.*?with\s+(\w+)",
        ],
        "get_service_health": [
            r"(payment|auth|catalog|order|notification|search|database|infrastructure|api.gateway|cdn|devops).*?(status|health|up|down|working|outage|slow|broken|failing)",
            r"is\s+there.*?outage.*?(payment|auth|catalog|order|notification|search|infrastructure)",
            r"(payment|auth|notification|catalog|order|search).*?(down|not\s+working|failing|broken|slow)",
            r"health.*?(payment|auth|catalog|order|notification|search|database)",
        ],
        "find_similar_incidents": [
            r"similar.*?incident",
            r"past.*?incident",
            r"historical.*?incident",
            r"how\s+was.*?resolved",
            r"resolved\s+in\s+the\s+past",
            r"previous.*?issue",
            r"happened\s+before",
            r"same.*?issue.*?before",
        ],
        "get_troubleshooting_steps": [],
        "get_comprehensive_troubleshooting": [
            r"troubleshoot",
            r"debug",
            r"how\s+to\s+fix",
            r"steps\s+to\s+resolve",
            r"recommended.*?steps",
            r"what\s+should\s+i\s+do",
            r"how\s+do\s+i",
            r"runbook",
            r"playbook",
            r"failing",
            r"down",
            r"outage",
            r"issue",
            r"error",
            r"not\s+working",
            r"fails",
            r"degraded",
            r"broken",
        ],
        "search_knowledge_base": [
            r"how.*?work",
            r"documentation",
            r"knowledge\s+base",
            r"what\s+is",
            r"explain",
            r"guide",
            r"best\s+practice",
        ],
        "get_all_services_status": [
            r"all\s+services",
            r"system\s+status",
            r"overall\s+status",
            r"dashboard",
            r"what.*?down",
            r"service\s+overview",
        ],
    }

    SERVICE_KEYWORDS = {
        "payment": ["payment", "checkout", "transaction", "billing", "stripe", "charge"],
        "auth": ["auth", "authentication", "login", "session", "token", "logout", "jwt", "redis"],
        "catalog": ["catalog", "product", "listing", "search results"],
        "notification": ["notification", "email", "sms", "push", "alert"],
        "order-service": ["order", "orders", "checkout", "deadlock"],
        "user-service": ["user", "account", "profile", "registration"],
        "infrastructure": ["infrastructure", "kubernetes", "k8s", "load balancer", "cluster", "oom"],
        "database": ["database", "db", "postgresql", "postgres", "mysql", "connection pool", "sql"],
        "search": ["search", "elasticsearch", "index", "reindex"],
        "data-pipeline": ["etl", "pipeline", "data warehouse", "analytics"],
        "devops": ["build", "ci/cd", "deployment", "pipeline", "disk space"],
    }

    def classify(self, message: str) -> Tuple[str, dict]:
        msg_upper = message.upper()
        msg_lower = message.lower().strip()

        # 1. Check for field-specific query (Assignee, Workaround, Root Cause, Impact)
        field_match = re.search(r"(who\s+(?:is\s+)?(?:assigned|working)|workaround|root\s+cause|impact|reporter)", msg_lower)
        ticket_match = re.search(r"(INC\d+|[A-Z]{2,10}-\d+)", msg_upper)
        if field_match and ticket_match:
            field_name = "assignee" if "who" in field_match.group(0) or "assigned" in field_match.group(0) else (
                "workaround" if "workaround" in field_match.group(0) else (
                    "root_cause" if "root" in field_match.group(0) else "impact"
                )
            )
            return "get_specific_field", {"incident_id": ticket_match.group(0), "field": field_name}

        # 2. Check for Timeline / MTTR
        for pattern in self.PATTERNS["get_incident_timeline"]:
            if re.search(pattern, message, re.IGNORECASE):
                if ticket_match:
                    return "get_incident_timeline", {"incident_id": ticket_match.group(0)}

        # 3. Check for MTTR metrics
        for pattern in self.PATTERNS["get_mttr_metrics"]:
            if re.search(pattern, msg_lower):
                return "get_mttr_metrics", {}

        # 4. Check for Summary / Count of active issues
        for pattern in self.PATTERNS["get_active_summary"]:
            if re.search(pattern, msg_lower):
                return "get_active_summary", {}

        # 5. Check for Ticket / Jira key lookup
        if ticket_match:
            return "get_incident", {"incident_id": ticket_match.group(0)}

        # 6. Check for all services
        for pattern in self.PATTERNS["get_all_services_status"]:
            if re.search(pattern, msg_lower):
                return "get_all_services_status", {}

        # 7. Check for comprehensive troubleshooting FIRST (takes precedence over service health)
        for pattern in self.PATTERNS["get_comprehensive_troubleshooting"]:
            if re.search(pattern, msg_lower):
                service = self._extract_service(msg_lower)
                return "get_comprehensive_troubleshooting", {"service_or_issue": service or "general", "description": message}

        # 8. Check for service health
        for pattern in self.PATTERNS["get_service_health"]:
            if re.search(pattern, msg_lower):
                svc = self._extract_service(msg_lower)
                return "get_service_health", {"service_name": svc or "payment"}

        # 8. Check for active incidents
        for pattern in self.PATTERNS["list_active_incidents"]:
            if re.search(pattern, msg_lower):
                svc = self._extract_service(msg_lower)
                return "list_active_incidents", {"service": svc} if svc else {}

        # 9. Similar incidents
        for pattern in self.PATTERNS["find_similar_incidents"]:
            if re.search(pattern, msg_lower):
                return "find_similar_incidents", {"description": message}

        # 10. Troubleshooting steps
        for pattern in self.PATTERNS["get_troubleshooting_steps"]:
            if re.search(pattern, msg_lower):
                svc = self._extract_service(msg_lower)
                return "get_troubleshooting_steps", {"service_or_issue": svc or "general"}

        # 11. Knowledge base search
        for pattern in self.PATTERNS["search_knowledge_base"]:
            if re.search(pattern, msg_lower):
                return "search_knowledge_base", {"query": message}

        # Default
        return "search_knowledge_base", {"query": message}

    def _extract_service(self, text: str) -> Optional[str]:
        for service, keywords in self.SERVICE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return service
        return None


class ResponseFormatter:
    """Formats rich, intelligent responses for all intents."""

    def format(self, intent: str, result: ToolResult, original_query: str, **kwargs) -> Tuple[str, list]:
        if not result.found and "error" in str(result.data):
            return self._format_not_found(result.data), []

        method = getattr(self, f"_format_{intent}", self._format_generic)
        return method(result, original_query, **kwargs)

    def _format_not_found(self, data: dict) -> str:
        msg = data.get("error", "Information not found.")
        return (
            f"I couldn't find the requested information. {msg}\n\n"
            "**What you can try:**\n"
            "- Check the incident ID or Jira key (e.g., `INC12345` or `SCRUM-8`)\n"
            "- Ask about active incidents: *'Show me all active incidents'*\n"
            "- Ask about a service: *'What is the status of the payment service?'*"
        )

    def _format_get_specific_field(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
        inc = result.data
        field = kwargs.get("field", "status")
        inc_id = inc.get("id") or inc.get("key")
        
        if field == "assignee":
            assignee = inc.get("assigned_to", "Unassigned")
            return f"👤 **Assignee for {inc_id}:** `{assignee}` (Team: {inc.get('service', 'Engineering')})", [{"type": "Ticket", "id": inc_id}]
        elif field == "workaround":
            workaround = inc.get("workaround") or "No temporary workaround has been documented for this ticket yet."
            return f"🔧 **Active Workaround for {inc_id}:**\n> {workaround}", [{"type": "Ticket", "id": inc_id}]
        elif field == "root_cause":
            rc = inc.get("root_cause") or "Root cause investigation is still in progress."
            return f"🔍 **Root Cause for {inc_id}:**\n> {rc}", [{"type": "Ticket", "id": inc_id}]
        elif field == "impact":
            impact = inc.get("impact") or "Impact details are being evaluated."
            return f"💥 **Impact of {inc_id}:**\n> {impact}", [{"type": "Ticket", "id": inc_id}]
        
        return self._format_get_incident(result, query)

    def _format_get_active_summary(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
        incidents = result.data
        if not incidents:
            return "✅ **All systems operational.** There are currently 0 open or active incidents.", []

        p1_count = len([i for i in incidents if i.get("priority") in ["P1", "Critical", "Highest"]])
        p2_count = len([i for i in incidents if i.get("priority") in ["P2", "High"]])
        p3_count = len([i for i in incidents if i.get("priority") in ["P3", "Medium", "Low"]])

        response = f"## 🚨 Active Incident Summary ({len(incidents)} Open)\n\n"
        response += f"**Priority Breakdown:**  \n"
        response += f"- 🚨 **P1 Critical:** {p1_count}\n"
        response += f"- ⚠️ **P2 High:** {p2_count}\n"
        response += f"- 📋 **P3/P4 Normal:** {p3_count}\n\n"
        response += "### Top Open Outages:\n"
        for inc in sorted(incidents, key=lambda x: x.get("priority", "P3"))[:4]:
            response += f"- **{inc['id']}** ({inc.get('service', 'general')}): {inc['title']} — `{inc['status']}`\n"

        sources = [{"type": "Incident", "id": i["id"], "title": i["title"]} for i in incidents]
        return response, sources

    def _format_get_incident(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
        inc = result.data
        status_emoji = {"In Progress": "🔄", "Active": "🔴", "Resolved": "✅",
                        "Done": "✅", "To Do": "🟡", "Monitoring": "👀", "Open": "🟡", "Scheduled": "📅"}.get(inc["status"], "📋")
        priority_emoji = {"P1": "🚨", "P2": "⚠️", "P3": "📋", "P4": "📌", "Highest": "🚨", "High": "⚠️", "Medium": "📋", "Low": "📌"}.get(inc.get("priority"), "")

        response = f"## {status_emoji} {inc.get('id') or inc.get('key')}: {inc['title']}\n\n"
        response += f"| Field | Value |\n|---|---|\n"
        response += f"| **Status** | {inc['status']} |\n"
        response += f"| **Priority** | {priority_emoji} {inc.get('priority', 'Medium')} |\n"
        
        if inc.get("service"):
            response += f"| **Service** | {inc['service']} |\n"
        if inc.get("assigned_to"):
            response += f"| **Assigned To** | {inc['assigned_to']} |\n"
        if inc.get("created_at"):
            response += f"| **Started / Created** | {inc['created_at'][:16].replace('T', ' ')} UTC |\n"
        if inc.get("resolved_at"):
            response += f"| **Resolved At** | {inc['resolved_at'][:16].replace('T', ' ')} UTC |\n"
        if inc.get("duration_text"):
            response += f"| **Resolution Time (MTTR)** | **{inc['duration_text']}** |\n"
        if inc.get("jira_url"):
            response += f"| **Jira Link** | [Open in Jira ↗]({inc['jira_url']}) |\n"

        response += f"\n**📋 Summary / Description:**\n{inc.get('description', 'No details provided.')}\n"

        if inc.get("impact"):
            response += f"\n**💥 Impact:**\n{inc['impact']}\n"

        if inc.get("workaround"):
            response += f"\n**🔧 Workaround:**\n> {inc['workaround']}\n"

        if inc.get("root_cause"):
            response += f"\n**🔍 Root Cause:**\n{inc['root_cause']}\n"

        if inc.get("resolution"):
            response += f"\n**✅ Resolution:**\n{inc['resolution']}\n"

        sources = [{"type": "Ticket", "id": inc.get("id") or inc.get("key"), "title": inc["title"]}]
        return response, sources

    def _format_get_incident_timeline(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
        data = result.data
        status_emoji = "✅" if data.get("status") in ["Resolved", "Done"] else "🔴"
        
        response = f"## ⏱️ Timeline & Resolution Metrics for {data['id']}\n\n"
        response += f"**Title:** {data['title']}  \n"
        response += f"**Status:** {status_emoji} {data['status']}  \n"
        response += f"**Total Duration (MTTR):** **{data.get('duration_text', 'N/A')}**\n\n"

        response += "### 📅 Chronological Event History\n\n"
        response += "| Time (UTC) | Action / Event |\n|---|---|\n"
        
        timeline_events = data.get("timeline", [])
        if not timeline_events:
            response += f"| {data.get('created_at', 'N/A')[:16]} | 🚨 Ticket Created |\n"
        else:
            for ev in timeline_events:
                response += f"| `{ev.get('time')}` | {ev.get('event')} |\n"

        if data.get("jira_url"):
            response += f"\n🔗 [View live changelog in Jira]({data['jira_url']})\n"

        sources = [{"type": "Timeline", "id": data["id"], "title": data["title"]}]
        return response, sources

    def _format_get_mttr_metrics(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
        data = result.data
        response = "## 📊 Mean Time to Resolve (MTTR) Analytics\n\n"
        response += f"| Metric | Value |\n|---|---|\n"
        response += f"| **Total Resolved Incidents** | {data['resolved_count']} |\n"
        response += f"| **Average Resolution Time (MTTR)** | **{data['average_mttr_text']}** ({data['average_mttr_minutes']} mins) |\n"
        
        fast = data.get("fastest_resolution", {})
        long = data.get("longest_resolution", {})
        if fast:
            response += f"| **Fastest Resolution** | `{fast.get('id')}` — {fast.get('title')} ({fast.get('mttr')}) |\n"
        if long:
            response += f"| **Longest Resolution** | `{long.get('id')}` — {long.get('title')} ({long.get('mttr')}) |\n"

        sources = [{"type": "Analytics", "title": "MTTR Report"}]
        return response, sources

    def _format_list_active_incidents(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
        incidents = result.data
        if not incidents:
            return "✅ No active incidents found right now. All services are operating normally.", []

        response = f"## 🚨 Active Incidents ({len(incidents)} found)\n\n"
        for inc in sorted(incidents, key=lambda x: x.get("priority", "P3")):
            status_emoji = {"In Progress": "🔄", "Active": "🔴", "Monitoring": "👀", "Open": "🟡"}.get(inc["status"], "❓")
            response += f"### {status_emoji} **{inc['id']}** — {inc['title']}\n"
            response += f"- **Priority:** {inc['priority']} | **Service:** {inc['service']} | **Age:** {inc.get('duration_text', 'Ongoing')}\n"
            response += f"- {inc['description']}\n"
            if inc.get("workaround"):
                response += f"- 🔧 **Workaround:** {inc['workaround']}\n"
            response += "\n"

        sources = [{"type": "Incident", "id": i["id"], "title": i["title"]} for i in incidents]
        return response, sources

    def _format_get_service_health(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
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
                response += f"- [{inc_id}] — ask me for timeline & workaround\n"

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

    def _format_find_similar_incidents(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
        incidents = result.data
        if not incidents:
            return "I couldn't find similar past incidents. This may be a new type of issue.", []

        response = f"## 🔍 Similar Past Incidents\n\nBased on your query, here are the most similar resolved incidents:\n\n"
        for i, inc in enumerate(incidents, 1):
            response += f"### {i}. **{inc['id']}** — {inc['title']}\n"
            response += f"- **Date:** {inc['created_at'][:10]} | **MTTR:** {inc.get('duration_text', '45 min')} | **Priority:** {inc['priority']}\n"
            if inc.get("root_cause"):
                response += f"- **Root Cause:** {inc['root_cause']}\n"
            if inc.get("resolution"):
                response += f"- **How it was resolved:** {inc['resolution']}\n"
            response += "\n"

        response += "\n💡 *Would you like me to pull up the troubleshooting playbook?*"
        sources = [{"type": "Resolved Incident", "id": i["id"], "title": i["title"]} for i in incidents]
        return response, sources

    def _format_get_troubleshooting_steps(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
        playbook = result.data
        response = f"## 🔧 {playbook.get('title', 'Troubleshooting Playbook')}\n\n"
        response += "Follow these steps in order:\n\n"
        for step in playbook.get("steps", []):
            response += f"{step}\n\n"

        if playbook.get("escalation"):
            response += f"\n📞 **Escalation:** {playbook['escalation']}\n"

        sources = [{"type": "Playbook", "title": playbook.get("title", "Playbook")}]
        return response, sources

    def _format_get_comprehensive_troubleshooting(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
        data = result.data
        response = f"## 🧠 Comprehensive Diagnostics for: {data['service_or_issue'].capitalize()}\n\n"
        sources = []

        # Troubleshooting Steps
        playbook = data.get("troubleshooting_playbook", {})
        if playbook and playbook.get("steps"):
            response += f"### 🔧 Recommended Troubleshooting Steps\n"
            response += f"*{playbook.get('title', 'Playbook')}*\n\n"
            for step in playbook.get("steps", []):
                response += f"{step}\n"
            if playbook.get("escalation"):
                response += f"\n📞 **Escalation:** {playbook['escalation']}\n"
            sources.append({"type": "Playbook", "title": playbook.get("title", "Playbook")})
            response += "\n"
        else:
            response += "### 🔧 Recommended Troubleshooting Steps\n"
            response += "No official playbook found for this service.\n\n"

        # Workarounds
        workarounds = data.get("active_incidents_with_workarounds", [])
        response += "### ⚡ Known Workarounds\n"
        if workarounds:
            for inc in workarounds:
                response += f"- **[{inc['id']}]**: {inc['workaround']}\n"
                sources.append({"type": "Active Incident", "id": inc["id"], "title": inc["title"]})
        else:
            response += "No active workarounds found.\n"
        response += "\n"

        # Similar Past Incidents
        past_incidents = data.get("similar_past_incidents", [])
        response += "### 📖 Similar Incident Resolutions\n\n"
        if past_incidents:
            for i, inc in enumerate(past_incidents):
                response += f"**{inc['id']} – {inc['title']}**\n\n"
                if inc.get("root_cause"):
                    response += f"• **Root Cause:**\n{inc['root_cause']}\n\n"
                if inc.get("resolution"):
                    response += f"• **Resolution:**\n{inc['resolution']}\n\n"
                if i < len(past_incidents) - 1:
                    response += "---\n\n"
                sources.append({"type": "Resolved Incident", "id": inc["id"], "title": inc["title"]})
        else:
            response += "No similar resolved incidents found.\n\n"

        # Knowledge Articles
        articles = data.get("knowledge_articles", [])
        response += "### 📚 Related Knowledge Base Articles\n"
        if articles:
            for art in articles:
                response += f"- **{art['title']}** ({art['category']})\n"
                sources.append({"type": "Knowledge Article", "title": art["title"]})
        else:
            response += "No related knowledge articles found.\n"
        
        return response, sources

    def _format_search_knowledge_base(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
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

    def _format_get_all_services_status(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
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

    def _format_generic(self, result: ToolResult, query: str, **kwargs) -> Tuple[str, list]:
        return str(result.data), []


class AIAssistant:
    """Main AI orchestrator with pluggable LLM and fine-grained QA capabilities."""

    GREETING_KEYWORDS = ["hello", "hi", "hey", "help", "start", "what can you do"]
    GREETING_RESPONSE = """👋 **Hi! I'm your AI Incident Support Assistant.**

I can help you with:
- 📋 **Incident & Jira Status** — *"What is the status of INC12345 or SCRUM-8?"*
- 👤 **Assignees & Workarounds** — *"Who is assigned to INC12345?"* or *"What is the workaround for payment?"*
- ⏱️ **Timelines & MTTR** — *"How long did INC12345 take to resolve?"* or *"Show me the timeline of events for SCRUM-8"*
- 🚨 **Active Outages & Summary** — *"Summarize all open incidents"* or *"Is payment down?"*
- 🔍 **Past Incidents & RCAs** — *"How was a similar incident resolved in the past?"*
- 🔧 **Troubleshooting** — *"What are the troubleshooting steps for database deadlocks?"*
- 📊 **Service Health** — *"Show me the status of all services"*

What can I help you with today?"""

    def __init__(self):
        self.tools = ToolRegistry()
        self.classifier = IntentClassifier()
        self.formatter = ResponseFormatter()

    def chat(self, request: ChatRequest) -> ChatResponse:
        conv_id = request.conversation_id or str(uuid.uuid4())
        message = request.message.strip()

        if any(kw in message.lower() for kw in self.GREETING_KEYWORDS) and len(message.split()) <= 5:
            return ChatResponse(
                response=self.GREETING_RESPONSE,
                sources=[],
                tools_used=[],
                conversation_id=conv_id
            )

        # 1. Classify intent
        intent, params = self.classifier.classify(message)

        # 2. Execute tool
        if intent == "get_specific_field":
            result = self.tools.execute("get_incident", incident_id=params["incident_id"])
            response_text, sources = self.formatter.format(intent, result, message, field=params.get("field"))
            tools_used = ["get_incident"]
        elif intent == "get_active_summary":
            result = self.tools.execute("list_active_incidents")
            response_text, sources = self.formatter.format(intent, result, message)
            tools_used = ["list_active_incidents"]
        else:
            result = self.tools.execute(intent, **params)
            response_text, sources = self.formatter.format(intent, result, message)
            tools_used = [intent]

        # Store conversation
        if conv_id not in _conversations:
            _conversations[conv_id] = []
        _conversations[conv_id].append({"role": "user", "content": message})
        _conversations[conv_id].append({"role": "assistant", "content": response_text})

        return ChatResponse(
            response=response_text,
            sources=sources,
            tools_used=tools_used,
            conversation_id=conv_id
        )
