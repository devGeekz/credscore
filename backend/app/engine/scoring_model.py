"""scoring model: the five underwriting metrics plus a risk tag
and a suggested credit limit.

every threshold lives in THRESHOLDS — tune there, never inline."""

import pandas as pd

THRESHOLDS = {
    # risk tag
    "consistency_strong": 50.0,        # cash-flow consistency >= for 'strong'
    "consistency_high_risk": 25.0,     # ...< for 'high_risk'
    "concentration_strong": 60.0,      # top-3 payer share <= for 'strong'
    "concentration_high_risk": 85.0,   # ...> for 'high_risk'
    "expense_ratio_strong": 85.0,      # supplier outflow share <= for 'strong'
    # suggested limit
    "limit_ratio": 0.25,               # share of average monthly net revenue
    # consistency and the suggested limit need this many active days
    # before they mean anything
    "min_consistency_days": 2,
}


def score(flows: pd.DataFrame) -> dict:
    business = flows[flows["flow_class"] == "business"]
    suppliers = flows[flows["flow_class"] == "supplier"]
    inflow_total = float(business["amount"].sum())
    outflow_supplier = float(suppliers["amount"].sum())

    start, end = flows["ts"].min(), flows["ts"].max()
    period_days = max((end - start).days + 1, 1)
    monthly_net = inflow_total / (period_days / 30.44)

    consistency = _consistency(business)
    expense_ratio = (outflow_supplier / inflow_total * 100) if inflow_total > 0 else 0.0
    concentration = _concentration(business, inflow_total)
    adb = _average_daily_balance(flows)
    active_days = int(business["ts"].dt.date.nunique())

    risk_tag = _risk_tag(consistency, concentration, expense_ratio, inflow_total)
    # one day of activity is a lump sum, not a revenue stream — no limit.
    suggested_limit = (
        round(max(monthly_net, 0) * THRESHOLDS["limit_ratio"], 2)
        if active_days >= THRESHOLDS["min_consistency_days"]
        else 0.0
    )

    return {
        "net_verified_revenue": round(inflow_total, 2),
        "cash_flow_consistency": round(consistency, 2),
        "average_daily_balance": round(adb, 2) if adb is not None else None,
        "expense_ratio": round(expense_ratio, 2),
        "counterparty_concentration": round(concentration, 2),
        "risk_tag": risk_tag,
        "suggested_credit_limit": suggested_limit,
        "raw_payload": {
            "period": {
                "start": start.date().isoformat(),
                "end": end.date().isoformat(),
                "days": period_days,
            },
            "monthly_average_revenue": round(monthly_net, 2),
            "active_days": active_days,
            "transaction_count": int(len(flows)),
            "business_transaction_count": int(len(business)),
            "excluded_amounts": {
                "personal": round(float(flows.loc[flows["flow_class"] == "personal", "amount"].sum()), 2),
                "internal": round(float(flows.loc[flows["flow_class"] == "internal", "amount"].sum()), 2),
                "cash_out": round(float(flows.loc[flows["flow_class"] == "cash_out", "amount"].sum()), 2),
            },
            "top_counterparties": [
                {"name": name, "amount": round(float(amount), 2)}
                for name, amount in (
                    business.groupby("counterparty")["amount"].sum().nlargest(5).items()
                )
            ],
            # chart data for the report view
            "daily_revenue": [
                [day.isoformat(), round(float(amount), 2)]
                for day, amount in business.groupby(business["ts"].dt.date)["amount"].sum().items()
            ],
            "thresholds_used": THRESHOLDS,
        },
    }


def _consistency(business: pd.DataFrame) -> float:
    """100 × (1 − coefficient of variation) over daily business revenue."""
    if business.empty:
        return 0.0
    daily = business.groupby(business["ts"].dt.date)["amount"].sum()
    if len(daily) < THRESHOLDS["min_consistency_days"] or daily.mean() == 0:
        return 0.0
    cv = daily.std(ddof=1) / daily.mean()
    return max(0.0, min(100.0, (1 - cv) * 100))


def _concentration(business: pd.DataFrame, inflow_total: float) -> float:
    if business.empty or inflow_total <= 0:
        return 0.0
    by_payer = business.groupby("counterparty")["amount"].sum().nlargest(3)
    return float(by_payer.sum() / inflow_total * 100)


def _average_daily_balance(flows: pd.DataFrame) -> float | None:
    """lowest 30-day rolling end-of-day balance (liquidity cushion)."""
    with_balance = flows.dropna(subset=["balance"])
    if with_balance.empty:
        return None  # statement had no balance column
    daily = with_balance.groupby(with_balance["ts"].dt.date)["balance"].last()
    return float(daily.rolling(30, min_periods=1).min().min())


def _risk_tag(
    consistency: float, concentration: float, expense_ratio: float, inflow_total: float
) -> str:
    if inflow_total <= 0:
        return "high_risk"
    if (
        consistency < THRESHOLDS["consistency_high_risk"]
        or concentration > THRESHOLDS["concentration_high_risk"]
    ):
        return "high_risk"
    if (
        consistency >= THRESHOLDS["consistency_strong"]
        and concentration <= THRESHOLDS["concentration_strong"]
        and expense_ratio <= THRESHOLDS["expense_ratio_strong"]
    ):
        return "strong"
    return "moderate"
