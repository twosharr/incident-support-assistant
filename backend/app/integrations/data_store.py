"""
Central data store - loads all mock JSON data on startup and manages incident timelines.
Acts as the mock database layer; seamlessly integrates with live JiraClient when configured.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from app.models import Incident, ServiceHealth, KnowledgeArticle
from app.config import settings


class DataStore:
    _instance = None

    def __init__(self):
        self.incidents: Dict[str, Incident] = {}
        self.services: Dict[str, ServiceHealth] = {}
        self.knowledge_articles: List[KnowledgeArticle] = []
        self.playbooks: dict = {}
        self._loaded = False
        self.load()

    @classmethod
    def get_instance(cls) -> "DataStore":
        if cls._instance is None:
            cls._instance = DataStore()
        return cls._instance

    def load(self):
        if self._loaded:
            return
        data_dir = settings.DATA_DIR

        # Load incidents
        with open(os.path.join(data_dir, "incidents.json"), "r", encoding="utf-8") as f:
            raw = json.load(f)
            for item in raw:
                inc = Incident(**item)
                self._enrich_incident_metrics(inc)
                self.incidents[inc.id] = inc

        # Load services
        with open(os.path.join(data_dir, "services.json"), "r", encoding="utf-8") as f:
            raw = json.load(f)
            for item in raw:
                svc = ServiceHealth(**item)
                self.services[svc.name] = svc

        # Load knowledge base
        with open(os.path.join(data_dir, "knowledge_base.json"), "r", encoding="utf-8") as f:
            raw = json.load(f)
            self.knowledge_articles = [KnowledgeArticle(**item) for item in raw]

        # Load playbooks
        with open(os.path.join(data_dir, "playbooks.json"), "r", encoding="utf-8") as f:
            self.playbooks = json.load(f)

        self._loaded = True
        print(f"[DataStore] Loaded {len(self.incidents)} incidents, "
              f"{len(self.services)} services, "
              f"{len(self.knowledge_articles)} KB articles, "
              f"{len(self.playbooks)} playbooks")

    def _enrich_incident_metrics(self, inc: Incident):
        """Calculate start time, end time, MTTR, and build a realistic timeline if missing."""
        created_dt = self._parse_iso(inc.created_at)
        resolved_dt = self._parse_iso(inc.resolved_at) if inc.resolved_at else None
        
        # If resolved and has resolved_at or updated_at, compute MTTR
        if inc.status.lower() == "resolved":
            if not resolved_dt and inc.updated_at:
                resolved_dt = self._parse_iso(inc.updated_at)
                inc.resolved_at = inc.updated_at
            
            if created_dt and resolved_dt:
                diff_min = max(1, int((resolved_dt - created_dt).total_seconds() / 60))
                inc.mttr_minutes = diff_min
                inc.duration_text = self._format_duration(diff_min)
            else:
                inc.mttr_minutes = 45
                inc.duration_text = "45 min"
        else:
            # Active / In Progress
            if created_dt:
                now_dt = datetime.now(timezone.utc)
                diff_min = max(1, int((now_dt - created_dt).total_seconds() / 60))
                inc.duration_text = f"{self._format_duration(diff_min)} (Ongoing)"
            else:
                inc.duration_text = "Ongoing"

        # Build default timeline if empty
        if not inc.timeline and created_dt:
            time_start = inc.created_at[:16].replace("T", " ")
            events = [
                {"time": time_start, "event": f"🚨 Incident detected: {inc.title}"},
                {"time": self._offset_time(time_start, 5), "event": f"👤 Assigned to {inc.assigned_to}"}
            ]
            if inc.workaround:
                events.append({"time": self._offset_time(time_start, 15), "event": f"🔧 Workaround deployed: {inc.workaround}"})
            if inc.status.lower() == "resolved":
                time_end = inc.resolved_at[:16].replace("T", " ") if inc.resolved_at else self._offset_time(time_start, inc.mttr_minutes or 45)
                events.append({"time": self._offset_time(time_end, -10), "event": f"🔍 Root cause identified: {inc.root_cause or 'Configuration error'}"})
                events.append({"time": time_end, "event": f"✅ Incident resolved & verified: {inc.resolution or 'Service restored'}"})
            inc.timeline = events

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return self.incidents.get(incident_id.upper())

    def list_incidents(
        self,
        status: Optional[str] = None,
        service: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[Incident]:
        results = list(self.incidents.values())
        if status:
            results = [i for i in results if i.status.lower() == status.lower()]
        if service:
            results = [i for i in results if service.lower() in i.service.lower()]
        if priority:
            results = [i for i in results if i.priority.lower() == priority.lower()]
        return results

    def resolve_incident(self, incident_id: str, root_cause: str, resolution: str) -> Optional[Incident]:
        """Mark incident as resolved, record closure time, and compute MTTR."""
        inc = self.get_incident(incident_id)
        if not inc:
            return None

        now_str = datetime.now(timezone.utc).isoformat()
        inc.status = "Resolved"
        inc.resolved_at = now_str
        inc.updated_at = now_str
        inc.root_cause = root_cause
        inc.resolution = resolution
        
        created_dt = self._parse_iso(inc.created_at)
        if created_dt:
            now_dt = datetime.now(timezone.utc)
            diff_min = max(1, int((now_dt - created_dt).total_seconds() / 60))
            inc.mttr_minutes = diff_min
            inc.duration_text = self._format_duration(diff_min)
        
        time_now_formatted = datetime.now().strftime("%Y-%m-%d %H:%M")
        inc.timeline.append({
            "time": time_now_formatted,
            "event": f"✅ Incident resolved by engineer. Fix: {resolution}"
        })
        return inc

    def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        if service_name in self.services:
            return self.services[service_name]
        for key, svc in self.services.items():
            if service_name.lower() in key.lower() or service_name.lower() in svc.display_name.lower():
                return svc
        return None

    def search_knowledge(self, query: str, top_k: int = 3) -> List[KnowledgeArticle]:
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for article in self.knowledge_articles:
            score = 0
            content_lower = article.content.lower()
            title_lower = article.title.lower()
            category_lower = article.category.lower() if getattr(article, "category", None) else ""

            # 1. Exact service/category match
            if query_lower == category_lower or query_lower in category_lower:
                score += 50

            for word in query_words:
                # 1. Category word match
                if word in category_lower:
                    score += 20
                
                # 2. Tag match
                if any(word in tag.lower() for tag in article.tags):
                    score += 15
                
                # 3. Related incident match
                if any(word in inc.lower() for inc in getattr(article, "related_incidents", [])):
                    score += 10
                
                # 4. Keyword match
                if word in title_lower:
                    score += 5
                elif word in content_lower:
                    score += 1

            if score > 0:
                scored.append((score, article))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [art for _, art in scored[:top_k]]

    def find_similar_incidents(self, query: str, resolved_only: bool = True, top_k: int = 3) -> List[Incident]:
        query_lower = query.lower()
        query_words = set(query_lower.split())

        candidates = list(self.incidents.values())
        if resolved_only:
            candidates = [i for i in candidates if i.status.lower() == "resolved"]

        scored = []
        for incident in candidates:
            score = 0
            text = f"{incident.title} {incident.description} {' '.join(incident.tags)}".lower()
            for word in query_words:
                if word in text:
                    score += 1
            if score > 0:
                scored.append((score, incident))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [inc for _, inc in scored[:top_k]]

    def get_playbook(self, service_or_category: str) -> dict:
        key = service_or_category.lower()
        if key in self.playbooks:
            return self.playbooks[key]
        for k in self.playbooks:
            if k in key or key in k:
                return self.playbooks[k]
        return self.playbooks.get("general", {})

    def get_all_services_status(self) -> List[ServiceHealth]:
        return list(self.services.values())

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

    def _offset_time(self, time_str: str, minutes_offset: int) -> str:
        try:
            dt = datetime.strptime(time_str[:16], "%Y-%m-%d %H:%M")
            from datetime import timedelta
            new_dt = dt + timedelta(minutes=minutes_offset)
            return new_dt.strftime("%Y-%m-%d %H:%M")
        except:
            return time_str
