"""
Test suite for the AI Incident Support Assistant.
"""
from pathlib import Path
import tempfile

import pytest
from app.config import Settings
from app.integrations.data_store import DataStore
from app.tools.tool_registry import ToolRegistry
from app.ai.assistant import AIAssistant, IntentClassifier, ResponseFormatter
from app.ai.llm_client import LLMFallbackClient
from app.models import ChatRequest


@pytest.fixture(autouse=True)
def load_data():
    store = DataStore.get_instance()
    store.load()


class TestDataStore:
    def test_get_incident_exists(self):
        store = DataStore.get_instance()
        inc = store.get_incident("INC12345")
        assert inc is not None
        assert inc.id == "INC12345"
        assert inc.service == "payment"

    def test_get_incident_not_found(self):
        store = DataStore.get_instance()
        inc = store.get_incident("INC00000")
        assert inc is None

    def test_get_incident_case_insensitive(self):
        store = DataStore.get_instance()
        inc = store.get_incident("inc12345")
        assert inc is not None

    def test_list_active_incidents(self):
        store = DataStore.get_instance()
        active = store.list_incidents()
        active_filtered = [i for i in active if i.status.lower() in ["in progress", "active", "open", "monitoring"]]
        assert len(active_filtered) > 0

    def test_list_incidents_by_service(self):
        store = DataStore.get_instance()
        payment_incidents = store.list_incidents(service="payment")
        assert len(payment_incidents) > 0
        for inc in payment_incidents:
            assert "payment" in inc.service.lower()

    def test_get_service_health(self):
        store = DataStore.get_instance()
        svc = store.get_service_health("payment")
        assert svc is not None
        assert svc.name == "payment"

    def test_search_knowledge_returns_results(self):
        store = DataStore.get_instance()
        results = store.search_knowledge("payment gateway timeout")
        assert len(results) > 0
        assert any("payment" in a.title.lower() or "payment" in a.content.lower() for a in results)

    def test_find_similar_incidents(self):
        store = DataStore.get_instance()
        results = store.find_similar_incidents("payment gateway timeout", resolved_only=True)
        assert len(results) > 0
        for inc in results:
            assert inc.status.lower() == "resolved"

    def test_get_playbook_payment(self):
        store = DataStore.get_instance()
        playbook = store.get_playbook("payment")
        assert playbook is not None
        assert "steps" in playbook
        assert len(playbook["steps"]) > 0

    def test_get_playbook_fallback_to_general(self):
        store = DataStore.get_instance()
        playbook = store.get_playbook("unknown-service-xyz")
        assert playbook is not None
        assert "steps" in playbook


class TestSettings:
    def test_env_file_values_with_spaces_are_trimmed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "GEMINI_API_KEY= gemini_test_key\nGEMINI_MODEL= gemini-3.6-flash\n",
                encoding="utf-8",
            )

            values = Settings._read_env_file(env_path)

            assert values["GEMINI_API_KEY"] == "gemini_test_key"
            assert values["GEMINI_MODEL"] == "gemini-3.6-flash"

        settings = Settings()
        assert settings.GEMINI_API_KEY
        assert settings.GEMINI_MODEL == "gemini-3.6-flash"


class TestToolRegistry:
    def test_get_incident_tool(self):
        registry = ToolRegistry()
        result = registry.execute("get_incident", incident_id="INC12345")
        assert result.found is True
        assert result.data["id"] == "INC12345"

    def test_get_incident_not_found(self):
        registry = ToolRegistry()
        result = registry.execute("get_incident", incident_id="INC00000")
        assert result.found is False

    def test_list_active_incidents_tool(self):
        registry = ToolRegistry()
        result = registry.execute("list_active_incidents")
        assert result.found is True
        assert isinstance(result.data, list)
        assert len(result.data) > 0

    def test_list_active_incidents_by_service(self):
        registry = ToolRegistry()
        result = registry.execute("list_active_incidents", service="payment")
        assert result.found is True
        for inc in result.data:
            assert "payment" in inc["service"]

    def test_get_service_health_tool(self):
        registry = ToolRegistry()
        result = registry.execute("get_service_health", service_name="payment")
        assert result.found is True
        assert result.data["name"] == "payment"

    def test_search_knowledge_base_tool(self):
        registry = ToolRegistry()
        result = registry.execute("search_knowledge_base", query="database connection pool")
        assert result.found is True
        assert isinstance(result.data, list)

    def test_find_similar_incidents_tool(self):
        registry = ToolRegistry()
        result = registry.execute("find_similar_incidents", description="payment gateway timeout")
        assert result.found is True

    def test_get_troubleshooting_steps_tool(self):
        registry = ToolRegistry()
        result = registry.execute("get_troubleshooting_steps", service_or_issue="payment")
        assert result.found is True
        assert "steps" in result.data

    def test_get_comprehensive_troubleshooting_tool(self):
        registry = ToolRegistry()
        result = registry.execute("get_comprehensive_troubleshooting", service_or_issue="payment", description="payment gateway timeout")
        assert result.found is True
        data = result.data
        assert "troubleshooting_playbook" in data
        assert "active_incidents_with_workarounds" in data
        assert "similar_past_incidents" in data
        assert "knowledge_articles" in data

    def test_get_all_services_status_tool(self):
        registry = ToolRegistry()
        result = registry.execute("get_all_services_status")
        assert result.found is True
        assert isinstance(result.data, list)
        assert len(result.data) > 0

    def test_unknown_tool(self):
        registry = ToolRegistry()
        result = registry.execute("nonexistent_tool")
        assert result.found is False


class TestIntentClassifier:
    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_classify_incident_id(self):
        intent, params = self.classifier.classify("What is the status of INC12345?")
        assert intent == "get_incident"
        assert params["incident_id"] == "INC12345"

    def test_classify_jira_key(self):
        intent, params = self.classifier.classify("What is the status of KAN-1?")
        assert intent == "get_incident"
        assert params["incident_id"] == "KAN-1"

    def test_classify_timeline_query(self):
        intent, params = self.classifier.classify("Show me the timeline of events for INC12345")
        assert intent == "get_incident_timeline"
        assert params["incident_id"] == "INC12345"

    def test_classify_mttr_query(self):
        intent, params = self.classifier.classify("What is our average MTTR?")
        assert intent == "get_mttr_metrics"

    def test_classify_payment_outage(self):
        intent, params = self.classifier.classify("Is there an outage affecting the payment service?")
        assert intent == "get_comprehensive_troubleshooting"
        assert params["service_or_issue"] == "payment"

    def test_classify_payment_status(self):
        intent, params = self.classifier.classify("What is the health status of the payment service?")
        assert intent == "get_service_health"
        assert params["service_name"] == "payment"

    def test_classify_similar_incidents(self):
        intent, params = self.classifier.classify("How was a similar incident resolved in the past?")
        assert intent == "find_similar_incidents"

    def test_classify_troubleshooting(self):
        intent, params = self.classifier.classify("What are the troubleshooting steps for database issues?")
        assert intent == "get_comprehensive_troubleshooting"
        assert params["service_or_issue"] == "database"

    def test_classify_all_services(self):
        intent, params = self.classifier.classify("Show me the status of all services")
        assert intent == "get_all_services_status"

    def test_classify_active_incidents(self):
        intent, params = self.classifier.classify("Show me all active incidents")
        assert intent == "list_active_incidents"


class TestAIAssistant:
    def setup_method(self):
        self.assistant = AIAssistant()

    def test_llm_fallback_does_not_truncate_mid_sentence(self):
        client = LLMFallbackClient(api_key="fake-key")

        long_text = " ".join([
            "Kubernetes is an open-source container orchestration platform used to automate the deployment, scaling, and management of containerized applications.",
            "It groups containers into pods and keeps them running across a cluster of machines.",
            "Kubernetes handles scheduling, self-healing, service discovery, and load balancing.",
            "It is widely used with Docker and cloud platforms to run resilient applications at scale.",
            "In practice, teams rely on Kubernetes to manage application availability, rollouts, and recovery without manual intervention.",
            "Kubernetes is an open-source container orchestration platform used to automate the deployment, scaling, and management of containerized applications.",
            "It groups containers into pods and keeps them running across a cluster of machines.",
            "Kubernetes handles scheduling, self-healing, service discovery, and load balancing.",
            "It is widely used with Docker and cloud platforms to run resilient applications at scale.",
            "In practice, teams rely on Kubernetes to manage application availability, rollouts, and recovery without manual intervention.",
            "Kubernetes is an open-source container orchestration platform used to automate the deployment, scaling, and management of containerized applications.",
            "It groups containers into pods and keeps them running across a cluster of machines.",
            "Kubernetes handles scheduling, self-healing, service discovery, and load balancing.",
            "It is widely used with Docker and cloud platforms to run resilient applications at scale.",
            "In practice, teams rely on Kubernetes to manage application availability, rollouts, and recovery without manual intervention.",
            "Kubernetes is an open-source container orchestration platform used to automate the deployment, scaling, and management of containerized applications.",
            "It groups containers into pods and keeps them running across a cluster of machines.",
            "Kubernetes handles scheduling, self-healing, service discovery, and load balancing.",
            "It is widely used with Docker and cloud platforms to run resilient applications at scale.",
            "In practice, teams rely on Kubernetes to manage application availability, rollouts, and recovery without manual intervention."
        ])

        class DummyPart:
            def __init__(self, text):
                self.text = text

        class DummyContent:
            def __init__(self, text):
                self.parts = [DummyPart(text)]

        class DummyCandidate:
            def __init__(self, text):
                self.content = DummyContent(text)

        class DummyResponse:
            def __init__(self, text):
                self.candidates = [DummyCandidate(text)]

        class DummyModels:
            def generate_content(self, *args, **kwargs):
                return DummyResponse(long_text)

        client.client = type("DummyClient", (), {"models": DummyModels()})()

        response = client.get_response("What is Kubernetes?")

        assert response.endswith(".")
        assert "..." not in response
        assert "Kubernetes is an open-source container orchestration platform" in response
        assert "self-healing" in response

    def test_greeting(self):
        request = ChatRequest(message="Hello")
        response = self.assistant.chat(request)
        assert response.response is not None
        assert "Welcome" in response.response or "help" in response.response.lower() or "hi" in response.response.lower()
        assert response.conversation_id is not None

    def test_incident_query(self):
        request = ChatRequest(message="What is the status of INC12345?")
        response = self.assistant.chat(request)
        assert "INC12345" in response.response
        assert "get_incident" in response.tools_used

    def test_timeline_query(self):
        request = ChatRequest(message="Show me the timeline of events for INC12345")
        response = self.assistant.chat(request)
        assert "Timeline" in response.response or "Event" in response.response
        assert "get_incident_timeline" in response.tools_used

    def test_mttr_analytics_query(self):
        request = ChatRequest(message="What is our average MTTR?")
        response = self.assistant.chat(request)
        assert "MTTR" in response.response or "Mean Time to Resolve" in response.response
        assert "get_mttr_metrics" in response.tools_used

    def test_service_health_query(self):
        request = ChatRequest(message="What is the health status of the payment service?")
        response = self.assistant.chat(request)
        assert response.response is not None
        assert len(response.tools_used) > 0
        assert "get_service_health" in response.tools_used

    def test_similar_incidents_query(self):
        request = ChatRequest(message="Show me past incidents similar to payment gateway timeout")
        response = self.assistant.chat(request)
        assert response.response is not None

    def test_troubleshooting_query(self):
        request = ChatRequest(message="What are the troubleshooting steps for payment issues?")
        response = self.assistant.chat(request)
        assert response.response is not None
        assert "Diagnostics" in response.response or "Troubleshooting" in response.response
        assert "get_comprehensive_troubleshooting" in response.tools_used

    def test_conversation_id_preserved(self):
        conv_id = "test-conv-123"
        request = ChatRequest(message="What is the status of INC12345?", conversation_id=conv_id)
        response = self.assistant.chat(request)
        assert response.conversation_id == conv_id

    def test_general_knowledge_query_uses_llm_fallback(self):
        self.assistant.llm_client.api_key = "fake-key"
        self.assistant.llm_client.get_response = lambda message: "Kubernetes is a container orchestration platform."

        request = ChatRequest(message="What is Kubernetes?")
        response = self.assistant.chat(request)
        assert response.response == "Kubernetes is a container orchestration platform."
        assert "llm_fallback" in response.tools_used

    def test_general_knowledge_query_without_api_key_returns_unavailable(self):
        self.assistant.llm_client.api_key = ""

        request = ChatRequest(message="Difference between Redis and Memcached?")
        response = self.assistant.chat(request)
        assert response.response == "LLM fallback is currently unavailable."
        assert "llm_fallback" in response.tools_used

    def test_general_knowledge_query_on_quota_error_returns_quota_message(self):
        self.assistant.llm_client.api_key = "fake-key"
        self.assistant.llm_client.client = type("Client", (), {
            "models": type("Models", (), {
                "generate_content": lambda *args, **kwargs: (_ for _ in ()).throw(Exception("429 RESOURCE_EXHAUSTED. quota exceeded for free tier requests"))
            })()
        })()

        request = ChatRequest(message="What is Kubernetes?")
        response = self.assistant.chat(request)
        assert response.response == "Gemini fallback is temporarily unavailable due to API quota limits. Please retry in a few moments."
        assert "llm_fallback" in response.tools_used

    def test_all_services_status(self):
        request = ChatRequest(message="Show me the status of all services")
        response = self.assistant.chat(request)
        assert response.response is not None
        assert "Service" in response.response or "status" in response.response.lower()
