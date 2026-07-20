# MAMI Compliance Checker

A web-based compliance assessment tool that lets Data Sharing Initiatives (DSIs) and Service Providers (SPs) evaluate their initiative against the MAMI (Minimal Agreements for Maximal Interoperability) framework. Users complete a 27-question questionnaire and receive a live interoperability heatmap and a mailed PDF report with recommendations.

Built for the **TNO Centre of Expertise for Data Sharing and Cloud (CoE-DSC)**.

---

## Features

- User registration with JWT authentication (DSI and SP participant types)
- Config-driven 27-question MAMI questionnaire (v3.0) per participant type
- Yes / Not there yet / Not applicable answer format with multi-select follow-ups
- GoRules ZEN Engine scoring → CRITICAL / NON_CRITICAL findings
- Live interoperability heatmap (4 categories × 3 dimensions)
- PDF report delivered by email (WeasyPrint + Resend)
- Admin panel: user management, initiative management, CSV export, aggregated heatmap, demo reset
- Self-service password reset via email
- Mobile-responsive UI

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLModel, Alembic |
| Database | PostgreSQL 16 |
| Scoring | GoRules ZEN Engine |
| PDF / Email | WeasyPrint, Resend SDK |
| Frontend | React 19, TypeScript, Vite, Ant Design v6, TanStack Router |
| Infrastructure | Docker, Docker Compose, Nginx |

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) — How to deploy on your own server
- [OPERATIONS.md](OPERATIONS.md) — Backups, updates, and day-to-day administration

## MAMI Framework

The MAMI framework is a 4×3 matrix of interoperability requirements:

- **4 categories**: Scheme management, Participants management, Data management, Services management
- **3 dimensions**: Human readable/actionable, Machine readable/actionable, Trust Anchors
- **27 recommendation codes** (e.g. HRA-1.1, MRA-2.3, TA-4.2)

## API Documentation

When the application is running, the auto-generated OpenAPI documentation is available at:

- `https://your-domain/docs` — Swagger UI
- `https://your-domain/redoc` — ReDoc

## Configuration

The questionnaire questions, scoring rules, and MAMI framework structure are all config-driven JSON files in the `config/` directory. Question or scoring changes require no code deployment — edit the JSON and restart the backend service.

| File | Purpose |
|---|---|
| `config/dsi-questionnaire-v2.json` | DSI questionnaire (27 questions) |
| `config/sp-questionnaire-v2.json` | SP questionnaire (27 questions) |
| `config/mami-framework.json` | MAMI structure definition |
| `config/scoring/mami-scoring.json` | GoRules ZEN scoring rules |
