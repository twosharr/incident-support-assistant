from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))

from app.ai.screenshot_analyzer import ScreenshotAnalyzer
from app.tools.tool_registry import ToolRegistry


folder = ROOT / 'test-assets'
images = sorted(folder.glob('incident_*.png'))

analyzer = ScreenshotAnalyzer()
registry = ToolRegistry()
results = []

for path in images:
    image_bytes = path.read_bytes()
    extracted = analyzer.extract_text(image_bytes)
    analysis = analyzer.analyze_text(extracted)
    request = {
        'service_or_issue': analysis['affected_service'],
        'description': analysis['description'],
    }
    tool_result = registry.execute('get_comprehensive_troubleshooting', **request)
    results.append({
        'filename': path.name,
        'extracted_text': extracted,
        'service': analysis['affected_service'],
        'severity': analysis['severity'],
        'detected_issue': analysis['detected_issue'],
        'likely_root_cause': analysis['likely_root_cause'],
        'smart_investigation_request': request,
        'smart_investigation_response_keys': list(tool_result.data.keys()) if isinstance(tool_result.data, dict) else [],
    })

output_path = folder / 'ocr_validation_results.json'
output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')

print(json.dumps(results, indent=2, ensure_ascii=False))
