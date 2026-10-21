import csv
from datetime import date

import pytest

from azul_crm.application.features import FeatureBuilder
from azul_crm.bootstrap import build_container
from azul_crm.domain.scoring import RuleSegmenter, ScoringPolicy, ValueScorer
from azul_crm.infrastructure.gold_validation import validate_gold
from azul_crm.infrastructure.settings import Settings


def test_gold_contract(root):
    assert validate_gold(root / "data/gold")["customers"] == 12


@pytest.mark.parametrize(
    "filename,field,value",
    [
        ("features.csv", "spend", "999999"),
        ("features.csv", "frequency", "1.5"),
        ("customers.csv", "is_synthetic", "maybe"),
        ("trips.csv", "customer_id", "missing"),
        ("trips.csv", "flight_date", "2026-10-01"),
    ],
)
def test_invalid_gold_rejected(root, filename, field, value):
    path = root / "data/gold" / filename
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        names, rows = reader.fieldnames, list(reader)
    rows[0][field] = value
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        validate_gold(root / "data/gold")


def test_no_history_and_thresholds():
    features = FeatureBuilder().build("empty", [], date(2025, 10, 1), date(2026, 9, 30))
    assert features.recency_days == 365
    assert ValueScorer(ScoringPolicy()).score(features) == 0
    assert RuleSegmenter(ScoringPolicy()).classify(70, 0.6) == "Alto Valor em Risco"


def test_window_overlap_rejected(root):
    path = root / "config/settings.toml"
    path.write_text(
        path.read_text().replace("outcome_start = 2026-10-01", "outcome_start = 2026-09-30")
    )
    with pytest.raises(ValueError):
        Settings(root).windows()


def test_changed_window_requires_regeneration(root):
    path = root / "config/settings.toml"
    path.write_text(path.read_text().replace("2025-10-01", "2025-09-01"))
    with pytest.raises(ValueError):
        build_container(Settings(root))


def test_metadata_exposes_assumptions(client):
    metadata = client.get("/api/v1/metadata").json()
    assert metadata["scoring_policy"]["high_value_threshold"] == 70
    assert metadata["churn_label_status"] == "planned_not_generated"
