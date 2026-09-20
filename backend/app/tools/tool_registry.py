"""
MCP-style tool registry. Each tool is a function with a schema descriptor.
The AI orchestrator uses these to respond to user queries.
"""
from typing import Optional, List, Dict, Any
from app.integrations.data_store import DataStore


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
            "description": "Fetch the status and details of a specific incident by ID (e.g., INC12345)",
            "params": ["incident_id"]
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
        incident = self.store.get_incident(incident_id)
        if not incident:
            return ToolResult("get_incident", {"error": f"Incident {incident_id} not found"}, found=False)
        return ToolResult("get_incident", incident.model_dump())

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
