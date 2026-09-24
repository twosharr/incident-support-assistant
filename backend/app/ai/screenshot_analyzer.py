import io
import logging
import re
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import easyocr
except Exception:  # pragma: no cover - handled at runtime
    easyocr = None

from PIL import Image

logger = logging.getLogger(__name__)


class ScreenshotAnalyzer:
    """OCR-based extraction and incident classification for screenshot troubleshooting."""

    SERVICE_KEYWORDS = {
        "database": {
            "database": 5,
            "db": 3,
            "postgres": 4,
            "postgresql": 4,
            "mysql": 4,
            "connection pool": 5,
            "sql": 3,
            "query backlog": 3,
            "read timeout": 3,
        },
        "payment": {
            "payment": 5,
            "checkout": 5,
            "transaction": 4,
            "billing": 4,
            "charge": 4,
            "stripe": 4,
            "gateway": 3,
            "processor": 3,
            "retries": 2,
        },
        "auth": {
            "auth": 5,
            "authentication": 5,
            "login": 4,
            "session": 4,
            "token": 4,
            "jwt": 4,
            "logout": 4,
            "unauthorized": 4,
            "redis": 3,
        },
        "search": {
            "search": 5,
            "elasticsearch": 5,
            "index": 4,
            "reindex": 4,
            "lucene": 4,
        },
        "catalog": {
            "catalog": 5,
            "product": 4,
            "listing": 4,
            "inventory": 3,
        },
        "notification": {
            "notification": 5,
            "email": 4,
            "sms": 4,
            "push": 4,
            "alert": 2,
            "mailer": 4,
            "queue": 3,
            "lag": 2,
            "consumer": 2,
        },
        "infrastructure": {
            "infrastructure": 8,
            "load balancer": 10,
            "ingress": 10,
            "ingress controller": 11,
            "nginx": 10,
            "reverse proxy": 10,
            "ssl certificate": 10,
            "backend pool": 10,
            "backend targets": 10,
            "target group": 10,
            "health check": 9,
            "health check failed": 10,
            "kubernetes": 9,
            "k8s": 9,
            "node": 7,
            "cluster": 7,
            "service unavailable": 6,
            "backend target": 9,
            "proxy": 6,
            "oom": 5,
            "connection resets": 6,
        },
        "devops": {
            "build": 4,
            "ci/cd": 4,
            "deployment": 4,
            "pipeline": 4,
            "disk space": 5,
            "artifact": 3,
        },
    }

    def extract_text(self, image_bytes: bytes) -> str:
        logger.info("OCR started")
        if easyocr is None:
            logger.error("EasyOCR is not available in the current environment.")
            raise RuntimeError("EasyOCR is not available in the current environment.")

        reader = easyocr.Reader(["en"], gpu=False)
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        image_array = np.asarray(image)
        logger.info("OCR reading image array with shape=%s", image_array.shape)
        results = reader.readtext(image_array)
        extracted = []
        for entry in results:
            if not entry or len(entry) < 2:
                continue
            text = str(entry[1]).strip()
            if text:
                extracted.append(text)

        extracted_text = "\n".join(extracted).strip()
        logger.info("OCR completed. Extracted text: %s", extracted_text)
        return extracted_text

    def analyze_text(self, text: str) -> Dict[str, Any]:
        logger.info("Text analysis started with raw text=%s", text)
        normalized = self._normalize_text(text)
        if not normalized:
            logger.warning("No recognizable incident information detected after normalization")
            return {
                "error": "No recognizable incident information was detected in the image.",
                "detected_issue": "",
                "affected_service": "general",
                "severity": "medium",
                "likely_root_cause": "",
                "extracted_error_details": "",
                "description": "",
                "source_text": "",
            }

        service = self.detect_service(normalized)
        issue = self.detect_issue(normalized)
        severity = self.detect_severity(normalized)
        root_cause = self.detect_root_cause(normalized)
        logger.info("Classification result: service=%s, issue=%s, severity=%s, root_cause=%s", service, issue, severity, root_cause)

        if not issue:
            issue = self._pick_default_issue(normalized)

        if not issue:
            logger.warning("No issue detected from normalized text")
            return {
                "error": "No recognizable incident information was detected in the image.",
                "detected_issue": "",
                "affected_service": service or "general",
                "severity": severity,
                "likely_root_cause": root_cause,
                "extracted_error_details": normalized,
                "description": normalized,
                "source_text": normalized,
            }

        description = issue
        if root_cause:
            description = f"{issue}. {root_cause}"

        result = {
            "error": None,
            "detected_issue": issue,
            "affected_service": service or "general",
            "severity": severity,
            "likely_root_cause": root_cause or "Unable to determine from the screenshot.",
            "extracted_error_details": normalized,
            "description": description,
            "source_text": normalized,
        }
        logger.info("Text analysis completed: %s", result)
        return result

    def analyze_image(self, image_bytes: bytes, filename: str = "") -> Dict[str, Any]:
        logger.info("Image received: filename=%s, size=%s bytes", filename, len(image_bytes))
        try:
            logger.info("OCR started for image=%s", filename)
            extracted = self.extract_text(image_bytes)
            logger.info("OCR completed for image=%s", filename)
        except Exception:
            logger.exception("OCR extraction failed for image=%s", filename)
            return {
                "error": "Unable to analyze the uploaded screenshot.",
                "detected_issue": "",
                "affected_service": "general",
                "severity": "medium",
                "likely_root_cause": "",
                "extracted_error_details": "",
                "description": "",
                "source_text": "",
            }

        if not extracted:
            logger.warning("OCR returned no text for image=%s", filename)
            return {
                "error": "No recognizable incident information was detected in the image.",
                "detected_issue": "",
                "affected_service": "general",
                "severity": "medium",
                "likely_root_cause": "",
                "extracted_error_details": "",
                "description": "",
                "source_text": "",
            }

        analysis = self.analyze_text(extracted)
        logger.info("Final image classification result for %s: %s", filename, analysis)
        return analysis

    def detect_service(self, text: str) -> Optional[str]:
        lowered = text.lower()
        scores: Dict[str, int] = {}

        for service, keywords in self.SERVICE_KEYWORDS.items():
            score = 0
            for keyword, weight in keywords.items():
                if keyword in lowered:
                    score += weight
            if score:
                scores[service] = score

        if not scores:
            return None

        best_service, best_score = max(scores.items(), key=lambda item: item[1])
        if best_service == "notification" and scores.get("infrastructure", 0) >= best_score - 2:
            return "infrastructure"
        return best_service

    def detect_issue(self, text: str) -> str:
        lowered = text.lower()

        if "database connection timeout" in lowered or ("database" in lowered and "timeout" in lowered):
            return "Database connection timeout"
        if "payment gateway" in lowered and "timeout" in lowered:
            return "Payment gateway timeout"
        if "connection pool exhausted" in lowered or ("connection pool" in lowered and "exhausted" in lowered):
            return "Connection pool exhausted"
        if "error 500" in lowered or "500 internal server error" in lowered:
            return "HTTP 500 error"
        if ("load balancer" in lowered or "ingress" in lowered or "target group" in lowered or "backend target" in lowered or "ssl certificate" in lowered) and ("service unavailable" in lowered or "503" in lowered):
            return "Load balancer or ingress outage"
        if "service unavailable" in lowered or "503" in lowered:
            return "Service unavailable"
        if "deadlock" in lowered:
            return "Database deadlock"
        if "outage" in lowered and "payment" in lowered:
            return "Payment service outage"
        if "timeout" in lowered:
            return "Timeout detected"
        if "failed" in lowered:
            return "Service failure detected"
        if "exception" in lowered:
            return "Application exception detected"
        return ""

    def detect_severity(self, text: str) -> str:
        lowered = text.lower()
        if any(term in lowered for term in [
            "sev1",
            "p1",
            "critical",
            "outage",
            "down",
            "fatal",
            "service unavailable",
            "internal server error",
            "database connection timeout",
            "connection pool exhausted",
            "payment service failing",
            "health check failed",
            "ssl certificate expired",
            "target group unhealthy",
            "backend targets down",
        ]):
            return "high"
        if any(term in lowered for term in ["timeout", "error", "failed", "warning", "degraded"]):
            return "medium"
        return "low"

    def detect_root_cause(self, text: str) -> str:
        lowered = text.lower()

        if any(term in lowered for term in ["load balancer", "ingress", "health check", "target group", "backend target", "ssl certificate", "reverse proxy", "nginx"]):
            if "ssl certificate" in lowered:
                return "An expired or misconfigured SSL certificate or edge ingress policy is likely causing the outage."
            if "health check" in lowered or "target group" in lowered or "backend target" in lowered or "load balancer" in lowered:
                return "Load balancer or ingress health checks are likely failing and routing unhealthy backend targets."
            return "Ingress or load balancer routing is likely failing at the edge layer."
        if "connection pool exhausted" in lowered:
            return "Connection pool exhausted is the likely root cause."
        if "database connection timeout" in lowered or "timeout" in lowered:
            return "Database timeout is likely affecting the request path."
        if "deadlock" in lowered:
            return "A database deadlock or lock contention is likely blocking requests."
        if "memory" in lowered and "leak" in lowered:
            return "A memory leak is likely causing elevated resource usage."
        if "jwt" in lowered or "token" in lowered:
            return "Authentication token or session handling is likely failing."
        if "503" in lowered or "service unavailable" in lowered:
            return "Upstream dependency or service availability issue is likely causing the outage."
        if "error 500" in lowered:
            return "An application error is likely surfacing from the failing service path."
        return "No clear root cause could be extracted from the screenshot."

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = text.replace("\r", "\n").replace("\t", " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _pick_default_issue(self, text: str) -> str:
        lowered = text.lower()
        if "error" in lowered:
            return "Application error detected"
        if "timeout" in lowered:
            return "Timeout detected"
        if "outage" in lowered:
            return "Service outage detected"
        return "Incident screenshot indicates a service problem"
