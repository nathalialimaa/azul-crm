import pytest

from azul_crm.application.explanations import exact_shapley


def test_linear_attribution_recovers_known_coefficients_and_dummy():
    result = exact_shapley(lambda x: 4 + 2 * x[0] - 3 * x[1], [5, 8, 99], [1, 2, 0])
    assert result["contributions"] == pytest.approx([8, -18, 0])
    assert result["base_value"] == 0
    assert result["additivity_error"] < 1e-12


def test_interaction_is_shared_symmetrically():
    result = exact_shapley(lambda x: x[0] * x[1], [2, 2], [0, 0])
    assert result["contributions"] == pytest.approx([2, 2])
    assert result["prediction"] == 4


def test_customer_api_explains_actual_active_predictions(client):
    cid = client.get("/api/v1/customers").json()["items"][0]["customer_id"]
    scores = client.get(f"/api/v1/customers/{cid}/scores").json()
    response = client.get(f"/api/v1/customers/{cid}/explanation")
    assert response.status_code == 200
    data = response.json()
    for target in ("value_score", "churn_risk"):
        result = data["outputs"][target]
        assert result["prediction"] == scores[target]
        assert result["additivity_error"] < 1e-10
        assert len(result["features"]) == 4
    assert client.get("/api/v1/customers/unknown/explanation").status_code == 404
