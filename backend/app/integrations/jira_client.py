"""
Live Jira Cloud REST API v3 Integration Client (Sync & Thread-Safe).
Uses standard synchronous httpx.Client to work seamlessly inside FastAPI routes,
Bot Framework handlers, and command-line scripts without asyncio event loop conflicts.
"""
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.config import settings


class JiraClient:
    def __init__(self):
        self.domain = settings.JIRA_DOMAIN.strip().replace("https://", "").replace("http://", "").rstrip("/")
        self.email = settings.JIRA_EMAIL.strip()
        self.token = settings.JIRA_API_TOKEN.strip()
        self.base_url = f"https://{self.domain}/rest/api/3" if self.domain else ""

    def is_configured(self) -> bool:
        return bool(self.domain and self.email and self.token)

    def test_connection(self) -> Dict[str, Any]:
        """Verify Jira credentials by calling myself endpoint."""
        if not self.is_configured():
            return {"connected": False, "error": "Jira credentials are incomplete in .env"}
        
        url = f"{self.base_url}/myself"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, auth=(self.email, self.token))
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "connected": True,
                        "display_name": data.get("displayName"),
                        "email": data.get("emailAddress"),
                        "domain": self.domain
                    }
                else:
                    return {"connected": False, "status_code": res.status_code, "error": res.text}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Fetch single issue details with changelog for timeline construction."""
        if not self.is_configured():
            return None

        url = f"{self.base_url}/issue/{issue_key.upper().strip()}?expand=changelog"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, auth=(self.email, self.token))
                if res.status_code != 200:
                    print(f"[Jira get_issue {issue_key}] Status: {res.status_code}")
                    return None
                
                raw = res.json()
                fields = raw.get("fields", {})
                
                created_str = fields.get("created")
                updated_str = fields.get("updated")
                resolution_date_str = fields.get("resolutiondate")
                
                created_dt = self._parse_iso(created_str) if created_str else None
                resolved_dt = self._parse_iso(resolution_date_str) if resolution_date_str else None
                
                mttr_minutes = None
                duration_text = "Ongoing"
                
                if created_dt and resolved_dt:
                    diff_seconds = (resolved_dt - created_dt).total_seconds()
                    mttr_minutes = max(0, int(diff_seconds / 60))
                    duration_text = self._format_duration(mttr_minutes)
                elif created_dt:
                    now = datetime.now(timezone.utc)
                    diff_seconds = (now - created_dt).total_seconds()
                    open_minutes = max(0, int(diff_seconds / 60))
                    duration_text = f"{self._format_duration(open_minutes)} (Open)"

                timeline = self._build_timeline(created_str, raw.get("changelog", {}))
                desc_text = self._extract_adf_text(fields.get("description"))

                return {
                    "id": raw.get("key"),
                    "key": raw.get("key"),
                    "title": fields.get("summary", "Untitled Issue"),
                    "status": fields.get("status", {}).get("name", "Unknown"),
                    "priority": fields.get("priority", {}).get("name", "Medium"),
                    "issue_type": fields.get("issuetype", {}).get("name", "Task"),
                    "assigned_to": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
                    "reporter": fields.get("reporter", {}).get("displayName") if fields.get("reporter") else "Unknown",
                    "created_at": created_str,
                    "updated_at": updated_str,
                    "resolved_at": resolution_date_str,
                    "mttr_minutes": mttr_minutes,
                    "duration_text": duration_text,
                    "description": desc_text,
                    "timeline": timeline,
                    "jira_url": f"https://{self.domain}/browse/{raw.get('key')}"
                }
        except Exception as e:
            print(f"[JiraClient get_issue Error] {e}")
            return None

    def list_recent_issues(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """List recently created Jira issues via JQL."""
        if not self.is_configured():
            return []

        jql = f"project = '{settings.JIRA_PROJECT_KEY}' ORDER BY created DESC" if settings.JIRA_PROJECT_KEY else "ORDER BY created DESC"
        url = f"{self.base_url}/search?jql={jql}&maxResults={max_results}"

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, auth=(self.email, self.token))
                if res.status_code != 200:
                    return []
                
                issues = []
                data = res.json()
                for item in data.get("issues", []):
                    fields = item.get("fields", {})
                    issues.append({
                        "key": item.get("key"),
                        "title": fields.get("summary", ""),
                        "status": fields.get("status", {}).get("name", ""),
                        "priority": fields.get("priority", {}).get("name", ""),
                        "created_at": fields.get("created"),
                        "jira_url": f"https://{self.domain}/browse/{item.get('key')}"
                    })
                return issues
        except Exception as e:
            print(f"[JiraClient list_recent_issues Error] {e}")
            return []

    def _build_timeline(self, created_str: Optional[str], changelog: dict) -> List[Dict[str, str]]:
        events = []
        if created_str:
            events.append({
                "time": created_str[:16].replace("T", " "),
                "event": "🚨 Ticket created in Jira"
            })

        histories = changelog.get("histories", [])
        for history in sorted(histories, key=lambda h: h.get("created", "")):
            time_str = history.get("created", "")[:16].replace("T", " ")
            author = history.get("author", {}).get("displayName", "User")
            for item in history.get("items", []):
                field = item.get("field")
                from_str = item.get("fromString")
                to_str = item.get("toString")
                if field == "status":
                    events.append({
                        "time": time_str,
                        "event": f"🔄 Status changed from [{from_str}] to [{to_str}] by {author}"
                    })
                elif field == "assignee":
                    events.append({
                        "time": time_str,
                        "event": f"👤 Assigned to {to_str} by {author}"
                    })
                elif field == "resolution":
                    events.append({
                        "time": time_str,
                        "event": f"✅ Marked as {to_str} by {author}"
                    })
        return events

    def _parse_iso(self, iso_str: str) -> Optional[datetime]:
        try:
            clean = iso_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean)
        except:
            return None

    def _format_duration(self, minutes: int) -> str:
        if minutes < 60:
            return f"{minutes} min"
        hours = minutes // 60
        rem_min = minutes % 60
        return f"{hours} hr {rem_min} min" if rem_min > 0 else f"{hours} hr"

    def _extract_adf_text(self, adf_node: Any) -> str:
        if not adf_node:
            return "No description provided."
        if isinstance(adf_node, str):
            return adf_node
        if isinstance(adf_node, dict):
            text_parts = []
            if adf_node.get("type") == "text":
                return adf_node.get("text", "")
            for child in adf_node.get("content", []):
                text_parts.append(self._extract_adf_text(child))
            return " ".join([p for p in text_parts if p]).strip()
        return ""


jira_client = JiraClient()
