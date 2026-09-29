"""raw statement rows -> canonical transactions.

canonical columns: ts, direction, amount, counterparty, reference, balance.

column matching is by hint ranking (exact beats substring), which covers
mtn momo ("Date/Time/Type/Amount/Balance/Counter Party/Reason") and the
telecel/airteltigo variants without per-telco parsers.
"""

import re

import pandas as pd

CANONICAL = ["ts", "direction", "amount", "counterparty", "reference", "balance"]

_HINTS = {
    "date": ("transaction date", "value date", "date"),
    "time": ("time",),
    "amount": ("amount",),
    "balance": ("balance",),
    "direction": ("transaction type", "dr/cr", "cr/dr", "type", "direction"),
    "counterparty": (
        "counter party", "counterparty", "party", "customer name", "customer",
        "payer", "payee", "name", "from", "to",
    ),
    "reference": (
        "reference", "reason", "narration", "narrative", "description",
        "details", "remarks",
    ),
}

_CREDIT_WORDS = r"\b(?:credit|receiv\w*|deposit|top[ -]?up|paid in)\b"
_DEBIT_WORDS = r"\b(?:debit|withdraw\w*|send|sent|out|payment|paid out)\b"


class NormalizeError(Exception):
    """rows were read but do not look like transactions."""


def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        raise NormalizeError("No rows found")

    df = raw.copy()
    df.columns = [re.sub(r"\s+", " ", str(c)).strip().lower() for c in df.columns]
    df = df.loc[:, ~pd.Index(df.columns).duplicated()]

    date_col = _pick(df.columns, _HINTS["date"])
    amount_col = _pick(df.columns, _HINTS["amount"])
    if date_col is None or amount_col is None:
        raise NormalizeError(f"Missing date/amount columns (found: {list(df.columns)})")

    time_col = _pick(df.columns, _HINTS["time"])
    balance_col = _pick(df.columns, _HINTS["balance"])
    direction_col = _pick(df.columns, _HINTS["direction"])
    counterparty_col = _pick(df.columns, _HINTS["counterparty"])
    reference_col = _pick(df.columns, _HINTS["reference"])

    amounts = _numeric(df[amount_col])
    balances = _numeric(df[balance_col]) if balance_col else None
    ts = _timestamps(df, date_col, time_col)
    direction = _direction(df, direction_col, amounts, balances)

    # a statement's counterparty is often the only reference it has.
    counterparty = (
        df[counterparty_col].fillna("").astype(str).str.strip()
        if counterparty_col else pd.Series("", index=df.index)
    )
    if not counterparty_col and reference_col:
        counterparty = df[reference_col].fillna("").astype(str).str.strip()
    reference = (
        df[reference_col].fillna("").astype(str).str.strip()
        if reference_col else pd.Series("", index=df.index)
    )

    out = pd.DataFrame(
        {
            "ts": ts,
            "direction": direction,
            "amount": amounts.abs(),
            "counterparty": counterparty,
            "reference": reference,
            "balance": balances if balances is not None else float("nan"),
        }
    )
    # summary/footer rows have no parsable date or amount — drop them.
    out = out.dropna(subset=["ts", "amount"])
    out = out[out["amount"] > 0]
    if out.empty:
        raise NormalizeError("No transactions found")

    return out.sort_values("ts").reset_index(drop=True)[CANONICAL]


def _pick(columns, hints) -> str | None:
    best, best_key = None, None
    for rank, hint in enumerate(hints):
        for col in columns:
            if col == hint:
                key = (0, rank, -len(hint))
            elif hint in col:
                key = (1, rank, -len(hint))
            else:
                continue
            if best_key is None or key < best_key:
                best, best_key = col, key
    return best


def _numeric(series: pd.Series) -> pd.Series:
    def one(value) -> float:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return float("nan")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        text = str(value).strip()
        parenthesised = text.startswith("(") and text.endswith(")")
        digits = re.sub(r"[^0-9.\-]", "", text)
        if digits in ("", "-", ".", "-.", "--"):
            return float("nan")
        try:
            parsed = float(digits)
        except ValueError:
            return float("nan")
        return -abs(parsed) if parenthesised else parsed

    return series.map(one).astype(float)


def _timestamps(df: pd.DataFrame, date_col: str, time_col: str | None) -> pd.Series:
    combined = df[date_col].astype(str).str.strip()
    if time_col:
        time_part = df[time_col].astype(str).str.strip().replace({"nan": "", "NaT": ""})
        combined = combined + " " + time_part
    combined = combined.str.replace(r"\s+", " ", regex=True).str.strip()

        # dates are dd/mm/yyyy; fall back to us ordering if that
        # fails to parse most rows.
    ts = pd.to_datetime(combined, errors="coerce", dayfirst=True, format="mixed")
    if ts.isna().mean() > 0.5:
        ts = pd.to_datetime(combined, errors="coerce", dayfirst=False, format="mixed")
    if ts.isna().mean() > 0.5:
        raise NormalizeError(f"Could not parse dates in '{date_col}'")
    return ts


def _direction(
    df: pd.DataFrame,
    direction_col: str | None,
    amounts: pd.Series,
    balances: pd.Series | None,
) -> pd.Series:
    direction = pd.Series(pd.NA, index=df.index, dtype="object")

    if direction_col:
        values = df[direction_col].fillna("").astype(str).str.lower()
        direction.loc[values.str.contains(_CREDIT_WORDS, regex=True)] = "in"
        direction.loc[values.str.contains(_DEBIT_WORDS, regex=True)] = "out"
    elif balances is not None and not (amounts < 0).any():
        # no type column and all-positive amounts: balance going down = outflow.
        direction.loc[balances.diff() < 0] = "out"

    direction.loc[amounts < 0] = "out"  # sign is authoritative
    direction.loc[amounts > 0] = direction.loc[amounts > 0].fillna("in")
    return direction.fillna("in")
