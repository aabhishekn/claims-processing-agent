"""Generate docs/Solution_Approach.pdf — structured solution document for the assignment."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent.parent / "docs" / "Solution_Approach.pdf"

ACCENT = colors.HexColor("#1f4e79")
LIGHT = colors.HexColor("#dce6f1")
GREY = colors.HexColor("#f3f4f6")

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1x", parent=styles["Heading1"], textColor=ACCENT, spaceBefore=18, spaceAfter=6)
H2 = ParagraphStyle("H2x", parent=styles["Heading2"], textColor=ACCENT, spaceBefore=12, spaceAfter=4)
BODY = ParagraphStyle("Bodyx", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=6)
BULLET = ParagraphStyle("Bulletx", parent=BODY, leftIndent=14, bulletIndent=4, spaceAfter=3)
CODE = ParagraphStyle(
    "Codex", parent=styles["Code"], fontSize=8, leading=10.5,
    backColor=GREY, borderPadding=6, leftIndent=4, spaceAfter=8, spaceBefore=2,
)
TITLE = ParagraphStyle("Titlex", parent=styles["Title"], textColor=ACCENT, fontSize=22, alignment=TA_CENTER)
SUB = ParagraphStyle("Subx", parent=styles["Normal"], fontSize=11, alignment=TA_CENTER, textColor=colors.HexColor("#555555"))


def bullets(items):
    return [Paragraph(f"• {t}", BULLET) for t in items]


def table(data, col_widths, header=True):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY]),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def cell(text):
    return Paragraph(text, ParagraphStyle("cell", parent=BODY, fontSize=9, leading=12, spaceAfter=0))


story = []

# ---- Cover / header ----
story.append(Spacer(1, 18 * mm))
story.append(Paragraph("Autonomous Insurance Claims Processing Agent", TITLE))
story.append(Spacer(1, 4 * mm))
story.append(Paragraph("FNOL Extraction, Validation &amp; Intelligent Routing — Solution Document", SUB))
story.append(Spacer(1, 2 * mm))
story.append(Paragraph("Abhishek Nikam", SUB))
story.append(Spacer(1, 6 * mm))
story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT))
story.append(Spacer(1, 6 * mm))

# ---- 1. Problem ----
story.append(Paragraph("1. Problem Statement", H1))
story.append(Paragraph(
    "Insurance claim intake begins with an FNOL (First Notice of Loss) — the first report a "
    "policyholder files after an incident. FNOL intake is largely manual: agents read forms, emails and "
    "call transcripts, re-key the data, and decide which workflow each claim should follow. The goal of "
    "this assignment is a lightweight agent that automates this step end-to-end:", BODY))
story += bullets([
    "<b>Extract</b> key fields from FNOL documents (PDF / TXT).",
    "<b>Identify</b> missing or inconsistent fields.",
    "<b>Classify and route</b> the claim to the correct workflow.",
    "<b>Explain</b> the routing decision in plain language.",
])

# ---- 2. Architecture ----
story.append(Paragraph("2. Solution Architecture", H1))
story.append(Paragraph(
    "The agent is a four-stage pipeline. Each stage is an independent, unit-testable Python module:", BODY))
story.append(Preformatted(
"""FNOL document (.pdf / .txt)
        |
        v
+---------------+   pdfplumber (PDF) / plain read (TXT)
|  ingest.py    |-> raw text
+---------------+
        |
        v
+---------------+   LLM (OpenAI-compatible API), strict JSON schema, temperature 0
|  extract.py   |-> structured fields   (regex fallback when no API key)
+---------------+
        |
        v
+---------------+   mandatory-field check + consistency checks
|  validate.py  |-> missingFields[], warnings[]
+---------------+
        |
        v
+---------------+   deterministic, ordered business rules
|   route.py    |-> recommendedRoute + reasoning
+---------------+
        |
        v
   Result JSON  ->  CLI output / Streamlit UI""", CODE))

story.append(Paragraph("2.1 Design Principle: Hybrid LLM + Rules", H2))
story += bullets([
    "<b>Extraction is fuzzy</b> — real FNOLs arrive as scanned forms, emails and transcripts. An LLM "
    "(called with a strict JSON schema at temperature 0) handles messy wording far better than regex. "
    "It is instructed to return <i>null</i> rather than guess, so it never invents data. The extractor is "
    "provider-agnostic: any OpenAI-compatible API works via env vars (LLM_API_KEY, LLM_BASE_URL, "
    "LLM_MODEL); defaults target Groq's free tier.",
    "<b>Routing is policy</b> — business rules must be auditable, deterministic and testable. They live "
    "in plain Python with unit tests, not inside a prompt. The reasoning string cites exactly which rule fired.",
    "<b>Graceful degradation</b> — without an API key the agent automatically switches to a labelled-field "
    "regex extractor, so the entire pipeline also runs fully offline.",
])

# ---- 3. Fields ----
story.append(Paragraph("3. Fields Extracted", H1))
story.append(table(
    [
        ["Group", "Fields"],
        ["Policy Information", "Policy Number, Policyholder Name, Effective Dates"],
        ["Incident Information", "Date, Time, Location, Description"],
        ["Involved Parties", "Claimant, Third Parties, Contact Details"],
        ["Asset Details", "Asset Type, Asset ID, Estimated Damage"],
        ["Other Mandatory Fields", "Claim Type, Attachments, Initial Estimate"],
    ],
    [45 * mm, 115 * mm],
))
story.append(Spacer(1, 3 * mm))
story.append(Paragraph(
    "Normalisation: dates → ISO (YYYY-MM-DD); amounts → plain numbers. '₹', 'Rs.', 'INR' and Indian "
    "digit grouping (2,80,000) are all parsed. 'None' / 'N/A' / empty values are treated as missing.", BODY))

# ---- 4. Validation ----
story.append(Paragraph("4. Validation", H1))
story.append(Paragraph("4.1 Mandatory-Field Check", H2))
story.append(Paragraph(
    "Nine fields are mandatory: policy number, policyholder name, incident date, location, description, "
    "claimant, asset type, estimated damage and claim type. Any empty/null mandatory field is reported in "
    "<font face='Courier'>missingFields</font> using a dotted path "
    "(e.g. <font face='Courier'>policyInformation.policyNumber</font>).", BODY))
story.append(Paragraph("4.2 Consistency Checks", H2))
story += bullets([
    "Incident date outside the policy effective dates.",
    "Incident date in the future.",
    "Estimated damage vs. initial estimate differing by more than 50%.",
])
story.append(Paragraph(
    "Consistency findings are surfaced as warnings inside the reasoning and metadata; they inform the "
    "reviewer but do not override the routing rules.", BODY))

story.append(PageBreak())

# ---- 5. Routing ----
story.append(Paragraph("5. Routing Rules Engine", H1))
story.append(Paragraph(
    "Rules are evaluated in strict precedence order — the first rule that matches decides the route:", BODY))
story.append(table(
    [
        ["#", "Condition", "Route"],
        ["1", cell("Description contains “fraud”, “inconsistent” or “staged”"), "Investigation Flag"],
        ["2", cell("Claim type is injury"), "Specialist Queue"],
        ["3", cell("Any mandatory field is missing"), "Manual Review"],
        ["4", cell("Estimated damage &lt; 25,000"), "Fast-track"],
        ["5", cell("Otherwise (complete, clean, high-value)"), "Standard Processing"],
    ],
    [10 * mm, 95 * mm, 55 * mm],
))
story.append(Spacer(1, 3 * mm))
story.append(Paragraph(
    "<b>Why this order?</b> A potential fraud signal must never be fast-tracked, and injury claims need "
    "specialist handling even when paperwork is incomplete. Rule 5 is a documented assumption: the brief "
    "does not define a route for complete, clean claims at or above the threshold, so they follow the "
    "standard adjuster workflow.", BODY))

# ---- 6. Output ----
story.append(Paragraph("6. Output Format", H1))
story.append(Preformatted(
"""{
  "extractedFields": {
    "policyInformation":  { "policyNumber": "...", "policyholderName": "...", "effectiveDates": "..." },
    "incidentInformation":{ "date": "...", "time": "...", "location": "...", "description": "..." },
    "involvedParties":    { "claimant": "...", "thirdParties": "...", "contactDetails": "..." },
    "assetDetails":       { "assetType": "...", "assetId": "...", "estimatedDamage": 18000.0 },
    "otherFields":        { "claimType": "...", "attachments": "...", "initialEstimate": 17500.0 }
  },
  "missingFields": ["policyInformation.policyNumber"],
  "recommendedRoute": "Manual Review",
  "reasoning": "1 mandatory field(s) missing: policyInformation.policyNumber. ...",
  "meta": { "sourceFile": "...", "extractionMethod": "llm", "inconsistencies": [] }
}""", CODE))

# ---- 7. Samples ----
story.append(Paragraph("7. Sample Documents &amp; Results", H1))
story.append(Paragraph(
    "Five dummy FNOL documents (2 TXT + 3 PDF) are generated by "
    "<font face='Courier'>scripts/generate_samples.py</font>. Each exercises one routing outcome; all five "
    "route correctly. A real blank ACORD 2 Automobile Loss Notice form is also handled gracefully — nearly "
    "all fields come back null, so it routes to Manual Review.", BODY))
story.append(table(
    [
        ["Sample", "Scenario", "Route"],
        [cell("fnol_01_fasttrack.txt"), cell("Complete claim, damage ₹18,000"), "Fast-track"],
        [cell("fnol_02_missing_fields.txt"), cell("No policy number / asset ID / estimate"), "Manual Review"],
        [cell("fnol_03_fraud_flag.pdf"), cell("Description mentions “staged” / “inconsistent”"), "Investigation Flag"],
        [cell("fnol_04_injury.pdf"), cell("Claim type: Injury (third party hurt)"), "Specialist Queue"],
        [cell("fnol_05_high_damage.pdf"), cell("Complete claim, damage ₹3,50,000"), "Standard Processing"],
    ],
    [52 * mm, 68 * mm, 40 * mm],
))

# ---- 8. Testing ----
story.append(Paragraph("8. Testing", H1))
story += bullets([
    "<b>14 unit tests</b> (pytest) cover every routing rule, the precedence order, currency parsing, "
    "regex extraction (including wrapped multi-line PDF text), empty-value handling and both consistency checks.",
    "<b>End-to-end</b>: batch CLI run over all five samples plus the blank ACORD PDF.",
])

story.append(PageBreak())

# ---- 9. How to run ----
story.append(Paragraph("9. How to Run", H1))
story.append(Preformatted(
"""# 1. Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional - enables LLM extraction (regex fallback used otherwise)
cp .env.example .env        # add LLM_API_KEY (free key: console.groq.com)

# 2. Generate the 5 dummy FNOL samples
python scripts/generate_samples.py

# 3. Process a single document (JSON to stdout)
python -m claims_agent.cli samples/fnol_01_fasttrack.txt

# 4. Batch process a directory
python -m claims_agent.cli samples/ --out outputs/

# 5. Web UI
streamlit run app.py

# 6. Tests
python -m pytest tests/""", CODE))

# ---- 10. Project layout ----
story.append(Paragraph("10. Project Layout", H1))
story.append(Preformatted(
"""claims_agent/
  ingest.py     PDF/TXT -> raw text
  extract.py    LLM extraction (Claude tool-use) + regex fallback, normalisation
  validate.py   mandatory-field + consistency checks
  route.py      deterministic routing rules engine
  agent.py      pipeline orchestrator
  cli.py        command-line interface
scripts/generate_samples.py   builds the 5 dummy FNOLs
app.py                        Streamlit UI (upload -> fields, route badge, JSON)
tests/test_routing.py         14 unit tests
README.md                     approach + run steps""", CODE))

# ---- 11. Tech ----
story.append(Paragraph("11. Tools &amp; Frameworks", H1))
story.append(table(
    [
        ["Component", "Choice", "Why"],
        [cell("Language"), cell("Python 3.9+"), cell("Assignment requirement; rich PDF/LLM ecosystem")],
        [cell("PDF text extraction"), cell("pdfplumber"), cell("Reliable layout-aware text extraction")],
        [cell("LLM extraction"), cell("OpenAI-compatible API (Groq default)"), cell("Strict JSON schema, temperature 0, provider-agnostic")],
        [cell("Fallback extraction"), cell("Regex"), cell("Offline operation without an API key")],
        [cell("UI"), cell("Streamlit"), cell("Fast to build, ideal for a demo")],
        [cell("Sample generation"), cell("reportlab"), cell("Programmatic dummy FNOL PDFs")],
        [cell("Testing"), cell("pytest"), cell("Unit tests for rules, parsing, extraction")],
    ],
    [38 * mm, 48 * mm, 74 * mm],
))

# ---- 12. Assumptions ----
story.append(Paragraph("12. Assumptions &amp; Future Improvements", H1))
story.append(Paragraph("Assumptions", H2))
story += bullets([
    "Amounts are INR; multiple currency notations are normalised.",
    "Complete claims at/above the fast-track threshold go to Standard Processing.",
    "Consistency warnings inform reviewers but do not change the route.",
])
story.append(Paragraph("Future improvements", H2))
story += bullets([
    "OCR (e.g. Tesseract) for scanned/image-only FNOL documents.",
    "Confidence scores per extracted field; low confidence routes to Manual Review.",
    "Fuzzy/semantic fraud detection beyond keyword matching.",
    "Queue integration (e.g. publish routing decisions to a message broker).",
])

doc = SimpleDocTemplate(
    str(OUT), pagesize=A4,
    leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
    title="Autonomous Insurance Claims Processing Agent — Solution Document",
    author="Abhishek Nikam",
)
OUT.parent.mkdir(exist_ok=True)
doc.build(story)
print(f"wrote {OUT}")
