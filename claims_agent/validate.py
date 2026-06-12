"""Validation: mandatory-field checks and consistency checks."""

from __future__ import annotations

import re
from datetime import date, datetime

# (section, key) pairs that must be present for straight-through processing.
MANDATORY_FIELDS: list[tuple[str, str]] = [
    ("policyInformation", "policyNumber"),
    ("policyInformation", "policyholderName"),
    ("incidentInformation", "date"),
    ("incidentInformation", "location"),
    ("incidentInformation", "description"),
    ("involvedParties", "claimant"),
    ("assetDetails", "assetType"),
    ("assetDetails", "estimatedDamage"),
    ("otherFields", "claimType"),
]


def find_missing_fields(fields: dict) -> list[str]:
    """Return dotted paths of mandatory fields that are empty/null."""
    missing = []
    for section, key in MANDATORY_FIELDS:
        value = fields.get(section, {}).get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(f"{section}.{key}")
    return missing


def find_inconsistencies(fields: dict) -> list[str]:
    """Return human-readable descriptions of internally inconsistent data."""
    issues: list[str] = []

    incident = _parse_date(fields.get("incidentInformation", {}).get("date"))
    effective = fields.get("policyInformation", {}).get("effectiveDates")
    if incident and effective:
        start, end = _parse_date_range(effective)
        if start and end and not (start <= incident <= end):
            issues.append(
                f"Incident date {incident.isoformat()} falls outside policy effective dates ({effective})."
            )

    damage = fields.get("assetDetails", {}).get("estimatedDamage")
    estimate = fields.get("otherFields", {}).get("initialEstimate")
    if damage is not None and estimate is not None and estimate > 0:
        if abs(damage - estimate) / max(damage, estimate) > 0.5:
            issues.append(
                f"Estimated damage ({damage:,.0f}) and initial estimate ({estimate:,.0f}) differ by more than 50%."
            )

    if incident and incident > date.today():
        issues.append(f"Incident date {incident.isoformat()} is in the future.")

    return issues


_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%B %d, %Y"]


def _parse_date(value) -> date | None:
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_date_range(value: str) -> tuple[date | None, date | None]:
    # Hyphen separator requires surrounding spaces so ISO dates (2026-01-01) stay intact.
    parts = re.split(r"\s+(?:to|through)\s+|\s+[-–]\s+", value.strip(), maxsplit=1)
    if len(parts) == 2:
        return _parse_date(parts[0]), _parse_date(parts[1])
    return None, None
