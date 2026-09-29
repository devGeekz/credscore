"""velocity & frequency heuristics: separating genuine business
revenue from personal transfers, internal sweeps, and cash-outs.

keyword lists + two numeric rules are the whole model. they are
tuning knobs, not ml — iterate them against real statements rather than
replacing them with a trained classifier until there's labelled data.
"""

import re

import pandas as pd

PERSONAL_KEYWORDS = (
    "salary", "payroll", "allowance", "stipend", "remittance", "gift",
    "family", "personal",
)
INTERNAL_KEYWORDS = (
    "own wallet", "self", "wallet to wallet", "reversal", "refund",
    "internal", "sweep",
)
CASH_OUT_KEYWORDS = (
    "withdrawal", "cash out", "cashout", "to bank", "bank transfer",
    "self transfer",
)

RARE_PARTNER_MAX = 2        # counterparty seen this often AND
OUTLIER_MULTIPLE = 5.0      # this much above the median inflow = salary/remittance
SUPPLIER_MIN_OUTFLOWS = 3   # this many outbound payments = recurring supplier


def classify_flows(df: pd.DataFrame) -> pd.DataFrame:
    """adds a `flow_class` column: business | personal | internal |
    supplier | cash_out | other."""
    df = df.copy()
    text = (
        df["counterparty"].fillna("") + " " + df["reference"].fillna("")
    ).str.lower()

    is_in = df["direction"] == "in"
    is_out = ~is_in

    personal = is_in & _matches(text, PERSONAL_KEYWORDS)
    internal = is_in & ~personal & _matches(text, INTERNAL_KEYWORDS)
    cash_out = is_out & _matches(text, CASH_OUT_KEYWORDS)

    # salary/remittance pattern: a rarely-seen counterparty paying an
    # outlier amount (personal signal).
    rare_outlier = pd.Series(False, index=df.index)
    candidate = df[is_in & ~personal & ~internal]
    if len(candidate):
        counts = candidate.groupby("counterparty")["amount"].transform("count")
        median = candidate["amount"].median()
        if median and median > 0:
            rare_outlier.loc[candidate.index] = (
                (counts <= RARE_PARTNER_MAX)
                & (candidate["amount"] >= OUTLIER_MULTIPLE * median)
            )

    # recurring outbound counterparty = supplier/cogs, not one-off spending.
    supplier = pd.Series(False, index=df.index)
    outflows = df[is_out & ~cash_out]
    if len(outflows):
        counts = outflows.groupby("counterparty")["amount"].transform("count")
        supplier.loc[outflows.index] = counts >= SUPPLIER_MIN_OUTFLOWS

    df["flow_class"] = "other"
    df.loc[is_in, "flow_class"] = "business"
    df.loc[internal, "flow_class"] = "internal"
    df.loc[personal | rare_outlier, "flow_class"] = "personal"
    df.loc[cash_out, "flow_class"] = "cash_out"
    df.loc[supplier, "flow_class"] = "supplier"
    return df


def _matches(text: pd.Series, keywords) -> pd.Series:
    mask = pd.Series(False, index=text.index)
    for keyword in keywords:
        mask |= text.str.contains(rf"\b{re.escape(keyword)}\b", regex=True, na=False)
    return mask
