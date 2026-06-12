"""Unit tests for routing rules, validation, and currency parsing."""

from copy import deepcopy

from claims_agent.extract import EMPTY_FIELDS, extract_with_regex, parse_amount
from claims_agent.route import (
    ROUTE_FAST_TRACK,
    ROUTE_INVESTIGATION,
    ROUTE_MANUAL,
    ROUTE_SPECIALIST,
    ROUTE_STANDARD,
    route_claim,
)
from claims_agent.validate import find_inconsistencies, find_missing_fields


def complete_fields(**overrides) -> dict:
    """A fully-populated claim; overrides use 'section.key' = value."""
    fields = deepcopy(EMPTY_FIELDS)
    fields["policyInformation"].update(
        policyNumber="POL-1", policyholderName="Test User", effectiveDates="2026-01-01 to 2026-12-31"
    )
    fields["incidentInformation"].update(
        date="2026-06-01", time="10:00", location="Mumbai", description="Minor scratch on bumper."
    )
    fields["involvedParties"].update(claimant="Test User", thirdParties="None", contactDetails="+91 9000000000")
    fields["assetDetails"].update(assetType="Private Car", assetId="MH01-AA-1111", estimatedDamage=10_000.0)
    fields["otherFields"].update(claimType="Own Damage", attachments="photos.zip", initialEstimate=9_500.0)
    for dotted, value in overrides.items():
        section, key = dotted.split(".")
        fields[section][key] = value
    return fields


# ---- routing rules -------------------------------------------------------

def test_fast_track_when_complete_and_below_threshold():
    fields = complete_fields()
    route, reasoning = route_claim(fields, find_missing_fields(fields))
    assert route == ROUTE_FAST_TRACK
    assert "25,000" in reasoning


def test_manual_review_when_mandatory_field_missing():
    fields = complete_fields(**{"policyInformation.policyNumber": None})
    missing = find_missing_fields(fields)
    assert "policyInformation.policyNumber" in missing
    route, reasoning = route_claim(fields, missing)
    assert route == ROUTE_MANUAL
    assert "policyInformation.policyNumber" in reasoning


def test_investigation_flag_on_fraud_keyword():
    fields = complete_fields(
        **{"incidentInformation.description": "Witness says the accident was STAGED for insurance."}
    )
    route, reasoning = route_claim(fields, find_missing_fields(fields))
    assert route == ROUTE_INVESTIGATION
    assert "staged" in reasoning.lower()


def test_specialist_queue_for_injury():
    fields = complete_fields(**{"otherFields.claimType": "Injury"})
    route, _ = route_claim(fields, find_missing_fields(fields))
    assert route == ROUTE_SPECIALIST


def test_standard_processing_when_damage_at_or_above_threshold():
    fields = complete_fields(**{"assetDetails.estimatedDamage": 350_000.0})
    route, _ = route_claim(fields, find_missing_fields(fields))
    assert route == ROUTE_STANDARD


# ---- precedence ----------------------------------------------------------

def test_fraud_beats_injury_and_missing():
    fields = complete_fields(
        **{
            "incidentInformation.description": "Damage pattern looks inconsistent with the report.",
            "otherFields.claimType": "Injury",
            "policyInformation.policyNumber": None,
        }
    )
    route, _ = route_claim(fields, find_missing_fields(fields))
    assert route == ROUTE_INVESTIGATION


def test_injury_beats_missing_fields():
    fields = complete_fields(
        **{"otherFields.claimType": "Injury", "assetDetails.estimatedDamage": None}
    )
    route, _ = route_claim(fields, find_missing_fields(fields))
    assert route == ROUTE_SPECIALIST


def test_missing_beats_fast_track():
    fields = complete_fields(**{"involvedParties.claimant": None})
    route, _ = route_claim(fields, find_missing_fields(fields))
    assert route == ROUTE_MANUAL


# ---- currency parsing ----------------------------------------------------

def test_parse_amount_variants():
    assert parse_amount("Rs. 18,000") == 18000.0
    assert parse_amount("₹2,80,000") == 280000.0
    assert parse_amount("INR 25000.50") == 25000.5
    assert parse_amount(12000) == 12000.0
    assert parse_amount("") is None
    assert parse_amount(None) is None


# ---- regex extraction ----------------------------------------------------

def test_regex_extraction_labeled_fields():
    text = (
        "Policy Number: POL-9\n"
        "Policyholder Name: A B\n"
        "Incident Date: 2026-06-01\n"
        "Estimated Damage: Rs. 18,000\n"
        "Claim Type: Own Damage\n"
    )
    fields = extract_with_regex(text)
    assert fields["policyInformation"]["policyNumber"] == "POL-9"
    assert fields["assetDetails"]["estimatedDamage"] == 18000.0
    assert fields["otherFields"]["claimType"] == "Own Damage"


def test_regex_extraction_continuation_lines():
    text = (
        "Description: The car was hit and the\n"
        "damage pattern appears inconsistent with the report.\n"
        "Claim Type: Own Damage\n"
    )
    fields = extract_with_regex(text)
    assert "inconsistent" in fields["incidentInformation"]["description"]
    assert fields["otherFields"]["claimType"] == "Own Damage"


def test_empty_value_treated_as_missing():
    fields = extract_with_regex("Policy Number:\nClaim Type: Own Damage\n")
    assert fields["policyInformation"]["policyNumber"] is None


# ---- consistency checks --------------------------------------------------

def test_incident_outside_policy_period_flagged():
    fields = complete_fields(**{"incidentInformation.date": "2027-06-01"})
    issues = find_inconsistencies(fields)
    assert any("outside policy effective dates" in i for i in issues)


def test_estimate_mismatch_flagged():
    fields = complete_fields(**{"otherFields.initialEstimate": 1_000.0})
    issues = find_inconsistencies(fields)
    assert any("differ by more than 50%" in i for i in issues)
