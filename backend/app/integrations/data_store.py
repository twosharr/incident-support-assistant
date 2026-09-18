"""
Central data store - loads all mock JSON data on startup.
Acts as the mock database layer; swap with real DB/API clients in production.
"""
import json
import os
from typing import Dict, List, Optional
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
        with open(os.path.join(data_dir, "incidents.json"), "r") as f:
            raw = json.load(f)
            for item in raw:
                inc = Incident(**item)
                self.incidents[inc.id] = inc

        # Load services
        with open(os.path.join(data_dir, "services.json"), "r") as f:
            raw = json.load(f)
            for item in raw:
                svc = ServiceHealth(**item)
                self.services[svc.name] = svc

        # Load knowledge base
        with open(os.path.join(data_dir, "knowledge_base.json"), "r") as f:
            raw = json.load(f)
            self.knowledge_articles = [KnowledgeArticle(**item) for item in raw]

        # Load playbooks
        with open(os.path.join(data_dir, "playbooks.json"), "r") as f:
            self.playbooks = json.load(f)

        self._loaded = True
        print(f"[DataStore] Loaded {len(self.incidents)} incidents, "
              f"{len(self.services)} services, "
              f"{len(self.knowledge_articles)} KB articles, "
              f"{len(self.playbooks)} playbooks")

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

    def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        # Try exact match first
        if service_name in self.services:
            return self.services[service_name]
        # Fuzzy match
        for key, svc in self.services.items():
            if service_name.lower() in key.lower() or service_name.lower() in svc.display_name.lower():
                return svc
        return None

    def search_knowledge(self, query: str, top_k: int = 3) -> List[KnowledgeArticle]:
        """Simple keyword-based search (no embedding needed for mock mode)."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for article in self.knowledge_articles:
            score = 0
            content_lower = article.content.lower()
            title_lower = article.title.lower()

            # Title match is worth more
            for word in query_words:
                if word in title_lower:
                    score += 3
                if word in content_lower:
                    score += 1
                if word in article.tags:
                    score += 2

            if score > 0:
                scored.append((score, article))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [art for _, art in scored[:top_k]]

    def find_similar_incidents(self, query: str, resolved_only: bool = True, top_k: int = 3) -> List[Incident]:
        """Find similar past incidents using keyword matching."""
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
        """Return troubleshooting playbook for a service or use the general one."""
        key = service_or_category.lower()
        if key in self.playbooks:
            return self.playbooks[key]
        # Fuzzy match
        for k in self.playbooks:
            if k in key or key in k:
                return self.playbooks[k]
        return self.playbooks.get("general", {})

    def get_all_services_status(self) -> List[ServiceHealth]:
        return list(self.services.values())
