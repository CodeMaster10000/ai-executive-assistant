# AI Executive Assistant Network

A multi-agent career intelligence system with a web GUI. Acts as a "digital board of advisors" running scouts, planners, a verifier, and an auditor — all governed by explicit policy-as-code.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | LangGraph (StateGraph) for agent pipelines, LangChain for LLM abstractions |
| **Backend** | FastAPI + Pydantic v2 (API schemas, DB models, validation) |
| **Inter-agent DTOs** | `TypedDict` for LangGraph state (idiomatic); Pydantic for API boundaries and persistence |
| **Frontend** | HTMX + HTML/CSS (single-service, served by FastAPI) |
| **Storage** | PostgreSQL (entities) + append-only JSONL (audit logs) |
| **Real-time** | SSE (Server-Sent Events) for run progress streaming |
| **Policies** | YAML files in `/policy/`, read-only in GUI, versioned via git |
| **Testing** | pytest |
| **Phase 1 agents** | Mock/stub implementations (no real LLM calls), swappable for real LLMs later |

---

## Engineering Pillars

1. **Policy-as-code** — explicit, versioned, testable YAML policies enforced by the policy engine (not convention)
2. **Evidence-first** — every claim referencing external info must have `EvidenceItem` (URL + SHA-256 hash + snippet); missing evidence fails verification or forces "Unknown"
3. **Deterministic verification** — non-LLM verifier validates JSON schema, evidence coverage, confidence thresholds, policy compliance, dedup, output bounds
4. **Immutable audit** — every run produces an append-only JSONL trail + run bundle under `artifacts/runs/<run_id>/`
5. **Safe degradation** — partial results with explicit "Unknown" sections; no silent failures, no invented data

---

## Profiles as Workspaces

Each **profile** (e.g., "Architect", "Developer", "Designer") is an independent workspace with its own:
- Target roles, constraints, skills, CV
- Runs, opportunities, cover letters, and run history

The GUI provides a profile switcher on the dashboard. All run-related data is scoped to a profile.

---

## LangGraph Pipeline Architecture

Three `StateGraph` definitions: **daily**, **weekly**, **cover_letter**.

```
StateGraph (per pipeline mode)
  Nodes = agents (retriever, extractor, coordinator, ceo, cfo, cover_letter, verifier, audit_writer)
  Edges = conditional routing based on policy engine
  State = TypedDict shared across nodes in a single graph execution
```

### Daily Intel Graph
```
job_scout_retriever -> job_scout_extractor ─┐
cert_scout_retriever -> cert_scout_extractor ──> coordinator -> verifier -> audit_writer
trends_scout_retriever -> trends_scout_extractor ┘
```

### Weekly Brief Graph
```
job_scout_retriever -> job_scout_extractor ─┐
cert_scout_retriever -> cert_scout_extractor ──> coordinator -> ceo_agent ─┐
trends_scout_retriever -> trends_scout_extractor ┘    cfo_agent ─┴─> coordinator_merge -> verifier -> audit_writer
```

### Cover Letter Graph
```
[CV + JD + extracted reqs] -> cover_letter_agent -> verifier -> audit_writer
```

### Policy Engine Integration
- **Middleware/interceptor on node transitions** — enforces tool boundaries, step budgets, data boundaries
- **LangGraph callbacks** feed SSE stream for real-time progress to the GUI

### Tooling Boundaries (enforced by policy engine)
- **Retriever agents**: network tools allowed
- **Planner agents** (CEO/CFO/Coordinator): no retrieval; structured inputs only
- **Cover letter agent**: reads CV + selected JD + extracted requirements only

---

## HTTP API

All endpoints use the `/api` prefix. Profile-scoped resources are nested under `/api/profiles/{profile_id}`.

### Workspace / Profile Management

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/profiles` | Create a new profile/workspace |
| `GET` | `/api/profiles` | List all profiles |
| `GET` | `/api/profiles/{profile_id}` | Get profile details |
| `PUT` | `/api/profiles/{profile_id}` | Update profile |
| `DELETE` | `/api/profiles/{profile_id}` | Delete profile and its data |
| `POST` | `/api/profiles/{profile_id}/cv` | Upload CV file |

### Run Lifecycle

A **run** is a single execution of a pipeline (daily intel, weekly brief, or cover letter). It has a unique ID, tracks which agents executed, stores all inputs/outputs/evidence, and produces a verifier report + audit trail.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/profiles/{profile_id}/runs` | Start a run (`{ mode: "daily"\|"weekly"\|"cover_letter", options }`) |
| `GET` | `/api/profiles/{profile_id}/runs` | List runs (filterable by mode, status, date range) |
| `GET` | `/api/profiles/{profile_id}/runs/{run_id}` | Run details + status + outputs |
| `GET` | `/api/profiles/{profile_id}/runs/{run_id}/stream` | SSE stream of live agent progress events |
| `POST` | `/api/profiles/{profile_id}/runs/{run_id}/cancel` | Cancel an in-progress run |

### Audit & Replay

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/profiles/{profile_id}/runs/{run_id}/audit` | Full audit trail (agent timeline, tool calls, hashes) |
| `GET` | `/api/profiles/{profile_id}/runs/{run_id}/verifier-report` | Verifier pass/fail/partial report |
| `POST` | `/api/profiles/{profile_id}/runs/{run_id}/replay` | Replay run (`{ mode: "strict"\|"refresh" }`) |
| `GET` | `/api/profiles/{profile_id}/runs/{run_id}/diff/{other_run_id}` | Diff between two runs |

### Opportunities

Aggregated from completed runs.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/profiles/{profile_id}/opportunities` | Browse discovered opportunities (jobs, certs, trends) |
| `GET` | `/api/profiles/{profile_id}/opportunities/{opportunity_id}` | Single opportunity with evidence items |

### Cover Letters

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/profiles/{profile_id}/cover-letters` | Generate cover letter (`{ opportunity_id }` or `{ jd_text }`) |
| `GET` | `/api/profiles/{profile_id}/cover-letters` | List generated cover letters |
| `GET` | `/api/profiles/{profile_id}/cover-letters/{letter_id}` | Single cover letter with evidence refs |

### Policies (file-based, read-only in GUI)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/policies` | List all active policies (reads from `/policy/*.yaml`) |
| `GET` | `/api/policies/{policy_name}` | Single policy details |

---

## GUI Pages (HTMX, served by FastAPI)

| Path | Description |
|---|---|
| `GET /` | Dashboard (profile switcher + recent activity) |
| `GET /profiles/{profile_id}` | Profile editor |
| `GET /profiles/{profile_id}/runs` | Runs list |
| `GET /profiles/{profile_id}/runs/{run_id}` | Run detail view (outputs, audit, verifier) |
| `GET /profiles/{profile_id}/opportunities` | Opportunities browser |
| `GET /profiles/{profile_id}/cover-letters` | Cover letters list |
| `GET /policies` | Policy viewer (read-only) |

---

## Data Model

### Core Entities

- **`UserProfile`** — targets, constraints, skills, CV; one per workspace
- **`SourceConfig`** — allowlisted sources + query templates per scout
- **`Run`** — immutable execution record with mode, status, timestamps
- **`Artifact`** — briefs, opportunities, cover letters produced by runs
- **`EvidenceItem`** — id, type (page/snippet/rss/api), url, retrieved_at, content_hash (sha256), snippet, metadata
- **`Claim`** — text, requires_evidence (bool), evidence_ids[], confidence
- **`VerifierReport`** — per-claim and overall pass/fail/partial status
- **`PolicyVersion`** — versioned, testable policy snapshots

### Audit Bundle

Stored under `artifacts/runs/<run_id>/`:
- Input profile hash
- Policy version hash
- Prompt template IDs + param hashes
- Tool call hashes
- Intermediate outputs
- Verifier report
- Final artifacts

### Replay Modes

- **Strict**: use stored tool responses (no network calls)
- **Refresh**: re-fetch URLs, compare content hashes, flag drift
- Both produce a **diff report** (opportunity changes, trend evidence changes, priority shifts)

---

## Policy Files

All policies live in `/policy/*.yaml`. The policy engine loads and enforces:
- Tool/source allowlists and denylists per agent
- Step budgets and token limits (`policy/budgets.yaml`)
- Data boundary rules (which fields cross which agent boundaries)
- Redaction rules for PII in logs

Policy unit tests must verify that forbidden behavior is actually blocked.

---

## Verification Rules

Verifier **fails** the run if:
- Schema invalid
- Any claim requiring evidence has zero evidence
- Tool use violates policy
- Citations reference missing evidence IDs
- Confidence thresholds violated for "recommend to pursue" items

Verifier marks **partial** (not fail) if:
- Retrieval failed, but pipeline degraded safely and declared unknown sections

---

## Implementation Roadmap

### Phase 1: Core engine + minimal GUI
- Policy engine (tools + sources + budgets)
- LangGraph daily pipeline with job scout retriever/extractor (mock/stub agents)
- Verifier + audit writer
- PostgreSQL schema + profile CRUD
- GUI: dashboard, profile editor, run daily, view audit timeline
- SSE streaming for run progress

### Phase 2: Complete scouts + weekly plan + multi-profile
- Add certs + trends scout graphs
- Add CEO/CFO/coordinator agents to weekly graph
- Opportunities browser (aggregated from runs)
- Full profile workspace switching

### Phase 3: Cover letter + replay + diffs
- Cover letter pipeline graph
- Replay strict + refresh modes
- Diff UI between runs

---

## Development Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the FastAPI dev server
uvicorn app.main:app --reload

# Run tests
pytest

# Run a specific test file
pytest tests/test_policy_engine.py

# Lint
ruff check .
```

---

## Deliverables Checklist

- GUI can run daily/weekly and show outputs
- Every opportunity has evidence items (url + hash + snippet)
- Verifier gates outputs and explains failures
- Audit logs are immutable and replay works
- Diff view shows what changed between runs
- Policies are enforced and tested
- Profiles act as independent workspaces
- SSE streams real-time agent progress
