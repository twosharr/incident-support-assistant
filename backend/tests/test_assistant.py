"""
Test suite for the AI Incident Support Assistant.
"""
import pytest
from app.integrations.data_store import DataStore
from app.tools.tool_registry import ToolRegistry
from app.ai.assistant import AIAssistant, IntentClassifier
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

    def test_all_services_status(self):
        request = ChatRequest(message="Show me the status of all services")
        response = self.assistant.chat(request)
        assert response.response is not None
        assert "Service" in response.response or "status" in response.response.lower()
