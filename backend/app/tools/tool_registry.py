"""
MCP-style tool registry. Each tool is a function with a schema descriptor.
Seamlessly queries the local mock data store and live Jira Cloud when configured.
"""
import asyncio
from typing import Optional, List, Dict, Any
from app.integrations.data_store import DataStore
from app.integrations.jira_client import jira_client


class ToolResult:
    def __init__(self, tool_name: str, data: Any, found: bool = True):
        self.tool_name = tool_name
        self.data = data
        self.found = found

    def to_dict(self) -> dict:
        return {"tool": self.tool_name, "data": self.data, "found": self.found}


class ToolRegistry:
    """Registry of all available AI tools (MCP-style function calls)."""

    TOOLS = {
        "get_incident": {
            "description": "Fetch the status and details of a specific incident or Jira issue (e.g., INC12345 or KAN-1)",
            "params": ["incident_id"]
        },
        "get_incident_timeline": {
            "description": "Get chronological timeline, start time, close time, and resolution duration (MTTR) for an incident",
            "params": ["incident_id"]
        },
        "get_mttr_metrics": {
            "description": "Calculate Mean Time to Resolve (MTTR) and outage duration analytics across resolved incidents",
            "params": []
        },
        "list_active_incidents": {
            "description": "List all currently active/open incidents, optionally filtered by service",
            "params": ["service (optional)"]
        },
        "get_service_health": {
            "description": "Get the current health status of a specific service (e.g., payment, auth)",
            "params": ["service_name"]
        },
        "search_knowledge_base": {
            "description": "Search the knowledge base for troubleshooting guides and documentation",
            "params": ["query"]
        },
        "find_similar_incidents": {
            "description": "Find past resolved incidents similar to a given description",
            "params": ["description"]
        },
        "get_troubleshooting_steps": {
            "description": "Get step-by-step troubleshooting playbook for a service or issue type",
            "params": ["service_or_issue"]
        },
        "get_all_services_status": {
            "description": "Get a summary of health status for all services",
            "params": []
        },
        "get_comprehensive_troubleshooting": {
            "description": "Aggregate troubleshooting playbooks, active workarounds, past similar incidents, and knowledge base articles.",
            "params": ["service_or_issue", "description"]
        }
    }

    def __init__(self):
        self.store = DataStore.get_instance()

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        method = getattr(self, f"_tool_{tool_name}", None)
        if not method:
            return ToolResult(tool_name, {"error": f"Unknown tool: {tool_name}"}, found=False)
        return method(**kwargs)

    def _tool_get_incident(self, incident_id: str) -> ToolResult:
        inc_key = incident_id.upper().strip()
        
        # 1. Try local data store first
        incident = self.store.get_incident(inc_key)
        if incident:
            return ToolResult("get_incident", incident.model_dump())

        # 2. If configured and looks like a Jira key (e.g. SCRUM-8, KAN-1, PROD-101), query live Jira
        if jira_client.is_configured() and "-" in inc_key:
            jira_issue = jira_client.get_issue(inc_key)
            if jira_issue:
                return ToolResult("get_incident", jira_issue)

        return ToolResult("get_incident", {"error": f"Incident or Jira ticket {incident_id} not found"}, found=False)

    def _tool_get_incident_timeline(self, incident_id: str) -> ToolResult:
        inc_key = incident_id.upper().strip()
        
        # Try local data store
        inc = self.store.get_incident(inc_key)
        if inc:
            return ToolResult("get_incident_timeline", {
                "id": inc.id,
                "title": inc.title,
                "status": inc.status,
                "created_at": inc.created_at,
                "resolved_at": inc.resolved_at,
                "mttr_minutes": inc.mttr_minutes,
                "duration_text": inc.duration_text,
                "timeline": inc.timeline
            })

        # Try live Jira
        if jira_client.is_configured() and "-" in inc_key:
            jira_issue = jira_client.get_issue(inc_key)
            if jira_issue:
                return ToolResult("get_incident_timeline", {
                    "id": jira_issue["key"],
                    "title": jira_issue["title"],
                    "status": jira_issue["status"],
                    "created_at": jira_issue["created_at"],
                    "resolved_at": jira_issue["resolved_at"],
                    "mttr_minutes": jira_issue["mttr_minutes"],
                    "duration_text": jira_issue["duration_text"],
                    "timeline": jira_issue["timeline"],
                    "jira_url": jira_issue["jira_url"]
                })

        return ToolResult("get_incident_timeline", {"error": f"No timeline found for {incident_id}"}, found=False)

    def _tool_get_mttr_metrics(self) -> ToolResult:
        resolved = [i for i in self.store.list_incidents() if i.status.lower() == "resolved" and i.mttr_minutes]
        if not resolved:
            return ToolResult("get_mttr_metrics", {"message": "No resolved incidents with MTTR available"}, found=False)

        total_minutes = sum(i.mttr_minutes for i in resolved)
        avg_mttr = int(total_minutes / len(resolved))
        fastest = min(resolved, key=lambda x: x.mttr_minutes)
        longest = max(resolved, key=lambda x: x.mttr_minutes)

        return ToolResult("get_mttr_metrics", {
            "resolved_count": len(resolved),
            "average_mttr_minutes": avg_mttr,
            "average_mttr_text": self._format_duration(avg_mttr),
            "fastest_resolution": {"id": fastest.id, "title": fastest.title, "mttr": fastest.duration_text},
            "longest_resolution": {"id": longest.id, "title": longest.title, "mttr": longest.duration_text}
        })

    def _tool_list_active_incidents(self, service: Optional[str] = None) -> ToolResult:
        active_statuses = ["in progress", "active", "open", "monitoring"]
        incidents = self.store.list_incidents()
        results = [i for i in incidents if i.status.lower() in active_statuses]
        if service:
            results = [i for i in results if service.lower() in i.service.lower()]
        return ToolResult("list_active_incidents", [i.model_dump() for i in results], found=len(results) > 0)

    def _tool_get_service_health(self, service_name: str) -> ToolResult:
        service = self.store.get_service_health(service_name)
        if not service:
            return ToolResult("get_service_health", {"error": f"Service '{service_name}' not found"}, found=False)
        return ToolResult("get_service_health", service.model_dump())

    def _tool_search_knowledge_base(self, query: str) -> ToolResult:
        articles = self.store.search_knowledge(query, top_k=3)
        if not articles:
            return ToolResult("search_knowledge_base", {"message": "No relevant articles found"}, found=False)
        return ToolResult("search_knowledge_base", [a.model_dump() for a in articles])

    def _tool_find_similar_incidents(self, description: str) -> ToolResult:
        incidents = self.store.find_similar_incidents(description, top_k=3)
        if not incidents:
            return ToolResult("find_similar_incidents", {"message": "No similar past incidents found"}, found=False)
        return ToolResult("find_similar_incidents", [i.model_dump() for i in incidents])

    def _tool_get_troubleshooting_steps(self, service_or_issue: str) -> ToolResult:
        playbook = self.store.get_playbook(service_or_issue)
        if not playbook:
            return ToolResult("get_troubleshooting_steps", {"message": "No playbook found for this service"}, found=False)
        return ToolResult("get_troubleshooting_steps", playbook)

    def _tool_get_all_services_status(self) -> ToolResult:
        services = self.store.get_all_services_status()
        return ToolResult("get_all_services_status", [s.model_dump() for s in services])

    def _tool_get_comprehensive_troubleshooting(self, service_or_issue: str, description: str = "") -> ToolResult:
        query_term = description if description else service_or_issue

        playbook = self.store.get_playbook(service_or_issue)
        
        active_incidents = self.store.list_incidents(service=service_or_issue)
        active_with_workarounds = [
            {"id": i.id, "title": i.title, "status": i.status, "workaround": i.workaround} 
            for i in active_incidents 
            if i.status.lower() in ["in progress", "active", "open", "monitoring"] and i.workaround
        ]
        
        similar_incidents = self.store.find_similar_incidents(query_term, resolved_only=True, top_k=2)
        past_resolutions = [
            {"id": i.id, "title": i.title, "root_cause": i.root_cause, "resolution": i.resolution}
            for i in similar_incidents
        ]
        
        articles = self.store.search_knowledge(query_term, top_k=2)
        
        data = {
            "service_or_issue": service_or_issue,
            "troubleshooting_playbook": playbook,
            "active_incidents_with_workarounds": active_with_workarounds,
            "similar_past_incidents": past_resolutions,
            "knowledge_articles": [a.model_dump() for a in articles]
        }
        return ToolResult("get_comprehensive_troubleshooting", data)

    def _format_duration(self, minutes: int) -> str:
        if minutes < 60:
            return f"{minutes} min"
        hours = minutes // 60
        rem = minutes % 60
        return f"{hours} hr {rem} min" if rem > 0 else f"{hours} hr"
