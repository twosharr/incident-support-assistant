from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT


CASES: List[Dict[str, str]] = [
    {
        "filename": "incident_01_database_timeout.png",
        "title": "Database Timeout",
        "service": "database",
        "lines": [
            "ALERT: API-DB latency spike",
            "ERROR 500 - payment-api",
            "Database connection timeout",
            "Connection pool exhausted",
            "db-primary-01: read timeout after 30s",
            "db-prod-01: query backlog > 12s",
            "Team: platform-db",
            "Status: P1 / Sev1",
        ],
    },
    {
        "filename": "incident_02_payment_gateway_timeout.png",
        "title": "Payment Gateway Timeout",
        "service": "payment",
        "lines": [
            "ERROR 504 - checkout-service",
            "Payment gateway timeout",
            "Upstream processor timed out after 45s",
            "Transaction retries increased 300%",
            "Charge endpoints returning 504s",
            "SLO breach: checkout latency > 2.5s",
            "Owner: payments-team",
            "Status: degraded",
        ],
    },
    {
        "filename": "incident_03_redis_auth_failure.png",
        "title": "Redis/Auth Failure",
        "service": "auth",
        "lines": [
            "ALERT: auth-redis cache unavailable",
            "JWT validation failed for 12% requests",
            "Redis connection reset by peer",
            "Session refresh failing in eu-west-1",
            "Login failures rising: 42.7%",
            "Error: invalid token / 401 Unauthorized",
            "Owner: identity-platform",
            "Impact: users unable to sign in",
        ],
    },
    {
        "filename": "incident_04_load_balancer_misconfiguration.png",
        "title": "Load Balancer Misconfiguration",
        "service": "infrastructure",
        "lines": [
            "ALERT: ingress-lb-02 health check failed",
            "503 Service Unavailable",
            "Load balancer misconfiguration",
            "Backend pool unhealthy: 4/8 targets down",
            "SSL certificate expired on edge-lb",
            "Connection resets to /api/v1/users",
            "Region: us-east-1",
            "Owner: network-ops",
        ],
    },
    {
        "filename": "incident_05_notification_queue_delay.png",
        "title": "Notification Queue Delay",
        "service": "notification",
        "lines": [
            "ALERT: mailer queue latency increasing",
            "Notification queue delay: 14m backlog",
            "Consumer lag: 18401 messages",
            "Email and SMS dispatch degraded",
            "Retry storm triggered by Kafka lag",
            "SLA breach for user confirmations",
            "Team: comms-platform",
            "Status: monitoring",
        ],
    },
]


def get_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_case(case: Dict[str, str]) -> None:
    width, height = 1800, 1200
    image = Image.new("RGB", (width, height), color=(245, 247, 250))
    draw = ImageDraw.Draw(image)

    margin = 80
    panel_x, panel_y, panel_w, panel_h = 60, 60, width - 120, height - 120
    draw.rounded_rectangle((panel_x, panel_y, panel_w, panel_h), radius=28, fill=(255, 255, 255), outline=(210, 216, 225), width=3)

    badge_color = {
        "database": (214, 48, 49),
        "payment": (248, 148, 6),
        "auth": (67, 97, 238),
        "infrastructure": (23, 165, 137),
        "notification": (142, 68, 173),
    }.get(case["service"], (59, 130, 246))
    draw.rounded_rectangle((margin, margin, 360, 120), radius=18, fill=badge_color)
    draw.text((120, 88), case["title"].upper(), fill=(255, 255, 255), font=get_font(34), anchor="la")

    draw.text((margin, 180), "INCIDENT MONITORING ALERT", fill=(87, 96, 109), font=get_font(26))

    start_y = 240
    line_gap = 52
    for index, line in enumerate(case["lines"]):
        y = start_y + index * line_gap
        color = (35, 45, 60) if index < 4 else (76, 86, 99)
        draw.text((margin, y), line, fill=color, font=get_font(33))

    status_x = 1220
    status_y = 180
    draw.rounded_rectangle((status_x, status_y, status_x + 420, status_y + 220), radius=18, fill=(239, 246, 255), outline=(152, 190, 255), width=3)
    draw.text((status_x + 30, status_y + 30), "SERVICE", fill=(73, 80, 90), font=get_font(22))
    draw.text((status_x + 30, status_y + 80), case["service"].upper(), fill=(29, 78, 216), font=get_font(38))
    draw.text((status_x + 30, status_y + 140), "SEVERITY: HIGH", fill=(185, 21, 29), font=get_font(24))

    draw.rounded_rectangle((status_x, status_y + 260, status_x + 420, status_y + 430), radius=18, fill=(255, 247, 237), outline=(245, 170, 78), width=3)
    draw.text((status_x + 30, status_y + 290), "RUNBOOK", fill=(120, 87, 31), font=get_font(22))
    draw.text((status_x + 30, status_y + 340), "Mitigate and validate", fill=(130, 100, 44), font=get_font(28))

    out_path = OUTPUT_DIR / case["filename"]
    image.save(out_path)


for case in CASES:
    render_case(case)

manifest = {
    "generated_at": "synthetic-test-data",
    "images": [
        {
            "filename": case["filename"],
            "title": case["title"],
            "service": case["service"],
        }
        for case in CASES
    ],
}
(OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Generated {len(CASES)} sample images in {OUTPUT_DIR}")
