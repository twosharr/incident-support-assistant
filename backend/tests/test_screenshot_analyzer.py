from app.ai.screenshot_analyzer import ScreenshotAnalyzer


def test_analyze_text_detects_database_timeout():
    analyzer = ScreenshotAnalyzer()
    result = analyzer.analyze_text(
        "ERROR 500\nDatabase connection timeout\nConnection pool exhausted\nPayment service failing"
    )

    assert result["affected_service"] == "database"
    assert result["severity"] == "high"
    assert "connection pool exhausted" in result["likely_root_cause"].lower()
    assert "database connection timeout" in result["detected_issue"].lower()


def test_analyze_text_prioritizes_infrastructure_terms():
    analyzer = ScreenshotAnalyzer()
    result = analyzer.analyze_text(
        "LOAD BALANCER\n"
        "ingress-lb-02\n"
        "health check failed\n"
        "Service Unavailable\n"
        "SSL certificate expired on edge-lb\n"
        "Backend targets down\n"
        "Target group unhealthy"
    )

    assert result["affected_service"] == "infrastructure"
    assert result["severity"] == "high"
    assert "load balancer" in result["likely_root_cause"].lower() or "ssl certificate" in result["likely_root_cause"].lower() or "health check" in result["likely_root_cause"].lower()


def test_analyze_text_handles_no_readable_content():
    analyzer = ScreenshotAnalyzer()
    result = analyzer.analyze_text("   \n\n  ")

    assert result["error"] == "No recognizable incident information was detected in the image."
