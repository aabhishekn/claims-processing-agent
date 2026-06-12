"""Field extraction: LLM-based (Claude) with regex fallback.

The extracted field structure mirrors the assessment brief:

- policyInformation: policyNumber, policyholderName, effectiveDates
- incidentInformation: date, time, location, description
- involvedParties: claimant, thirdParties, contactDetails
- assetDetails: assetType, assetId, estimatedDamage
- otherFields: claimType, attachments, initialEstimate
"""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy

EMPTY_FIELDS: dict = {
    "policyInformation": {
        "policyNumber": None,
        "policyholderName": None,
        "effectiveDates": None,
    },
    "incidentInformation": {
        "date": None,
        "time": None,
        "location": None,
        "description": None,
    },
    "involvedParties": {
        "claimant": None,
        "thirdParties": None,
        "contactDetails": None,
    },
    "assetDetails": {
        "assetType": None,
        "assetId": None,
        "estimatedDamage": None,
    },
    "otherFields": {
        "claimType": None,
        "attachments": None,
        "initialEstimate": None,
    },
}

EXTRACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "policyInformation": {
                "type": "object",
                "properties": {
                    "policyNumber": {"type": ["string", "null"]},
                    "policyholderName": {"type": ["string", "null"]},
                    "effectiveDates": {
                        "type": ["string", "null"],
                        "description": "Policy effective date range, e.g. '2026-01-01 to 2026-12-31'",
                    },
                },
            },
            "incidentInformation": {
                "type": "object",
                "properties": {
                    "date": {"type": ["string", "null"], "description": "ISO date YYYY-MM-DD"},
                    "time": {"type": ["string", "null"]},
                    "location": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                },
            },
            "involvedParties": {
                "type": "object",
                "properties": {
                    "claimant": {"type": ["string", "null"]},
                    "thirdParties": {"type": ["string", "null"]},
                    "contactDetails": {"type": ["string", "null"]},
                },
            },
            "assetDetails": {
                "type": "object",
                "properties": {
                    "assetType": {"type": ["string", "null"]},
                    "assetId": {"type": ["string", "null"]},
                    "estimatedDamage": {
                        "type": ["number", "null"],
                        "description": "Estimated damage amount as a plain number, no currency symbols",
                    },
                },
            },
            "otherFields": {
                "type": "object",
                "properties": {
                    "claimType": {"type": ["string", "null"]},
                    "attachments": {"type": ["string", "null"]},
                    "initialEstimate": {
                        "type": ["number", "null"],
                        "description": "Initial estimate as a plain number, no currency symbols",
                    },
                },
            },
        },
        "required": [
            "policyInformation",
            "incidentInformation",
            "involvedParties",
            "assetDetails",
            "otherFields",
        ],
}

SYSTEM_PROMPT = """You are an insurance claims intake assistant. Extract FNOL (First Notice of Loss) \
fields from the document text and respond with ONLY a JSON object matching this schema (no prose, no \
markdown fences):

{schema}

Use null for any field not present in the document — never guess or invent values. Normalize dates \
to YYYY-MM-DD and amounts to plain numbers (strip currency symbols and thousands separators)."""

# Provider-agnostic: any OpenAI-compatible API works. Defaults target Groq's free tier.
DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def extract_fields(text: str) -> tuple[dict, str]:
    """Extract structured fields from raw FNOL text.

    Returns (fields, method) where method is "llm" or "regex".
    """
    if os.environ.get("LLM_API_KEY"):
        try:
            return extract_with_llm(text), "llm"
        except Exception as exc:  # noqa: BLE001 - fall back on any API failure
            print(f"[warn] LLM extraction failed ({exc}); falling back to regex.")
    return extract_with_regex(text), "regex"


def extract_with_llm(text: str) -> dict:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
    )
    response = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        temperature=0,
        max_tokens=2048,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(schema=json.dumps(EXTRACTION_SCHEMA))},
            {"role": "user", "content": f"Extract the FNOL fields from this document:\n\n{text}"},
        ],
    )
    raw = response.choices[0].message.content
    data = json.loads(_strip_code_fences(raw))
    return _merge_into_template(data)


def _strip_code_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return raw


# ---------------------------------------------------------------------------
# Regex fallback — handles labeled-field documents like "Policy Number: ABC-123"
# ---------------------------------------------------------------------------

_FIELD_PATTERNS: dict[tuple[str, str], list[str]] = {
    ("policyInformation", "policyNumber"): [r"policy\s*(?:number|no\.?|#)"],
    ("policyInformation", "policyholderName"): [r"policy\s*holder(?:\s*name)?", r"name\s+of\s+insured", r"insured\s+name"],
    ("policyInformation", "effectiveDates"): [r"effective\s*dates?", r"policy\s*period"],
    ("incidentInformation", "date"): [r"(?:incident|loss|accident)\s*date", r"date\s+of\s+(?:incident|loss|accident)"],
    ("incidentInformation", "time"): [r"(?:incident|loss|accident)\s*time", r"time\s+of\s+(?:incident|loss|accident)"],
    ("incidentInformation", "location"): [r"(?:incident\s*)?location(?:\s+of\s+loss)?"],
    ("incidentInformation", "description"): [r"description(?:\s+of\s+(?:incident|loss|accident))?"],
    ("involvedParties", "claimant"): [r"claimant(?:\s*name)?"],
    ("involvedParties", "thirdParties"): [r"third\s*part(?:y|ies)"],
    ("involvedParties", "contactDetails"): [r"contact\s*(?:details?|info(?:rmation)?|number|phone)?", r"phone"],
    ("assetDetails", "assetType"): [r"asset\s*type", r"vehicle\s*type"],
    ("assetDetails", "assetId"): [r"asset\s*id", r"v\.?i\.?n\.?", r"registration\s*(?:number|no\.?)"],
    ("assetDetails", "estimatedDamage"): [r"estimated?\s*damage(?:\s*amount)?", r"estimate\s*amount"],
    ("otherFields", "claimType"): [r"claim\s*type", r"type\s+of\s+claim"],
    ("otherFields", "attachments"): [r"attachments?"],
    ("otherFields", "initialEstimate"): [r"initial\s*estimate"],
}

_NUMERIC_FIELDS = {
    ("assetDetails", "estimatedDamage"),
    ("otherFields", "initialEstimate"),
}

_MISSING_MARKERS = {"", "n/a", "na", "none", "not provided", "not available", "-", "—", "null", "tbd"}


def extract_with_regex(text: str) -> dict:
    fields = deepcopy(EMPTY_FIELDS)
    last_match: tuple[str, str] | None = None  # for continuation lines (PDF wrapping)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if ":" not in line:
            # Unlabeled non-empty line right after a matched text field = wrapped continuation.
            if line and last_match and last_match not in _NUMERIC_FIELDS:
                section, key = last_match
                if isinstance(fields[section][key], str):
                    fields[section][key] += " " + line
            else:
                last_match = None
            continue
        label, _, value = line.partition(":")
        label_norm = label.strip().lower()
        value = value.strip()
        last_match = None
        for (section, key), patterns in _FIELD_PATTERNS.items():
            if fields[section][key] is not None:
                continue
            if any(re.fullmatch(p, label_norm) for p in patterns):
                fields[section][key] = _clean_value(value, numeric=(section, key) in _NUMERIC_FIELDS)
                if fields[section][key] is not None:
                    last_match = (section, key)
                break
    return fields


def _clean_value(value: str, numeric: bool = False):
    if value.strip().lower() in _MISSING_MARKERS:
        return None
    if numeric:
        return parse_amount(value)
    return value.strip()


def parse_amount(value) -> float | None:
    """Parse currency strings like '₹18,000', 'Rs. 18000', 'INR 25,000.50' to a number."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"(?i)(rs\.?|inr|₹|\$|,|\s)", "", str(value))
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def _merge_into_template(data: dict) -> dict:
    """Fit arbitrary LLM output into the canonical field template."""
    fields = deepcopy(EMPTY_FIELDS)
    for section, keys in fields.items():
        incoming = data.get(section) or {}
        for key in keys:
            value = incoming.get(key)
            if isinstance(value, str) and value.strip().lower() in _MISSING_MARKERS:
                value = None
            if (section, key) in _NUMERIC_FIELDS:
                value = parse_amount(value)
            elif isinstance(value, list):
                value = "; ".join(str(v) for v in value) or None
            fields[section][key] = value
    return fields


if __name__ == "__main__":  # quick manual check
    sample = "Policy Number: POL-123\nEstimated Damage: ₹18,000\n"
    print(json.dumps(extract_with_regex(sample), indent=2))
