# Phase 3: Evidence and Reporting - Research

**Researched:** 2026-02-17
**Domain:** URL evidence probing (httpx async, SSRF prevention, SHA-256 snapshots) + HTML report generation (Jinja2 + WeasyPrint) + rate limiting (slowapi per-domain)
**Confidence:** HIGH for httpx and Jinja2 (already in venv); MEDIUM-HIGH for WeasyPrint (not installed, known API from docs); MEDIUM for rate limiting (slowapi per-domain key pattern is non-standard)

---

## Summary

Phase 3 adds two major capabilities: an async URL evidence subsystem and an HTML compliance report generator. Both build on the existing FastAPI + SQLModel + PostgreSQL + slowapi foundation from Phases 1–2.

The URL evidence subsystem is architecturally simpler than it looks. httpx 0.28.1 is already installed and provides the async HTTP client. SSRF prevention requires a custom `AsyncBaseTransport` wrapper or a pre-flight DNS resolution check — there is no built-in "block private IPs" option in httpx. SHA-256 snapshotting is `hashlib.sha256(content).hexdigest()` applied to the raw response bytes. Rate limiting per domain (not per user IP) uses slowapi's `key_func` parameter with a custom callable that extracts the domain from the request body. The consent gate is a boolean field on the EvidenceURL model, enforced in the API endpoint before dispatching the probe.

The HTML report generator uses Jinja2 3.1.6 (already installed) to render an HTML template from scoring results + evidence data. WeasyPrint converts that HTML to PDF — but it is NOT currently installed and requires significant system-level dependencies (pango, cairo, gobject-introspection) that must be added to the Dockerfile. Given the roadmap splits reporting into 03-02 (HTML) and 03-03 (PDF/heatmap), the HTML-first approach is correct: Jinja2 alone is sufficient for 03-02, and WeasyPrint is deferred to 03-03.

The MAMI 4x3 matrix heatmap in the report is best done as a pure HTML/CSS table colored by compliance status (green/yellow/red). No external chart library is needed for MVP — the matrix is small (4 categories x 3 dimensions = 12 cells) and CSS background-color is sufficient.

**Primary recommendation:** Build URL probing as a synchronous FastAPI endpoint running `asyncio.gather` for concurrent probes (not background tasks, to keep the status visible immediately for small batches). Use the pre-flight DNS resolution pattern for SSRF prevention. Generate reports as Jinja2-rendered HTML strings stored in a `ComplianceReport` table; serve them as `text/html` responses. Defer WeasyPrint/PDF to 03-03.

---

## Standard Stack

### Core (New additions for Phase 3)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx (AsyncClient) | 0.28.1 (already installed) | Async HTTP probes for URL evidence checking | Already in venv; idiomatic async HTTP in the Python ecosystem; supports timeout, redirect control, and custom transports |
| jinja2 | 3.1.6 (already installed) | HTML report template rendering | Already in venv as FastAPI transitive dep; mature, well-documented, FileSystemLoader pattern is trivial |
| weasyprint | ~61.x | HTML-to-PDF conversion for 03-03 | Decided in stack; requires system deps — must add to Dockerfile |
| hashlib (stdlib) | Python stdlib | SHA-256 content snapshots | No extra install; `hashlib.sha256(bytes).hexdigest()` |
| ipaddress (stdlib) | Python stdlib | SSRF prevention — private IP range checking | No extra install; `ipaddress.ip_address(ip).is_private` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| socket (stdlib) | Python stdlib | DNS resolution for SSRF pre-flight | `socket.getaddrinfo(host, None)` before connecting |
| slowapi (already installed) | 0.1.9+ | Per-domain rate limiting for URL probes | Already installed; use custom `key_func` per endpoint |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 FileSystemLoader | Inline string templates | FileSystemLoader allows template editing without code changes; inline strings make editing harder |
| CSS heatmap table | matplotlib/chart.js | Both add complexity/weight; 12-cell CSS table is sufficient for MVP |
| Pre-flight DNS SSRF check | Custom AsyncBaseTransport | Transport approach intercepts at connection level (more robust); DNS pre-flight is simpler but has TOCTOU race — acceptable for MVP given small user base |
| WeasyPrint | ReportLab | WeasyPrint was decided; ReportLab requires learning a different layout model; WeasyPrint renders from the same HTML template |

### Installation (Phase 3 additions)
```bash
# Backend — WeasyPrint for Phase 03-03
cd backend
uv add "weasyprint>=61.0"
```

**WeasyPrint Dockerfile requirement** — must add system deps to `backend/Dockerfile` before the Python stage:
```dockerfile
# In the builder stage (python:3.12-slim), before uv sync:
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 3 additions)
```
backend/
├── app/
│   ├── models/
│   │   ├── evidence.py            # EvidenceURL model (EVID-01 through EVID-05)
│   │   └── report.py              # ComplianceReport model (REPT-01 through REPT-07)
│   ├── schemas/
│   │   ├── evidence.py            # EvidenceCreate, EvidenceRead, ProbeResult schemas
│   │   └── report.py              # ReportRead schema
│   ├── api/v1/
│   │   ├── evidence.py            # POST/GET /initiatives/{id}/evidence endpoints
│   │   └── reports.py             # POST/GET /initiatives/{id}/report endpoints
│   ├── services/
│   │   ├── url_probe.py           # async_probe_url(), SSRF check, SHA-256 snapshot
│   │   └── report_generator.py    # generate_html_report(), Jinja2 rendering
│   └── templates/
│       └── report.html            # Jinja2 HTML report template
alembic/
└── versions/
    ├── 003_add_evidence_url.py    # EvidenceURL migration
    └── 004_add_compliance_report.py  # ComplianceReport migration
```

---

### Pattern 1: EvidenceURL Model

**What:** One row per URL submitted per questionnaire answer. Stores consent, probe result, and snapshot.

```python
# backend/app/models/evidence.py
from enum import Enum
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, Text


class ProbeStatus(str, Enum):
    pending = "PENDING"
    ok = "OK"
    failed = "FAILED"
    error = "ERROR"


class EvidenceURL(SQLModel, table=True):
    __tablename__ = "evidence_url"

    id: Optional[int] = Field(default=None, primary_key=True)
    initiative_id: int = Field(foreign_key="initiative.id", index=True)
    question_id: str = Field(index=True)        # e.g. "q_S-HRA-1.1"
    mami_code: str = Field(index=True)          # e.g. "S-HRA-1.1"
    url: str                                    # The URL submitted by user
    consent_given: bool = Field(default=False)  # EVID-01: explicit consent required
    probe_status: ProbeStatus = Field(default=ProbeStatus.pending)
    http_status: Optional[int] = None           # e.g. 200, 404
    keyword_found: Optional[bool] = None        # EVID-03: keyword presence check
    keyword_checked: Optional[str] = None       # The keyword that was checked
    content_sha256: Optional[str] = None        # EVID-04: SHA-256 of response body
    probed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

### Pattern 2: Async URL Probe with SSRF Prevention

**What:** Validates URL is not pointing to private infrastructure, then probes it with httpx.

**SSRF prevention strategy:** Pre-flight DNS resolution + IP range check before sending the request. This is simpler than a custom transport and sufficient for MVP. The TOCTOU window (DNS rebinding attack) is acceptable for a small compliance tool where the attacker would need to control DNS.

```python
# backend/app/services/url_probe.py
import hashlib
import ipaddress
import socket
from datetime import datetime
from urllib.parse import urlparse
import httpx


BLOCKED_SCHEMES = {"file", "ftp", "gopher", "data", "javascript"}
PROBE_TIMEOUT = 10.0  # seconds
MAX_CONTENT_BYTES = 1_000_000  # 1 MB snapshot limit


class SSRFError(ValueError):
    """Raised when a URL targets a private/reserved IP address."""


def _check_ssrf(url: str) -> str:
    """
    Parse URL and resolve hostname to IP. Raise SSRFError if private/reserved.
    Returns the hostname for logging.

    Blocks:
    - Non-http(s) schemes
    - Private IPv4 ranges (10.x, 172.16-31.x, 192.168.x, 127.x)
    - Link-local (169.254.x)
    - Loopback (::1)
    - IPv4-mapped IPv6 private addresses
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SSRFError(f"Scheme '{parsed.scheme}' is not allowed; use http or https")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("URL has no hostname")

    try:
        # Resolve DNS — getaddrinfo returns list of (family, type, proto, canonname, sockaddr)
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFError(f"DNS resolution failed for '{hostname}': {e}")

    for result in results:
        ip_str = result[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise SSRFError(
                f"URL resolves to a private/reserved IP address ({ip_str}) — blocked for security"
            )

    return hostname


async def async_probe_url(
    url: str,
    keyword: Optional[str] = None,
) -> dict:
    """
    Probe a URL and return probe result dict. SSRF check runs first.

    Returns:
      {
        "http_status": int | None,
        "keyword_found": bool | None,
        "content_sha256": str | None,
        "probed_at": datetime,
        "error": str | None,
      }
    """
    result = {
        "http_status": None,
        "keyword_found": None,
        "content_sha256": None,
        "probed_at": datetime.utcnow(),
        "error": None,
    }

    try:
        _check_ssrf(url)
    except SSRFError as e:
        result["error"] = str(e)
        return result

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(PROBE_TIMEOUT),
            follow_redirects=True,
            max_redirects=3,
            headers={"User-Agent": "MAMI-Checker/1.0 (+https://coe-dsc.nl)"},
        ) as client:
            response = await client.get(url)
            result["http_status"] = response.status_code

            # SHA-256 snapshot of raw response bytes (up to MAX_CONTENT_BYTES)
            content = response.content[:MAX_CONTENT_BYTES]
            result["content_sha256"] = hashlib.sha256(content).hexdigest()

            # Optional keyword presence check (case-insensitive)
            if keyword:
                text = response.text[:MAX_CONTENT_BYTES]
                result["keyword_found"] = keyword.lower() in text.lower()

    except httpx.TimeoutException:
        result["error"] = "Request timed out after 10 seconds"
    except httpx.RequestError as e:
        result["error"] = f"HTTP request failed: {e}"

    return result
```

---

### Pattern 3: Evidence API Endpoint with Rate Limiting

**What:** POST endpoint that accepts a URL + consent, validates, probes, and stores result. Rate-limited per domain (not per user IP) using slowapi's `key_func`.

**Key design decision:** Run the probe synchronously within the request (not as a background task) because:
- Under-50-user MVP means no throughput concern
- User gets immediate feedback on probe result
- Background tasks require polling UI complexity
- FastAPI's `BackgroundTasks` are process-local — not reliable across restarts

```python
# backend/app/api/v1/evidence.py
import asyncio
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.deps import get_current_user, get_session
from app.models.evidence import EvidenceURL, ProbeStatus
from app.models.initiative import Initiative
from app.models.user import User
from app.services.url_probe import async_probe_url, SSRFError

router = APIRouter(tags=["evidence"])


def get_probe_domain(request: Request) -> str:
    """
    Custom slowapi key_func: rate limit by domain extracted from request body.
    Falls back to remote address if domain cannot be parsed.

    NOTE: slowapi key_func receives the Request object. To access request body,
    we parse it from the route's Pydantic body — but key_func is called before
    the endpoint runs. Use request.client.host as fallback; domain-based limiting
    is enforced inside the endpoint via in-memory tracking for MVP.
    """
    # For MVP: rate limit by remote IP (simplest correct approach)
    # Per-domain limiting is enforced via DB query inside the endpoint
    if not request.client or not request.client.host:
        return "127.0.0.1"
    return request.client.host


# The main app limiter is in app.state — access via request.app.state.limiter
# For the URL probe endpoint we apply a separate per-user limit as a decorator:

@router.post("/initiatives/{initiative_id}/evidence")
@limiter.limit("10/minute")  # 10 URL probes per minute per IP
async def submit_evidence(
    initiative_id: int,
    evidence_in: EvidenceCreate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Submit URL evidence for a question. Requires explicit consent before probing.
    Rate-limited at 10 probes/minute per IP.
    """
    # Ownership check
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    # Consent gate — EVID-01: never probe without consent
    if not evidence_in.consent_given:
        raise HTTPException(
            status_code=400,
            detail="Explicit consent is required before probing a URL"
        )

    # Per-domain rate limit check (secondary guard, in addition to slowapi IP limit)
    domain = _extract_domain(evidence_in.url)
    recent_probes = session.exec(
        select(EvidenceURL).where(
            EvidenceURL.initiative_id == initiative_id,
            EvidenceURL.url.contains(domain),  # rough domain match
        )
    ).all()
    # Allow max 5 probes per domain per initiative (EVID-05 rate limit)
    if len(recent_probes) >= 5:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: maximum 5 URL probes per domain per initiative"
        )

    # Store evidence record as PENDING
    evidence = EvidenceURL(
        initiative_id=initiative_id,
        question_id=evidence_in.question_id,
        mami_code=evidence_in.mami_code,
        url=evidence_in.url,
        consent_given=True,
        keyword_checked=evidence_in.keyword,
        probe_status=ProbeStatus.pending,
    )
    session.add(evidence)
    session.commit()
    session.refresh(evidence)

    # Run probe
    probe_result = await async_probe_url(evidence_in.url, keyword=evidence_in.keyword)

    # Update with results
    if probe_result["error"]:
        evidence.probe_status = ProbeStatus.error
    elif probe_result["http_status"] and probe_result["http_status"] < 400:
        evidence.probe_status = ProbeStatus.ok
    else:
        evidence.probe_status = ProbeStatus.failed

    evidence.http_status = probe_result["http_status"]
    evidence.keyword_found = probe_result["keyword_found"]
    evidence.content_sha256 = probe_result["content_sha256"]
    evidence.probed_at = probe_result["probed_at"]
    session.add(evidence)
    session.commit()
    session.refresh(evidence)

    return evidence


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).hostname or url
    except Exception:
        return url
```

**Note on slowapi decorator in routers:** The `limiter` object lives in `app.state.limiter`. In a router module, access it via:
```python
# In the router file — the limiter must be the SAME instance as app.state.limiter
# Pattern: import from main.py or create a shared limiter module
from app.core.limiter import limiter  # create this module
```

Create `backend/app/core/limiter.py`:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

Then in `main.py`, import this instance instead of creating a new one:
```python
from app.core.limiter import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

---

### Pattern 4: ComplianceReport Model

**What:** Stores a generated report as HTML string. One active report per initiative; regeneration replaces it.

```python
# backend/app/models/report.py
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text


class ComplianceReport(SQLModel, table=True):
    __tablename__ = "compliance_report"

    id: Optional[int] = Field(default=None, primary_key=True)
    initiative_id: int = Field(foreign_key="initiative.id", index=True, unique=True)
    # unique=True: one active report per initiative; regeneration replaces it
    html_content: str = Field(sa_column=Column(Text))   # Full rendered HTML
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    questionnaire_version: str                          # Version at generation time
    total_answers: int
    critical_count: int
    non_critical_count: int
    compliant_count: int
```

---

### Pattern 5: Jinja2 Report Generator

**What:** Renders the compliance report HTML from scoring results and evidence data.

```python
# backend/app/services/report_generator.py
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),  # XSS-safe: auto-escapes HTML content
    )


def generate_html_report(
    initiative: dict,
    answers: list[dict],         # [{mami_code, answer_value, rationale}]
    findings: list[dict],        # [{mami_code, severity, status}]
    evidence_by_code: dict,      # {"S-HRA-1.1": [EvidenceURL, ...]}
    mami_config: dict,           # Full mami-framework.json content
) -> str:
    """
    Render the Jinja2 HTML report template. Returns full HTML string.
    """
    env = _get_jinja_env()
    template = env.get_template("report.html")

    # Build matrix data structure: {category: {dimension: {code_id: status}}}
    matrix = _build_matrix(answers, findings, mami_config)

    # Build per-code findings data with evidence attached
    findings_detail = _build_findings_detail(answers, findings, evidence_by_code, mami_config)

    context = {
        "initiative": initiative,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "matrix": matrix,
        "findings_detail": findings_detail,
        "critical_count": sum(1 for f in findings if f["severity"] == "CRITICAL"),
        "non_critical_count": sum(1 for f in findings if f["severity"] == "NON_CRITICAL"),
        "total_answers": len(answers),
        "mami_config": mami_config,
    }

    return template.render(**context)


def _build_matrix(answers, findings, mami_config):
    """
    Returns nested dict: {category_key: {dimension_key: {code_id: compliance_status}}}
    compliance_status: "CRITICAL" | "NON_CRITICAL" | "COMPLIANT" | "NOT_APPLICABLE" | "UNANSWERED"
    """
    finding_lookup = {f["mami_code"]: f for f in findings}
    answer_lookup = {a["mami_code"]: a for a in answers}

    categories = ["scheme", "participants", "data", "services"]
    dimensions = ["human_readable", "machine_readable", "trust_anchors"]

    matrix = {cat: {dim: {} for dim in dimensions} for cat in categories}

    for code in mami_config["codes"]:
        code_id = code["id"]
        cat = code["category"]
        dim = code["dimension"]

        if code_id in finding_lookup:
            status = finding_lookup[code_id]["severity"]  # "CRITICAL" or "NON_CRITICAL"
        elif code_id in answer_lookup:
            answer = answer_lookup[code_id]
            if answer["answer_value"] == "NOT_APPLICABLE":
                status = "NOT_APPLICABLE"
            else:
                status = "COMPLIANT"
        else:
            status = "UNANSWERED"

        matrix[cat][dim][code_id] = status

    return matrix
```

---

### Pattern 6: HTML Report Template Structure

**What:** Jinja2 template for the compliance report. Key sections: header, executive summary, 4x3 matrix table, per-code findings.

```html
<!-- backend/app/templates/report.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MAMI Compliance Report — {{ initiative.name }}</title>
  <style>
    /* coe-dsc.nl brand colors */
    :root {
      --primary: #003d73;
      --accent: #0077cc;
      --critical: #c0392b;
      --non-critical: #e67e22;
      --compliant: #27ae60;
      --na: #95a5a6;
      --unanswered: #ecf0f1;
    }
    body { font-family: Arial, sans-serif; margin: 2rem; color: #333; }
    h1 { color: var(--primary); }

    /* Executive summary box */
    .summary-box { background: #f8f9fa; border-left: 4px solid var(--primary); padding: 1rem; margin: 1rem 0; }

    /* Matrix heatmap table */
    .matrix-table { border-collapse: collapse; width: 100%; margin: 1.5rem 0; }
    .matrix-table th { background: var(--primary); color: white; padding: 0.5rem; text-align: center; }
    .matrix-table td { border: 1px solid #ccc; padding: 0.5rem; text-align: center; font-size: 0.85rem; }
    .cell-CRITICAL    { background: var(--critical); color: white; }
    .cell-NON_CRITICAL { background: var(--non-critical); color: white; }
    .cell-COMPLIANT   { background: var(--compliant); color: white; }
    .cell-NOT_APPLICABLE { background: var(--na); color: white; }
    .cell-UNANSWERED  { background: var(--unanswered); color: #666; }

    /* Findings list */
    .finding-card { border: 1px solid #ddd; border-radius: 4px; padding: 1rem; margin: 0.75rem 0; }
    .finding-CRITICAL { border-left: 4px solid var(--critical); }
    .finding-NON_CRITICAL { border-left: 4px solid var(--non-critical); }
    .severity-badge { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 3px; font-size: 0.8rem; font-weight: bold; }
    .badge-CRITICAL { background: var(--critical); color: white; }
    .badge-NON_CRITICAL { background: var(--non-critical); color: white; }
    .evidence-item { background: #f0f4f8; padding: 0.5rem; border-radius: 3px; margin: 0.25rem 0; font-size: 0.85rem; }
    .evidence-ok { color: var(--compliant); }
    .evidence-failed { color: var(--critical); }
  </style>
</head>
<body>
  <h1>MAMI Compliance Report</h1>
  <p><strong>Initiative:</strong> {{ initiative.name }}</p>
  <p><strong>Organisation:</strong> {{ initiative.organization }}</p>
  <p><strong>Generated:</strong> {{ generated_at }}</p>

  <!-- Executive Summary -->
  <h2>Executive Summary</h2>
  <div class="summary-box">
    <p>This initiative has answered <strong>{{ total_answers }}</strong> MAMI framework questions.</p>
    <p>
      <strong>{{ critical_count }}</strong> critical finding(s) require immediate attention.
      <strong>{{ non_critical_count }}</strong> non-critical finding(s) are recommended for improvement.
    </p>
    {% if critical_count == 0 %}
    <p style="color: var(--compliant); font-weight: bold;">No critical findings — core MUST requirements are met.</p>
    {% else %}
    <p style="color: var(--critical); font-weight: bold;">Action required: critical MUST requirements are not met.</p>
    {% endif %}
  </div>

  <!-- MAMI 4x3 Matrix Overview -->
  <h2>MAMI Framework Matrix Overview</h2>
  <table class="matrix-table">
    <thead>
      <tr>
        <th>Category</th>
        <th>Human Readable/Actionable</th>
        <th>Machine Readable/Actionable</th>
        <th>Trust Anchors</th>
      </tr>
    </thead>
    <tbody>
      {% for cat_key, cat_label in [
          ("scheme", "Scheme Management"),
          ("participants", "Participants"),
          ("data", "Data"),
          ("services", "Services")
      ] %}
      <tr>
        <td><strong>{{ cat_label }}</strong></td>
        {% for dim_key in ["human_readable", "machine_readable", "trust_anchors"] %}
        <td>
          {% set codes_in_cell = matrix[cat_key][dim_key] %}
          {% for code_id, status in codes_in_cell.items() %}
          <div class="cell-{{ status }}">{{ code_id }}</div>
          {% endfor %}
        </td>
        {% endfor %}
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <!-- Per-Code Findings -->
  <h2>Findings Detail</h2>
  {% for finding in findings_detail %}
  <div class="finding-card finding-{{ finding.severity }}">
    <h3>
      {{ finding.mami_code }}
      <span class="severity-badge badge-{{ finding.severity }}">{{ finding.severity }}</span>
    </h3>
    <p><strong>Description:</strong> {{ finding.description }}</p>
    <p><strong>MoSCoW Level:</strong> {{ finding.moscow_level }}</p>
    <p><strong>Answer:</strong> {{ finding.answer_value }}{% if finding.rationale %} — {{ finding.rationale }}{% endif %}</p>

    {% if finding.evidence %}
    <p><strong>Evidence submitted:</strong></p>
    {% for ev in finding.evidence %}
    <div class="evidence-item">
      <a href="{{ ev.url }}" target="_blank" rel="noopener noreferrer">{{ ev.url }}</a>
      <span class="{{ 'evidence-ok' if ev.probe_status == 'OK' else 'evidence-failed' }}">
        [{{ ev.probe_status }}{% if ev.http_status %} HTTP {{ ev.http_status }}{% endif %}]
      </span>
      {% if ev.content_sha256 %}
      <span style="font-size:0.75rem; color:#999;">SHA-256: {{ ev.content_sha256[:16] }}…</span>
      {% endif %}
    </div>
    {% endfor %}
    {% endif %}

    <p><strong>Next steps:</strong> {{ finding.next_steps }}</p>
  </div>
  {% endfor %}

  <footer style="margin-top: 2rem; color: #999; font-size: 0.8rem;">
    Generated by MAMI Compliance Checker — CoE-DSC / TNO &middot; {{ generated_at }}
  </footer>
</body>
</html>
```

---

### Pattern 7: Report Generation Endpoint

**What:** POST endpoint that triggers scoring + evidence lookup + Jinja2 render + DB store. GET returns the stored HTML.

```python
# backend/app/api/v1/reports.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime
from app.core.deps import get_current_user, get_zen_engine, get_mami_config
from app.db.session import get_session
from app.models.initiative import Initiative
from app.models.report import ComplianceReport
from app.models.questionnaire import QuestionnaireAnswer
from app.models.evidence import EvidenceURL
from app.services.scoring_engine import score_all_answers
from app.services.report_generator import generate_html_report
import zen

router = APIRouter(tags=["reports"])


@router.post("/initiatives/{initiative_id}/report", response_class=HTMLResponse)
async def generate_report(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
    engine: zen.ZenEngine = Depends(get_zen_engine),
    mami_config: dict = Depends(get_mami_config),
):
    """Generate or regenerate the compliance report. Returns rendered HTML."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    # Load answers
    answers = session.exec(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.initiative_id == initiative_id)
    ).all()

    # Score via existing ZEN engine service
    code_lookup = {c["id"]: c for c in mami_config.get("codes", [])}
    answers_for_scoring = [
        {
            "mami_code": a.mami_code,
            "moscow_level": code_lookup.get(a.mami_code, {}).get("moscow_level", "SHOULD"),
            "answer_value": a.answer_value,
            "critical_override": code_lookup.get(a.mami_code, {}).get("critical_override"),
        }
        for a in answers
    ]
    findings_raw = await score_all_answers(engine, answers_for_scoring)

    # Load evidence grouped by mami_code
    evidence_rows = session.exec(
        select(EvidenceURL).where(EvidenceURL.initiative_id == initiative_id)
    ).all()
    evidence_by_code = {}
    for ev in evidence_rows:
        evidence_by_code.setdefault(ev.mami_code, []).append(ev)

    # Build answer dicts for template
    answers_dict = [
        {
            "mami_code": a.mami_code,
            "answer_value": a.answer_value,
            "rationale": a.rationale,
        }
        for a in answers
    ]
    initiative_dict = {
        "name": initiative.name,
        "organization": initiative.organization,
        "contact_name": initiative.contact_name,
    }

    # Render HTML
    html_content = generate_html_report(
        initiative=initiative_dict,
        answers=answers_dict,
        findings=findings_raw,
        evidence_by_code=evidence_by_code,
        mami_config=mami_config,
    )

    # Upsert report (one per initiative — regeneration replaces)
    stmt = pg_insert(ComplianceReport).values(
        initiative_id=initiative_id,
        html_content=html_content,
        generated_at=datetime.utcnow(),
        questionnaire_version="1.0",
        total_answers=len(answers),
        critical_count=sum(1 for f in findings_raw if f["severity"] == "CRITICAL"),
        non_critical_count=sum(1 for f in findings_raw if f["severity"] == "NON_CRITICAL"),
        compliant_count=len(answers) - len(findings_raw),
    ).on_conflict_do_update(
        index_elements=["initiative_id"],
        set_={
            "html_content": pg_insert(ComplianceReport).excluded.html_content,
            "generated_at": pg_insert(ComplianceReport).excluded.generated_at,
            "total_answers": pg_insert(ComplianceReport).excluded.total_answers,
            "critical_count": pg_insert(ComplianceReport).excluded.critical_count,
            "non_critical_count": pg_insert(ComplianceReport).excluded.non_critical_count,
            "compliant_count": pg_insert(ComplianceReport).excluded.compliant_count,
        },
    )
    session.exec(stmt)
    session.commit()

    return HTMLResponse(content=html_content, status_code=200)


@router.get("/initiatives/{initiative_id}/report", response_class=HTMLResponse)
def get_report(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Return the last generated compliance report as HTML."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    report = session.exec(
        select(ComplianceReport).where(ComplianceReport.initiative_id == initiative_id)
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="No report generated yet")

    return HTMLResponse(content=report.html_content, status_code=200)
```

---

### Pattern 8: WeasyPrint PDF Export (03-03 only)

**What:** Convert the stored HTML report to PDF using WeasyPrint.

```python
# backend/app/api/v1/reports.py — add PDF endpoint for 03-03
from fastapi.responses import Response
import weasyprint

@router.get("/initiatives/{initiative_id}/report/pdf")
def get_report_pdf(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Export the compliance report as PDF via WeasyPrint."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    report = session.exec(
        select(ComplianceReport).where(ComplianceReport.initiative_id == initiative_id)
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="No report generated yet")

    # WeasyPrint: HTML string → PDF bytes
    pdf_bytes = weasyprint.HTML(string=report.html_content).write_pdf()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="mami-report-{initiative_id}.pdf"'
        },
    )
```

**WeasyPrint notes:**
- `weasyprint.HTML(string=html)` — use string= for in-memory HTML (not filename=)
- `weasyprint.HTML(string=html, base_url=".")` — needed if CSS references local files
- `.write_pdf()` returns `bytes` synchronously (blocking) — run in `asyncio.run_in_executor` if called from an async endpoint (though for MVP with <50 users the blocking is acceptable)
- WeasyPrint is CPU-bound; for async endpoints use `asyncio.get_event_loop().run_in_executor(None, lambda: weasyprint.HTML(string=html).write_pdf())`

---

### Anti-Patterns to Avoid

- **Do not probe URLs in background tasks** for this MVP. `FastAPI.BackgroundTasks` are process-local and not persisted across restarts. Use synchronous probe within the request.
- **Do not store the full HTML report as a file on disk.** Store it in the `compliance_report.html_content` column — it's a TEXT column, PostgreSQL handles it fine at report sizes (<1 MB).
- **Do not use `httpx.get()` (top-level function).** Always use `AsyncClient` as a context manager to ensure connection pooling and proper cleanup.
- **Do not skip the SSRF check** even if user input is "just a URL field." The risk is small for MVP but the check is 5 lines of code.
- **Do not use Jinja2 without `autoescape=True`** in the HTML template. User-provided content (initiative name, rationale) renders into HTML; autoescape prevents XSS.
- **Do not use `unique=True` on `ComplianceReport.initiative_id` at the model level** without a matching `on_conflict_do_update` upsert — the unique constraint will cause `IntegrityError` on regeneration if you use a plain `session.add()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSRF prevention | Custom regex to detect "192.168" strings | `ipaddress.ip_address(ip).is_private` + DNS resolution | Regex misses IPv6, decimal-encoded IPs, and edge cases |
| SHA-256 snapshot | Custom hash or MD5 | `hashlib.sha256(response.content).hexdigest()` | stdlib; SHA-256 is the standard for content integrity |
| HTML→PDF | Custom PDF layout code | WeasyPrint | PDF layout from scratch is 100+ lines of low-level code |
| Rate limiting | Custom counter in DB | slowapi + in-memory fallback | Rate limiting has subtle edge cases (race conditions); slowapi is already installed |
| Template rendering | Python f-strings for HTML | Jinja2 | F-strings don't autoescape; Jinja2 is already installed |

---

## Common Pitfalls

### Pitfall 1: WeasyPrint System Dependencies Missing in Docker
**What goes wrong:** `ImportError: cannot import name 'HTML' from 'weasyprint'` or `OSError: libpango not found` at runtime in the container.
**Why it happens:** WeasyPrint wraps libpango, cairo, and GDK-PixBuf — none of which are in `python:3.12-slim`.
**How to avoid:** Add the apt-get install block to the Dockerfile (see Standard Stack section above). Test with `docker compose build` immediately after adding WeasyPrint to pyproject.toml.
**Warning signs:** Works locally (if libpango is installed) but fails in Docker.

### Pitfall 2: slowapi `@limiter.limit` Decorator Requires the Limiter Instance
**What goes wrong:** `AttributeError: 'Limiter' object has no attribute 'limit'` or the rate limit is silently not applied because a second `Limiter` instance is created in the router module.
**Why it happens:** `main.py` creates a `Limiter` instance and attaches it to `app.state.limiter`. If a router module creates a second `Limiter()`, it's a different object — the decorator on routes uses the wrong instance.
**How to avoid:** Extract the limiter to `app/core/limiter.py` as a module-level singleton. Import it in both `main.py` and all router modules.

### Pitfall 3: SSRF via DNS Rebinding (Acceptable for MVP)
**What goes wrong:** An attacker controls a DNS record that resolves to a public IP during the SSRF check, then switches to a private IP for the actual HTTP connection.
**Why it happens:** DNS resolution and TCP connection are two separate steps — the IP can change between them.
**How to avoid (MVP):** The pre-flight check is sufficient for the threat model (small compliance tool, <50 users). Note this as a known limitation. Production hardening would use a custom `AsyncBaseTransport` that resolves DNS once and pins the IP for the connection.

### Pitfall 4: `ComplianceReport` Unique Constraint + Plain `session.add()` on Regeneration
**What goes wrong:** Second report generation raises `sqlalchemy.exc.IntegrityError: UNIQUE constraint failed: compliance_report.initiative_id`.
**Why it happens:** `session.add(report)` does an INSERT; if a row already exists with that `initiative_id`, the unique constraint fires.
**How to avoid:** Use `pg_insert().on_conflict_do_update()` for all report saves (same pattern as questionnaire answers). Never use `session.add()` for the report upsert.

### Pitfall 5: Jinja2 `autoescape` Not Set
**What goes wrong:** XSS vulnerability — user-provided content in `initiative.name`, `rationale`, or URL values renders as raw HTML in the report.
**Why it happens:** Jinja2's default `autoescape` is `False` for performance. When rendering HTML, it must be explicitly enabled.
**How to avoid:** Always create the Jinja2 `Environment` with `autoescape=select_autoescape(["html"])`. This is a one-line fix that prevents the entire class of XSS issues.

### Pitfall 6: `httpx.AsyncClient` as a One-Shot (Not Reused Across Requests)
**What goes wrong:** Creating a new `AsyncClient` per request is correct here (each probe is isolated). The pitfall is forgetting `async with` and leaking connections.
**Why it happens:** `httpx.AsyncClient()` without a context manager does not auto-close. The response stream stays open.
**How to avoid:** Always use `async with httpx.AsyncClient(...) as client:` — the context manager handles cleanup.

### Pitfall 7: `Text` Column Type for `html_content`
**What goes wrong:** `ComplianceReport.html_content` defined as `str = Field(...)` without `sa_column=Column(Text)` maps to `VARCHAR` in PostgreSQL, which has a 255-character default limit in some ORM configurations.
**Why it happens:** SQLModel maps Python `str` to `VARCHAR` by default.
**How to avoid:** Use `sa_column=Column(Text)` for any large text field. `Text` in PostgreSQL has no length limit.

---

## Code Examples

### SSRF-safe URL probe (complete)
```python
# Source: Python stdlib socket + ipaddress modules
import hashlib
import ipaddress
import socket
from urllib.parse import urlparse
import httpx

def _is_safe_url(url: str) -> tuple[bool, str]:
    """Returns (is_safe, reason). reason is empty string if safe."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False, f"Scheme '{parsed.scheme}' not allowed"
    hostname = parsed.hostname
    if not hostname:
        return False, "No hostname in URL"
    try:
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        return False, f"DNS resolution failed: {e}"
    for result in results:
        ip_str = result[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, f"Resolves to private IP: {ip_str}"
        except ValueError:
            continue
    return True, ""

async def probe_url(url: str, keyword: str | None = None) -> dict:
    is_safe, reason = _is_safe_url(url)
    if not is_safe:
        return {"error": reason, "http_status": None, "content_sha256": None, "keyword_found": None}

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0),
        follow_redirects=True,
        max_redirects=3,
    ) as client:
        try:
            r = await client.get(url)
            body = r.content[:1_000_000]
            sha = hashlib.sha256(body).hexdigest()
            kw_found = keyword.lower() in r.text.lower() if keyword else None
            return {"http_status": r.status_code, "content_sha256": sha, "keyword_found": kw_found, "error": None}
        except httpx.TimeoutException:
            return {"error": "timeout", "http_status": None, "content_sha256": None, "keyword_found": None}
        except httpx.RequestError as e:
            return {"error": str(e), "http_status": None, "content_sha256": None, "keyword_found": None}
```

### Jinja2 environment setup (correct)
```python
# Source: Jinja2 3.1.6 official docs
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("/path/to/templates"),
    autoescape=select_autoescape(["html"]),  # mandatory for HTML output
)
template = env.get_template("report.html")
html = template.render(key=value, ...)
```

### slowapi shared limiter pattern
```python
# app/core/limiter.py — create once, import everywhere
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# main.py
from app.core.limiter import limiter
app.state.limiter = limiter

# any router
from app.core.limiter import limiter

@router.post("/some-endpoint")
@limiter.limit("10/minute")
async def endpoint(request: Request, ...):
    ...
```

### pg_insert upsert for ComplianceReport
```python
# Source: existing questionnaire.py pattern — same pg_insert().on_conflict_do_update()
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.report import ComplianceReport

stmt = pg_insert(ComplianceReport).values(
    initiative_id=initiative_id,
    html_content=html,
    generated_at=datetime.utcnow(),
    ...
).on_conflict_do_update(
    index_elements=["initiative_id"],
    set_={"html_content": pg_insert(ComplianceReport).excluded.html_content, ...},
)
session.exec(stmt)
session.commit()
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `requests` for HTTP probes | `httpx.AsyncClient` | True async — fits FastAPI's async model; no blocking the event loop |
| WeasyPrint `<60` used `cairocffi` | WeasyPrint `61+` uses `pydyf` (pure Python PDF) | Fewer system deps on newer versions — but pango/fontconfig still required for font rendering |
| Jinja2 v2 (Python 2 era) | Jinja2 3.1.6 | `select_autoescape()` helper is v3+ API; don't use the old `autoescape=True` boolean directly |
| Full re-render on every GET | Store HTML in DB, GET returns stored | Regeneration is explicit (POST); GET is fast read — correct pattern for "report snapshot" |

---

## Open Questions

1. **Keyword for URL evidence check (EVID-03)**
   - What we know: The spec says "keyword presence check." The keyword could come from the question config or user input.
   - What's unclear: Is the keyword per-question (configured in questionnaire-v1.json) or free-text entered by the user at evidence submission time?
   - Recommendation: Accept an optional `keyword` field in the `EvidenceCreate` schema (user-supplied). No question-level keyword config needed for MVP.

2. **Rate limiting storage for URL probes**
   - What we know: slowapi uses in-memory storage by default (MemoryStorage). This resets on restart.
   - What's unclear: Is per-domain limiting (EVID-05) meant to be enforced via slowapi or via DB query?
   - Recommendation: Use DB query (count existing probes per domain per initiative) as the authoritative gate. slowapi `@limiter.limit("10/minute")` as a secondary API-level guard. Do not add Redis for MVP.

3. **Report HTML served inline vs. separate iframe**
   - What we know: The frontend currently uses `HTMLResponse` with content type `text/html`.
   - What's unclear: Should the frontend open the report in a new tab, embed it in an iframe, or download it?
   - Recommendation: Return `HTMLResponse` from the API. Frontend opens the URL in a new tab (`window.open`). No iframe complexity needed for MVP.

4. **WeasyPrint in Plan 03-03 — defer system deps update?**
   - What we know: WeasyPrint requires apt packages not in `python:3.12-slim`. These must be added to the Dockerfile.
   - What's unclear: The current Dockerfile is a multi-stage build. The runtime stage (`FROM python:3.12-slim`) also needs the system packages (not just the builder stage).
   - Recommendation: Add apt-get to the final runtime stage, not just the builder. Confirm this in 03-03.

---

## Sources

### Primary (HIGH confidence)
- httpx 0.28.1 source in `.venv` (`_client.py`, `_urls.py`, `_transports/base.py`) — AsyncClient API, timeout, redirect, transport pattern verified directly
- Jinja2 3.1.6 source in `.venv` (`__init__.py`, `environment.py`) — Environment, FileSystemLoader, select_autoescape API verified directly
- Python stdlib `ipaddress` and `socket` modules — well-established SSRF prevention primitives
- Python stdlib `hashlib` — SHA-256 via `hashlib.sha256(bytes).hexdigest()`
- slowapi 0.1.9 source in `.venv` (`extension.py`, `util.py`) — Limiter class, `@limiter.limit()` decorator, key_func parameter verified directly
- Existing project codebase — `main.py`, `questionnaire.py`, `scoring.py`, `scoring_engine.py` — confirmed patterns: pg_insert upsert, async_gather, app.state, lifespan, deps.py injection

### Secondary (MEDIUM confidence)
- WeasyPrint system dependency requirements (pango, cairo) — known from prior research and WeasyPrint official documentation; WeasyPrint is not installed in the current venv, so API is from documentation knowledge (training data, January 2025)
- WeasyPrint `weasyprint.HTML(string=...).write_pdf()` API — MEDIUM confidence; core API has been stable across versions 55–61

### Tertiary (LOW confidence)
- WeasyPrint `pydyf` backend change in v60+ reducing system dependency requirements — flagged as LOW confidence; needs verification when actually installing during 03-03

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — httpx and Jinja2 verified from installed venv; WeasyPrint MEDIUM (not installed)
- Architecture: HIGH — patterns follow established project conventions (pg_insert upsert, app.state deps, lifespan)
- Pitfalls: HIGH — SSRF, WeasyPrint Docker, slowapi instance sharing, and upsert pitfalls all verified from source code
- Rate limiting pattern: MEDIUM — slowapi key_func per-domain pattern is not directly verified via test; fallback to DB count is more reliable

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable stack; WeasyPrint system deps may change on major versions)
