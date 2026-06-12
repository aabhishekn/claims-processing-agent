# Autonomous Insurance Claims Processing Agent (FNOL)

A lightweight Python agent that ingests FNOL (First Notice of Loss) documents, extracts key claim fields, identifies missing/inconsistent data, and routes the claim to the correct workflow with a human-readable explanation.

Built for the Synapx technical assessment.

## Architecture

```
 FNOL document (.pdf / .txt)
        │
        ▼
 ┌──────────────┐   pdfplumber / plain read
 │  ingest.py   │──► raw text
 └──────────────┘
        │
        ▼
 ┌──────────────┐   LLM via any OpenAI-compatible API (JSON mode, temperature 0)
 │  extract.py  │──► structured fields        ── falls back to a labeled-field
 └──────────────┘                                regex extractor if no API key
        │
        ▼
 ┌──────────────┐   mandatory-field check +
 │ validate.py  │──► missingFields[], consistency warnings
 └──────────────┘
        │
        ▼
 ┌──────────────┐   deterministic rules engine
 │   route.py   │──► recommendedRoute + reasoning
 └──────────────┘
        │
        ▼
   Result JSON
```

### Why hybrid LLM + rules?

- **Extraction is fuzzy** — real FNOLs arrive as scanned forms, emails, call transcripts. An LLM handles messy, unstructured wording far better than regex. The LLM is constrained by a strict JSON schema and told to return `null` rather than guess.
- **Provider-agnostic** — extraction talks to any OpenAI-compatible API via three env vars (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`). Defaults target Groq's free tier (`llama-3.3-70b-versatile`); xAI Grok, OpenAI, etc. work by changing the base URL and model.
- **Routing is policy** — business rules must be auditable, testable, and deterministic. They live in plain Python (`route.py`) with unit tests, not in a prompt. The reasoning string cites exactly which rule fired.
- **Graceful degradation** — without an `LLM_API_KEY` the agent automatically uses a regex extractor for labeled-field documents, so the whole pipeline runs offline.

### Routing rules (precedence order)

| # | Condition | Route |
|---|-----------|-------|
| 1 | Description contains "fraud", "inconsistent", or "staged" | **Investigation Flag** |
| 2 | Claim type is injury | **Specialist Queue** |
| 3 | Any mandatory field missing | **Manual Review** |
| 4 | Estimated damage < 25,000 | **Fast-track** |
| 5 | Otherwise (complete, clean, high-value) | **Standard Processing** |

Precedence rationale: a potential fraud signal must never be fast-tracked, and injury claims need specialist handling even when paperwork is incomplete. Rule 5 is an assumption — the brief doesn't define a route for complete, clean claims at/above the threshold, so they go to the standard adjuster workflow.

**Mandatory fields:** policy number, policyholder name, incident date, location, description, claimant, asset type, estimated damage, claim type.

**Consistency checks** (reported as warnings in the reasoning/meta, don't change the route): incident date outside policy effective dates, incident date in the future, estimated damage vs initial estimate differing by more than 50%.

## Output format

```json
{
  "extractedFields": {
    "policyInformation": { "policyNumber": "...", "policyholderName": "...", "effectiveDates": "..." },
    "incidentInformation": { "date": "...", "time": "...", "location": "...", "description": "..." },
    "involvedParties": { "claimant": "...", "thirdParties": "...", "contactDetails": "..." },
    "assetDetails": { "assetType": "...", "assetId": "...", "estimatedDamage": 18000.0 },
    "otherFields": { "claimType": "...", "attachments": "...", "initialEstimate": 17500.0 }
  },
  "missingFields": ["policyInformation.policyNumber"],
  "recommendedRoute": "Manual Review",
  "reasoning": "1 mandatory field(s) missing: policyInformation.policyNumber. A human must complete the file before it can proceed.",
  "meta": { "sourceFile": "...", "extractionMethod": "llm", "inconsistencies": [] }
}
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional — enables LLM extraction (otherwise regex fallback is used):
cp .env.example .env   # then add your LLM_API_KEY (free key: https://console.groq.com)
```

## Run

```bash
# Generate the 5 dummy FNOL samples (2 TXT + 3 PDF)
python scripts/generate_samples.py

# Process one document (JSON to stdout)
python -m claims_agent.cli samples/fnol_01_fasttrack.txt

# Batch process a directory, write JSON files
python -m claims_agent.cli samples/ --out outputs/

# Web UI
streamlit run app.py

# Tests
python -m pytest tests/
```

## Sample results

| Sample | Scenario | Route |
|--------|----------|-------|
| `fnol_01_fasttrack.txt` | Complete, damage ₹18,000 | Fast-track |
| `fnol_02_missing_fields.txt` | No policy number / asset ID / estimate | Manual Review |
| `fnol_03_fraud_flag.pdf` | Description mentions "staged" / "inconsistent" | Investigation Flag |
| `fnol_04_injury.pdf` | Claim type: Injury | Specialist Queue |
| `fnol_05_high_damage.pdf` | Complete, damage ₹3,50,000 | Standard Processing |

Also handles a real **blank ACORD 2 Automobile Loss Notice PDF** gracefully: nearly all fields come back `null` → Manual Review.

## Project layout

```
claims_agent/
  ingest.py     # PDF/TXT -> raw text
  extract.py    # LLM extraction (OpenAI-compatible JSON mode) + regex fallback, normalization
  validate.py   # mandatory-field + consistency checks
  route.py      # deterministic routing rules engine
  agent.py      # pipeline orchestrator
  cli.py        # command-line interface
scripts/generate_samples.py   # builds the 5 dummy FNOLs
app.py                        # Streamlit UI
tests/test_routing.py         # rules, precedence, parsing, extraction tests
```

## Assumptions

- Currency amounts are INR; "₹", "Rs.", "INR", and Indian digit grouping (2,80,000) are all parsed.
- "None" / "N/A" / empty values are treated as missing.
- Complete claims at/above the fast-track threshold go to Standard Processing (not defined in the brief).
- Consistency warnings inform the reviewer but don't override the routing rules.
