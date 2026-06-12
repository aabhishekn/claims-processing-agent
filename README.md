# 🚗 Autonomous Insurance Claims Processing Agent (FNOL)

A lightweight Python agent that reads **FNOL (First Notice of Loss)** documents and automates the first step of the insurance claims lifecycle:

1. **Extracts** key claim fields from PDF / TXT documents
2. **Identifies** missing or inconsistent fields
3. **Classifies & routes** the claim to the correct workflow
4. **Explains** the routing decision in plain language

> **What is an FNOL?** The first report a policyholder files with their insurer after an incident (accident, theft, damage). FNOL intake is largely manual today — agents read forms, emails and call transcripts, re-key the data, and decide which workflow each claim follows. This agent automates exactly that.

---

## Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Fields Extracted](#fields-extracted)
- [Routing Rules](#routing-rules)
- [Output Format](#output-format)
- [Usage](#usage)
- [Sample Documents & Results](#sample-documents--results)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Design Decisions](#design-decisions)
- [Assumptions](#assumptions)
- [Future Improvements](#future-improvements)

---

## Quick Start

```bash
# 1. Clone and set up
git clone <repo-url> && cd <repo>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. (Optional) Enable LLM extraction — free key from https://console.groq.com
cp .env.example .env        # paste your key into LLM_API_KEY

# 3. Generate the 5 dummy FNOL samples
python scripts/generate_samples.py

# 4. Run the agent
python -m claims_agent.cli samples/ --out outputs/

# 5. Or use the web UI
streamlit run app.py
```

No API key? No problem — the agent automatically falls back to a built-in regex extractor and the full pipeline still runs offline.

---

## How It Works

The agent is a four-stage pipeline. Each stage is an independent, unit-testable module:

```
 FNOL document (.pdf / .txt)
        │
        ▼
 ┌──────────────┐  pdfplumber (PDF) / plain read (TXT)
 │  ingest.py   │──► raw text
 └──────────────┘
        │
        ▼
 ┌──────────────┐  LLM via any OpenAI-compatible API (JSON mode, temperature 0)
 │  extract.py  │──► structured fields      ── regex fallback when no API key
 └──────────────┘
        │
        ▼
 ┌──────────────┐  mandatory-field check + consistency checks
 │ validate.py  │──► missingFields[], warnings[]
 └──────────────┘
        │
        ▼
 ┌──────────────┐  deterministic, ordered business rules
 │   route.py   │──► recommendedRoute + reasoning
 └──────────────┘
        │
        ▼
   Result JSON ──► CLI output / Streamlit UI
```

### Stage 1 — Ingest (`claims_agent/ingest.py`)
Loads the document and returns raw text. PDFs go through `pdfplumber` (layout-aware text extraction); TXT files are read directly.

### Stage 2 — Extract (`claims_agent/extract.py`)
Two interchangeable extractors:

| Extractor | When used | How it works |
|-----------|-----------|--------------|
| **LLM** | `LLM_API_KEY` set | Calls any OpenAI-compatible API in JSON mode at temperature 0 with a strict field schema. Instructed to return `null` rather than guess — it never invents data. |
| **Regex** | No API key, or LLM call fails | Matches labeled fields (`Policy Number: ...`), handles multi-line wrapped values from PDFs. |

Values are normalized either way: dates → ISO (`YYYY-MM-DD`), amounts → plain numbers (`₹2,80,000` → `280000.0`), `None`/`N/A`/empty → `null`.

**Provider-agnostic:** three env vars control the LLM — `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`. Defaults target **Groq's free tier** (`llama-3.3-70b-versatile`); xAI Grok, OpenAI, or any compatible provider works by changing the base URL and model.

### Stage 3 — Validate (`claims_agent/validate.py`)
- **Mandatory-field check** — 9 fields are mandatory (see [Fields Extracted](#fields-extracted)). Empty/null ones are reported as dotted paths, e.g. `policyInformation.policyNumber`.
- **Consistency checks** — flagged as warnings (they inform the reviewer but don't change the route):
  - Incident date outside the policy effective dates
  - Incident date in the future
  - Estimated damage vs. initial estimate differing by more than 50%

### Stage 4 — Route (`claims_agent/route.py`)
A deterministic rules engine evaluated in strict precedence order (see [Routing Rules](#routing-rules)). The reasoning string cites exactly which rule fired.

---

## Fields Extracted

| Group | Fields | Mandatory |
|-------|--------|-----------|
| **Policy Information** | Policy Number, Policyholder Name, Effective Dates | Policy Number, Policyholder Name |
| **Incident Information** | Date, Time, Location, Description | Date, Location, Description |
| **Involved Parties** | Claimant, Third Parties, Contact Details | Claimant |
| **Asset Details** | Asset Type, Asset ID, Estimated Damage | Asset Type, Estimated Damage |
| **Other Fields** | Claim Type, Attachments, Initial Estimate | Claim Type |

---

## Routing Rules

Evaluated top-down — the **first rule that matches decides the route**:

| # | Condition | Route |
|---|-----------|-------|
| 1 | Description contains "fraud", "inconsistent", or "staged" | 🚨 **Investigation Flag** |
| 2 | Claim type is injury | 🩺 **Specialist Queue** |
| 3 | Any mandatory field missing | 📝 **Manual Review** |
| 4 | Estimated damage < 25,000 | ✅ **Fast-track** |
| 5 | Otherwise (complete, clean, high-value) | 📂 **Standard Processing** |

**Why this order?** A potential fraud signal must never be fast-tracked, and injury claims need specialist handling even when paperwork is incomplete. Rule 5 is a documented assumption — the brief doesn't define a route for complete, clean claims at/above the threshold, so they follow the standard adjuster workflow.

---

## Output Format

```json
{
  "extractedFields": {
    "policyInformation":   { "policyNumber": "POL-2026-88341", "policyholderName": "Rajesh Kumar Sharma", "effectiveDates": "2026-01-01 to 2026-12-31" },
    "incidentInformation": { "date": "2026-06-02", "time": "08:45 AM", "location": "Andheri East, Mumbai, Maharashtra", "description": "..." },
    "involvedParties":     { "claimant": "Rajesh Kumar Sharma", "thirdParties": null, "contactDetails": "+91 98200 11223" },
    "assetDetails":        { "assetType": "Private Car - Hyundai Creta 2023", "assetId": "MH02-AB-4455", "estimatedDamage": 18000.0 },
    "otherFields":         { "claimType": "Own Damage", "attachments": "photos_rear_door.zip", "initialEstimate": 17500.0 }
  },
  "missingFields": [],
  "recommendedRoute": "Fast-track",
  "reasoning": "All mandatory fields present, no fraud indicators, and estimated damage (18,000) is below the 25,000 fast-track threshold.",
  "meta": {
    "sourceFile": "samples/fnol_01_fasttrack.txt",
    "extractionMethod": "llm",
    "inconsistencies": []
  }
}
```

---

## Usage

### Command line

```bash
# Single document → JSON to stdout
python -m claims_agent.cli samples/fnol_01_fasttrack.txt

# Batch process a directory → one JSON file per document
python -m claims_agent.cli samples/ --out outputs/
```

Batch output:

```
fnol_01_fasttrack.txt -> Fast-track  (outputs/fnol_01_fasttrack.json)
fnol_02_missing_fields.txt -> Manual Review  (outputs/fnol_02_missing_fields.json)
fnol_03_fraud_flag.pdf -> Investigation Flag  (outputs/fnol_03_fraud_flag.json)
fnol_04_injury.pdf -> Specialist Queue  (outputs/fnol_04_injury.json)
fnol_05_high_damage.pdf -> Standard Processing  (outputs/fnol_05_high_damage.json)
```

### Web UI

```bash
streamlit run app.py
```

Upload an FNOL document → see the extracted fields table, missing-field warnings, a colored route badge, the reasoning, and downloadable result JSON.

---

## Sample Documents & Results

Five dummy FNOLs (2 TXT + 3 PDF) are generated by `scripts/generate_samples.py`. Each exercises one routing outcome:

| Sample | Scenario | Route |
|--------|----------|-------|
| `fnol_01_fasttrack.txt` | Complete claim, damage ₹18,000 | ✅ Fast-track |
| `fnol_02_missing_fields.txt` | No policy number / asset ID / estimate | 📝 Manual Review |
| `fnol_03_fraud_flag.pdf` | Description mentions "staged" / "inconsistent" | 🚨 Investigation Flag |
| `fnol_04_injury.pdf` | Claim type: Injury (third party hurt) | 🩺 Specialist Queue |
| `fnol_05_high_damage.pdf` | Complete claim, damage ₹3,50,000 | 📂 Standard Processing |

The agent also handles a real **blank ACORD 2 Automobile Loss Notice PDF** gracefully — nearly all fields come back `null`, so it routes to Manual Review instead of crashing.

---

## Project Structure

```
claims_agent/
  ingest.py     # PDF/TXT -> raw text
  extract.py    # LLM extraction (OpenAI-compatible JSON mode) + regex fallback, normalization
  validate.py   # mandatory-field + consistency checks
  route.py      # deterministic routing rules engine
  agent.py      # pipeline orchestrator
  cli.py        # command-line interface
scripts/
  generate_samples.py   # builds the 5 dummy FNOL documents
app.py                  # Streamlit UI
tests/
  test_routing.py       # 14 unit tests: rules, precedence, parsing, extraction
samples/                # generated dummy FNOLs (2 TXT + 3 PDF)
```

---

## Testing

```bash
python -m pytest tests/
```

14 unit tests cover:
- All 5 routing outcomes
- Rule precedence (fraud beats injury beats missing beats fast-track)
- Currency parsing (`Rs. 18,000`, `₹2,80,000`, `INR 25000.50`, plain numbers)
- Regex extraction, including multi-line wrapped PDF text and empty values
- Both consistency checks

---

## Design Decisions

### Why hybrid LLM + rules?

- **Extraction is fuzzy** — real FNOLs arrive as scanned forms, emails, call transcripts. An LLM handles messy, unstructured wording far better than regex. The LLM is constrained by a strict JSON schema and told to return `null` rather than guess.
- **Routing is policy** — business rules must be auditable, deterministic, and testable. They live in plain Python with unit tests, not inside a prompt. The reasoning cites exactly which rule fired.
- **Graceful degradation** — without an API key the agent automatically uses the regex extractor, so the whole pipeline runs offline.

### Tools & frameworks

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.9+ | Assignment requirement; rich PDF/LLM ecosystem |
| PDF text | pdfplumber | Reliable layout-aware extraction |
| LLM | OpenAI-compatible API (Groq default) | Strict JSON output, temperature 0, provider-agnostic, free tier |
| UI | Streamlit | Fast to build, ideal for demo |
| Sample PDFs | reportlab | Programmatic dummy FNOL generation |
| Tests | pytest | Unit tests for rules, parsing, extraction |

---

## Assumptions

- Currency amounts are INR; "₹", "Rs.", "INR", and Indian digit grouping (2,80,000) are all parsed.
- "None" / "N/A" / empty values are treated as missing.
- Complete claims at/above the fast-track threshold go to **Standard Processing** (not defined in the brief).
- Consistency warnings inform the reviewer but don't override the routing rules.

---

## Future Improvements

- OCR (e.g. Tesseract) for scanned/image-only FNOL documents
- Per-field confidence scores; low confidence routes to Manual Review
- Fuzzy/semantic fraud detection beyond keyword matching
- Queue integration — publish routing decisions to a message broker / claims system
