"""Deterministic routing rules engine.

Precedence (highest first):
1. Fraud keywords in description      -> Investigation Flag
2. Claim type is injury               -> Specialist Queue
3. Any mandatory field missing        -> Manual Review
4. Estimated damage < 25,000          -> Fast-track
5. Otherwise                          -> Standard Processing
"""

from __future__ import annotations

FRAUD_KEYWORDS = ["fraud", "inconsistent", "staged"]
FAST_TRACK_THRESHOLD = 25_000

ROUTE_INVESTIGATION = "Investigation Flag"
ROUTE_SPECIALIST = "Specialist Queue"
ROUTE_MANUAL = "Manual Review"
ROUTE_FAST_TRACK = "Fast-track"
ROUTE_STANDARD = "Standard Processing"


def route_claim(fields: dict, missing_fields: list[str], inconsistencies: list[str] | None = None) -> tuple[str, str]:
    """Apply routing rules in precedence order. Returns (route, reasoning)."""
    inconsistencies = inconsistencies or []
    description = (fields.get("incidentInformation", {}).get("description") or "").lower()
    claim_type = (fields.get("otherFields", {}).get("claimType") or "").lower()
    damage = fields.get("assetDetails", {}).get("estimatedDamage")

    notes = ""
    if inconsistencies:
        notes = " Consistency warnings: " + " ".join(inconsistencies)

    found_keywords = [kw for kw in FRAUD_KEYWORDS if kw in description]
    if found_keywords:
        return ROUTE_INVESTIGATION, (
            f"Incident description contains potential fraud indicator(s): "
            f"{', '.join(repr(k) for k in found_keywords)}. Flagged for investigation "
            f"(overrides all other rules)." + notes
        )

    if "injury" in claim_type:
        return ROUTE_SPECIALIST, (
            f"Claim type is '{fields['otherFields']['claimType']}'. Injury claims require "
            f"specialist handling, so the claim is routed to the Specialist Queue." + notes
        )

    if missing_fields:
        return ROUTE_MANUAL, (
            f"{len(missing_fields)} mandatory field(s) missing: {', '.join(missing_fields)}. "
            f"A human must complete the file before it can proceed." + notes
        )

    if damage is not None and damage < FAST_TRACK_THRESHOLD:
        return ROUTE_FAST_TRACK, (
            f"All mandatory fields present, no fraud indicators, and estimated damage "
            f"({damage:,.0f}) is below the {FAST_TRACK_THRESHOLD:,} fast-track threshold." + notes
        )

    return ROUTE_STANDARD, (
        f"All mandatory fields present and no fraud indicators, but estimated damage "
        f"({damage:,.0f}) is at or above the {FAST_TRACK_THRESHOLD:,} fast-track threshold, "
        f"so the claim follows the standard adjuster workflow." + notes
    )
