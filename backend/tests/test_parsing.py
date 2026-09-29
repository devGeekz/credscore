from pathlib import Path

import pandas as pd
import pytest

from app.engine.extract import extract_dataframe
from app.engine.heuristics import classify_flows
from app.engine.normalize import CANONICAL, normalize
from app.engine.scoring_model import score

FIXTURE = Path(__file__).parent / "fixtures" / "momo_sample.csv"


def _flows() -> pd.DataFrame:
    raw = extract_dataframe(FIXTURE.read_bytes(), "momo_sample.csv")
    return classify_flows(normalize(raw))


@pytest.fixture(scope="module")
def flows() -> pd.DataFrame:
    return _flows()


def test_extract_normalize_produces_canonical_columns(flows):
    assert list(flows.columns) == CANONICAL + ["flow_class"]
    assert not flows["ts"].isna().any()
    assert (flows["amount"] > 0).all()
    assert set(flows["direction"]) <= {"in", "out"}
    assert flows["ts"].is_monotonic_increasing


def test_salary_and_self_transfer_are_not_revenue(flows):
    salary = flows[flows["reference"].str.contains("salary", case=False)]
    sweep = flows[flows["reference"].str.contains("self transfer", case=False)]
    assert not salary.empty and (salary["flow_class"] == "personal").all()
    assert not sweep.empty and (sweep["flow_class"] == "internal").all()

    inflows = flows.loc[flows["direction"] == "in", "amount"].sum()
    business = flows.loc[flows["flow_class"] == "business", "amount"].sum()
    assert business < inflows
    assert salary["amount"].sum() + sweep["amount"].sum() == pytest.approx(inflows - business)


def test_outflow_classification(flows):
    supplier = flows[flows["flow_class"] == "supplier"]
    cash_out = flows[flows["flow_class"] == "cash_out"]
    assert set(supplier["counterparty"]) == {"UPSA SUPPLIERS"}
    assert len(supplier) == 4
    assert set(cash_out["counterparty"]) == {"MTN AGENT 1234"}
    # one-off payment with a neutral type stays unclassified, not a supplier
    assert (flows[flows["counterparty"] == "VODA PERFECT"]["flow_class"] == "other").all()
    assert (flows[flows["counterparty"] == "VODA PERFECT"]["direction"] == "out").all()


def test_metrics_match_their_definitions(flows):
    report = score(flows)
    business = flows[flows["flow_class"] == "business"]
    suppliers = flows[flows["flow_class"] == "supplier"]
    inflow_total = business["amount"].sum()

    assert report["net_verified_revenue"] == pytest.approx(inflow_total, abs=0.01)

    top3 = business.groupby("counterparty")["amount"].sum().nlargest(3).sum()
    assert report["counterparty_concentration"] == pytest.approx(
        top3 / inflow_total * 100, abs=0.01
    )
    assert report["expense_ratio"] == pytest.approx(
        suppliers["amount"].sum() / inflow_total * 100, abs=0.01
    )

    balances = flows["balance"].dropna()
    assert report["average_daily_balance"] is not None
    assert balances.min() <= report["average_daily_balance"] <= balances.max()

    assert report["risk_tag"] in {"strong", "moderate", "high_risk"}
    assert report["suggested_credit_limit"] >= 0
    assert report["raw_payload"]["daily_revenue"]


def test_healthy_fixture_scores_strong(flows):
    assert score(flows)["risk_tag"] == "strong"


def test_single_lump_sum_is_high_risk():
    flows = pd.DataFrame(
        {
            "ts": pd.to_datetime(["2026-09-01"]),
            "direction": ["in"],
            "amount": [1000.0],
            "counterparty": ["ONE PAYER"],
            "reference": [""],
            "balance": [float("nan")],
            "flow_class": ["business"],
        }
    )
    report = score(flows)
    assert report["risk_tag"] == "high_risk"
    assert report["counterparty_concentration"] == 100.0
    assert report["cash_flow_consistency"] == 0.0
    assert report["average_daily_balance"] is None
    assert report["suggested_credit_limit"] == 0.0


def test_extract_rejects_garbage():
    from app.engine.extract import ExtractError

    with pytest.raises(ExtractError):
        extract_dataframe(b"\x00\x01\x02 not a statement", "mystery.bin")
