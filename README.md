# Modern Treasury Dataloader

Upload a JSON **DataLoaderConfig** in the browser: the app validates it, shows execution order (DAG), and creates resources in Modern Treasury’s **sandbox** via the Python SDK, with live progress (SSE).

---

## Quick start

**You need:** Python 3.11+, a Modern Treasury **sandbox** API key and org ID.

```bash
cd mt-dataloader
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open **http://127.0.0.1:8000**. Enter your **API key** and **org ID** on the setup screen, upload JSON (or paste), then **Validate → Preview → Execute**. No `.env` file is required.

---

## Configuration (everything optional)

| What | Default behavior |
|------|------------------|
| **MT credentials** | Enter in the web UI when you run a flow. Stored for that session; you can skip `.env` entirely. |
| **`.env`** | Optional. Copy `.env.example` → `.env` only if you want the server to pre-fill defaults (e.g. key/org so you don’t type them each time). |
| **`baseline.yaml`** | Optional fallback when **org discovery** can’t reach MT. Most self-contained configs define their own `connections` and `internal_accounts` and don’t rely on baseline. |
| **Runs / logs** | Written under `runs/` and `logs/` (created automatically). Override with `DATALOADER_RUNS_DIR` if you care. |

Other knobs (`DATALOADER_LOG_LEVEL`, `DATALOADER_MAX_CONCURRENT_REQUESTS`, etc.) are optional; see `.env.example` or `AppSettings` in `models.py`.

**Org discovery:** On validate, the app may query your org for existing connections / accounts / ledgers and register refs. If that fails (e.g. timeout), it falls back to `baseline.yaml`. Auth errors are not masked.

---

## JSON config

- **Schema (for LLMs / tools):** `GET /api/schema` — full `DataLoaderConfig` JSON Schema.
- **Validate without UI:** `POST /api/validate-json` — body = raw JSON; returns structured errors for repair loops.

Resources reference each other with **`$ref:<resource_type>.<ref>`** (e.g. `$ref:internal_account.buyer_maya_wallet`). The `ref` field on each object is a short key; the engine builds the typed name. Child refs include selectors like `$ref:counterparty.vendor_cp.account[0]`.

**Legal entities (sandbox):** For demos, you only need `ref`, `legal_entity_type`, and name fields in JSON. The app **replaces** identifications, addresses, documents, and related compliance fields with deterministic mock data before calling MT, so sandbox KYC/KYB stays predictable.

**Connections (sandbox):** Use **`entity_id: "example1"`** or **`"example2"`** on `connections` when the flow includes **ACH or wire** payment orders on newly created internal accounts. The **`modern_treasury`** entity is effectively **book-only** for new IAs in sandbox; ACH POs will 422. See `prompts/decision_rubrics.md` (Connections).

After creating a legal entity, the engine **polls** until MT reports `active` (or timeout) before continuing, so dependent internal accounts are less likely to race pending compliance.

See **`prompts/`** — start with **`prompts/README.md`** (what each file is for) and **`prompts/system_prompt.md`** (output format + paste order). Use the files under **`examples/`** as structural templates for PSP shapes.

---

## Webhooks (optional)

Receive real-time MT webhook events correlated to dataloader runs. Requires a public URL — the app runs locally, so you need a tunnel.

### 1. Start ngrok

```bash
ngrok http 8000
```

Copy the `https://` forwarding URL (e.g. `https://ab12-34-56.ngrok-free.app`).

### 2. Create a webhook endpoint in Modern Treasury

Go to **MT Dashboard → Developers → Webhooks → Add Endpoint**:

| Field | Value |
|-------|-------|
| **Webhook URL** | `https://<your-ngrok-subdomain>.ngrok-free.app/webhooks/mt` |
| **Basic Authentication** | Disabled |
| **Events to send** | "Receive all events" (recommended) or select specific types |

Click **Save**. MT will display a **signing secret** — copy it if you want signature verification (optional for sandbox).

### 3. Configure signature verification (optional)

Add the signing secret to `.env`:

```bash
DATALOADER_WEBHOOK_SECRET=whsec_...
```

Or leave it blank / unset to skip verification. Without it the receiver accepts all payloads — fine for sandbox demos.

### 4. Use the listener

Open **http://127.0.0.1:8000/listen** — the page auto-detects your ngrok tunnel and shows the full webhook URL. Incoming events stream live. Use the **Send Test** button to verify the pipeline works before running a real config.

After executing a config, go to **Runs → Details** for that run to see webhooks correlated to the resources it created.

### Staged resources (live demo mode)

Four resource types support `staged: true`: **payment orders**, **incoming payment details**, **expected payments**, and **ledger transactions**. Staged resources are resolved (refs replaced with real IDs) but **not created** during execution. They appear as "Fire" buttons on the run detail page so you can trigger them one-by-one during a live demo while webhook events stream in.

See `examples/staged_demo.json` for a working example and `prompts/decision_rubrics.md` (Staged Resources) for dependency rules.

---

## Examples

| File | What it shows |
|------|----------------|
| `examples/marketplace_demo.json` | Full PSP marketplace: `modern_treasury_bank` + `example1`, legal entities, counterparties, internal accounts (`*_wallet` refs, **Payment Account** MT names), sandbox **IPD**, **book** fee + settle + **ACH** payout, **ACH debit** NSF demo (`sandbox_behavior`). No ledger / EP / VA. |
| `examples/psp_minimal.json` | Smallest useful **book** transfer between two internal accounts. |
| `examples/staged_demo.json` | Marketplace with `staged: true` on IPD + 3 POs. Infrastructure creates normally; staged items get "Fire" buttons. Deposit → fee → settle → payout chain. |

Validate examples locally:

```bash
source .venv/bin/activate
python - <<'PY'
import json
from models import DataLoaderConfig
from engine import dry_run
for p in ("examples/marketplace_demo.json", "examples/psp_minimal.json", "examples/staged_demo.json"):
    with open(p) as f:
        dry_run(DataLoaderConfig(**json.load(f)))
    print(p, "OK")
PY
```

---

## Execution flow

1. **Validate** — Credentials check, optional discovery, parse JSON, build DAG, dry run.
2. **Preview** — Batches, dependencies, metadata, cleanup hints.
3. **Execute** — Topological order, SSE updates, idempotency keys on creates. Staged resources are resolved but held back.
4. **Run detail** — Config viewer, resource list, staged "Fire" buttons, live + historical webhooks (four tabs).
5. **Runs** — Manifests, cleanup (delete/archive what the API allows).

---

## Cleanup

| Action | Typical resources |
|--------|-------------------|
| Delete | Counterparties, external/virtual accounts, ledgers, ledger accounts, categories, expected payments |
| Archive | Ledger transactions |
| Remove | Category / nested category links |
| Skip | Internal accounts, legal entities, payment orders, returns, reversals, connections |

---

## Layout

```
main.py, models.py, engine.py, handlers.py, baseline.py
templates/     HTMX + Jinja2 UI
static/        CSS
examples/      marketplace_demo.json, psp_minimal.json, staged_demo.json
prompts/       LLM kit + system_prompt.md
baseline.yaml  discovery fallback
runs/, logs/   runtime (gitignored)
```

---

## Development

| Module | Role |
|--------|------|
| `models.py` | Pydantic config + `AppSettings` |
| `engine.py` | Refs, DAG (`graphlib`), execute, manifests |
| `handlers.py` | MT SDK calls, polling |
| `baseline.py` | Org discovery + YAML fallback |
| `main.py` | FastAPI, SSE, cleanup |
| `webhooks.py` | Webhook receiver, run detail, staged fire, listener |

```bash
source .venv/bin/activate
python test_step6_smoke.py
```

---

## Scope

**In:** Sandbox resource creation from JSON, `$ref` DAG, SSE UI, run manifests + idempotency, metadata passthrough, webhook receiver + correlation, staged resources with live-fire UI.

**Out:** Embedded LLM, production attach-to-arbitrary-org mode, full CLI.
