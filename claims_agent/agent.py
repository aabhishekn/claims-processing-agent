"""Pipeline orchestrator: ingest -> extract -> validate -> route -> JSON result."""

from __future__ import annotations

from pathlib import Path

from .extract import extract_fields
from .ingest import load_document
from .route import route_claim
from .validate import find_inconsistencies, find_missing_fields


def process_document(path: str | Path) -> dict:
    """Process a single FNOL document and return the result JSON structure."""
    text = load_document(path)
    fields, method = extract_fields(text)
    missing = find_missing_fields(fields)
    inconsistencies = find_inconsistencies(fields)
    route, reasoning = route_claim(fields, missing, inconsistencies)

    return {
        "extractedFields": fields,
        "missingFields": missing,
        "recommendedRoute": route,
        "reasoning": reasoning,
        "meta": {
            "sourceFile": str(path),
            "extractionMethod": method,
            "inconsistencies": inconsistencies,
        },
    }


def process_text(text: str, source: str = "<text>") -> dict:
    """Process raw FNOL text (used by the Streamlit app for uploads)."""
    fields, method = extract_fields(text)
    missing = find_missing_fields(fields)
    inconsistencies = find_inconsistencies(fields)
    route, reasoning = route_claim(fields, missing, inconsistencies)

    return {
        "extractedFields": fields,
        "missingFields": missing,
        "recommendedRoute": route,
        "reasoning": reasoning,
        "meta": {
            "sourceFile": source,
            "extractionMethod": method,
            "inconsistencies": inconsistencies,
        },
    }
