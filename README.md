# Autonomous Insurance Claims Processing Agent (FNOL)

A Python agent that reads FNOL (First Notice of Loss) documents and automates the first step of the insurance claims lifecycle:

1. Extracts key claim fields from PDF and TXT documents
2. Identifies missing or inconsistent fields
3. Classifies and routes the claim to the correct workflow
4. Explains the routing decision in plain language

**What is an FNOL?**
The first report a policyholder files with their insurer after an incident (accident, theft, or damage). FNOL intake is largely manual — agents read forms, emails, and call transcripts, re-key the data, and decide which workflow each claim follows. This agent automates that process.

---

## Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Fields Extracted](#fields-extracted)
- [Routing Rules](#routing-rules)
- [Output Format](#output-format)
- [Usage](#usage)
- [Sample Documents and Results](#sample-documents-and-results)
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

# 4. Run the agent on all samples
python -m claims_agent.cli samples/ --out outputs/

# 5. Or launch the web UI
streamlit run app.py
```

No API key? The agent automatically falls back to a built-in regex extractor and the full pipeline runs offline.

---

## How It Works

The agent runs as a four-stage pipeline. Each stage is an independent, unit-testable Python module.

```
FNOL document (.pdf / .txt)
        |
        v
+---------------+   pdfplumber (PDF) / plain read (TXT)
|  ingest.py    |---> raw text
+---------------+
        |
        v
+---------------+   LLM via any OpenAI-compatible API (JSON mode, temperature 0)
|  extract.py   |---> structured fields      (regex fallback when no API key)
+---------------+
        |
        v
+---------------+   mandatory-field check + consistency checks
|  validate.py  |---> missingFields[], warnings[]
+---------------+
        |
        v
+---------------+   deterministic, ordered business rules
|   route.py    |---> recommendedRoute + reasoning
+---------------+
        |
        v
   Result JSON  --->  CLI output or Streamlit UI
```

### Stage 1 — Ingest

Loads the document and returns raw text. PDFs go through `pdfplumber` for layout-aware extraction; TXT files are read directly.

### Stage 2 — Extract

Two interchangeable extractors:

| Extractor | When used | How it works |
|-----------|-----------|--------------|
| LLM | `LLM_API_KEY` is set | Calls any OpenAI-compatible API in JSON mode at temperature 0 with a strict field schema. Returns `null` for missing fields — never invents data. |
| Regex | No API key, or LLM call fails | Matches labeled fields like `Policy Number: ...` and handles multi-line wrapped PDF text. |

Values are normalized by both extractors: dates become ISO format (`YYYY-MM-DD`), amounts become plain numbers (`Rs. 2,80,000` becomes `280000.0`), and `None` / `N/A` / empty strings become `null`.

**Provider configuration:**
The LLM extractor is provider-agnostic. Three environment variables control it:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | (none) | API key for your chosen provider |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | API base URL |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Model name |

Groq offers a free tier with no credit card required. xAI Grok, OpenAI, or any OpenAI-compatible provider also work by changing `LLM_BASE_URL` and `LLM_MODEL`.

### Stage 3 — Validate

Checks two things:

**Mandatory fields** — 9 fields must be present for a claim to proceed without manual intervention. Missing ones are reported as dotted paths, for example `policyInformation.policyNumber`.

**Consistency checks** — reported as warnings. They inform the reviewer but do not change the routing outcome.
- Incident date falls outside the policy effective dates
- Incident date is in the future
- Estimated damage and initial estimate differ by more than 50%

### Stage 4 — Route

A deterministic rules engine that evaluates conditions in strict precedence order. The first matching rule decides the route. The reasoning string says exactly which rule fired and why.

---

## Fields Extracted

| Group | Fields | Mandatory |
|-------|--------|:---------:|
| Policy Information | Policy Number, Policyholder Name, Effective Dates | Policy Number, Policyholder Name |
| Incident Information | Date, Time, Location, Description | Date, Location, Description |
| Involved Parties | Claimant, Third Parties, Contact Details | Claimant |
| Asset Details | Asset Type, Asset ID, Estimated Damage | Asset Type, Estimated Damage |
| Other Fields | Claim Type, Attachments, Initial Estimate | Claim Type |

---

## Routing Rules

Rules are evaluated top-down. The first rule that matches decides the route.

| Priority | Condition | Route |
|----------|-----------|-------|
| 1 | Description contains "fraud", "inconsistent", or "staged" | Investigation Flag |
| 2 | Claim type is injury | Specialist Queue |
| 3 | Any mandatory field is missing | Manual Review |
| 4 | Estimated damage is less than 25,000 | Fast-track |
| 5 | All fields present, no issues, damage at or above 25,000 | Standard Processing |

**Why this order?**
A fraud signal must never be fast-tracked regardless of other conditions. Injury claims need specialist handling even when paperwork is incomplete. Rule 5 covers complete, clean, high-value claims — this route is not defined in the assignment brief, so Standard Processing is used as a documented assumption.

---

## Output Format

```json
{
  "extractedFields": {
    "policyInformation": {
      "policyNumber": "POL-2026-88341",
      "policyholderName": "Rajesh Kumar Sharma",
      "effectiveDates": "2026-01-01 to 2026-12-31"
    },
    "incidentInformation": {
      "date": "2026-06-02",
      "time": "08:45 AM",
      "location": "Andheri East, Mumbai, Maharashtra",
      "description": "While reversing out of the office parking lot, the vehicle scraped a concrete pillar."
    },
    "involvedParties": {
      "claimant": "Rajesh Kumar Sharma",
      "thirdParties": null,
      "contactDetails": "+91 98200 11223"
    },
    "assetDetails": {
      "assetType": "Private Car - Hyundai Creta 2023",
      "assetId": "MH02-AB-4455",
      "estimatedDamage": 18000.0
    },
    "otherFields": {
      "claimType": "Own Damage",
      "attachments": "photos_rear_door.zip",
      "initialEstimate": 17500.0
    }
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

Process a single document and print JSON to stdout:

```bash
python -m claims_agent.cli samples/fnol_01_fasttrack.txt
```

Process a directory and write one JSON file per document:

```bash
python -m claims_agent.cli samples/ --out outputs/
```

Expected output for the batch run:

```
fnol_01_fasttrack.txt      -> Fast-track           (outputs/fnol_01_fasttrack.json)
fnol_02_missing_fields.txt -> Manual Review         (outputs/fnol_02_missing_fields.json)
fnol_03_fraud_flag.pdf     -> Investigation Flag    (outputs/fnol_03_fraud_flag.json)
fnol_04_injury.pdf         -> Specialist Queue      (outputs/fnol_04_injury.json)
fnol_05_high_damage.pdf    -> Standard Processing   (outputs/fnol_05_high_damage.json)
```

### Web UI

```bash
streamlit run app.py
```

Upload an FNOL document to see the extracted fields table, missing-field warnings, the recommended route, the reasoning, and a downloadable result JSON.

---

## Sample Documents and Results

Five dummy FNOL documents (2 TXT and 3 PDF) are generated by `scripts/generate_samples.py`. Each exercises one routing outcome.

| Sample | Scenario | Expected Route |
|--------|----------|----------------|
| `fnol_01_fasttrack.txt` | Complete claim, damage Rs. 18,000 | Fast-track |
| `fnol_02_missing_fields.txt` | No policy number, no asset ID, no estimate | Manual Review |
| `fnol_03_fraud_flag.pdf` | Description contains "staged" and "inconsistent" | Investigation Flag |
| `fnol_04_injury.pdf` | Claim type is Injury | Specialist Queue |
| `fnol_05_high_damage.pdf` | Complete claim, damage Rs. 3,50,000 | Standard Processing |

The agent also handles a real blank ACORD 2 Automobile Loss Notice PDF gracefully. Nearly all fields are null, so it routes to Manual Review without errors.

---

## Project Structure

```
claims_agent/
    ingest.py       PDF/TXT document loading -> raw text
    extract.py      LLM extraction (OpenAI-compatible JSON mode) + regex fallback
    validate.py     Mandatory-field and consistency checks
    route.py        Deterministic routing rules engine
    agent.py        Pipeline orchestrator
    cli.py          Command-line interface

scripts/
    generate_samples.py     Generates the 5 dummy FNOL documents

app.py                      Streamlit web UI
tests/
    test_routing.py         14 unit tests

samples/                    Generated dummy FNOL files (2 TXT + 3 PDF)
.env.example                Environment variable template
requirements.txt            Python dependencies
```

---

## Testing

```bash
python -m pytest tests/
```

14 unit tests cover:

- All 5 routing outcomes
- Rule precedence (fraud beats injury, injury beats missing, missing beats fast-track)
- Currency parsing: `Rs. 18,000`, `Rs. 2,80,000`, `INR 25000.50`, plain numbers
- Regex extraction including multi-line wrapped PDF text
- Empty and N/A values treated as missing
- Both consistency checks

---

## Design Decisions

### Hybrid LLM and deterministic rules

**Why LLM for extraction?**
Real FNOL documents arrive as scanned forms, emails, and call transcripts — they do not follow a fixed format. An LLM with a strict JSON schema handles unstructured wording far better than regex. It is configured at temperature 0 and instructed to return `null` rather than guess, so it never fabricates data.

**Why deterministic rules for routing?**
Business rules must be auditable, testable, and easy to modify. Putting them in a prompt makes them opaque and non-deterministic. A plain Python rules engine with unit tests is more reliable and transparent. The reasoning string cites the exact rule that fired.

**Why a regex fallback?**
The full pipeline should run without any external dependency. The regex extractor handles labeled-field documents well enough for the demo and for offline development.

### Tools and frameworks

| Component | Library | Reason |
|-----------|---------|--------|
| PDF extraction | pdfplumber | Reliable layout-aware text extraction |
| LLM extraction | openai SDK | Provider-agnostic, works with Groq, xAI, OpenAI, etc. |
| Web UI | Streamlit | Fast to build, good for demos |
| Sample PDFs | reportlab | Programmatic PDF generation |
| Tests | pytest | Standard Python testing |

---

## Assumptions

- Currency amounts are INR. The symbols Rs., INR, and the Indian digit grouping format (2,80,000) are all supported.
- "None", "N/A", and empty values are treated as missing fields.
- Complete claims at or above the 25,000 threshold use Standard Processing because this route is not defined in the assignment brief.
- Consistency warnings inform the reviewer but do not change the routing decision.

---

## Future Improvements

- OCR support (for example, Tesseract) for scanned or image-only FNOL documents
- Per-field confidence scores, with low-confidence fields triggering Manual Review
- Semantic fraud detection beyond keyword matching
- Integration with a claims management system or message queue
