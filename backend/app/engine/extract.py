"""raw statement bytes -> a raw dataframe, columns exactly as the file used
them. canonical shaping happens in engine.normalize."""

import io
import re

import pandas as pd
import pdfplumber


class ExtractError(Exception):
    """the file could not be read at all."""


def extract_dataframe(data: bytes, filename: str = "") -> pd.DataFrame:
    name = (filename or "").lower()
    if name.endswith(".pdf") or data[:5] == b"%PDF-":
        return _from_pdf(data)
    if name.endswith(".csv") or b"," in data[:2048]:
        return _from_csv(data)
    raise ExtractError(f"Unsupported file type: {filename or 'unknown'}")


def _from_csv(data: bytes) -> pd.DataFrame:
    last_error = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
        except Exception as exc:
            raise ExtractError(f"Could not read CSV: {exc}") from exc
    raise ExtractError(f"Could not decode CSV: {last_error}")


def _from_pdf(data: bytes) -> pd.DataFrame:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        # the first extractable table wins; merging per-page layouts is the
        # upgrade path once multi-page inputs exist.
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                frame = _table_to_frame(table)
                if frame is not None:
                    return frame
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return _from_text(text)


def _table_to_frame(table: list) -> pd.DataFrame | None:
    rows = [[(cell or "").strip() for cell in row] for row in table if row]
    if len(rows) < 2:
        return None
    header, *body = rows
    if not any(header):
        return None
    columns = [name or f"col{i}" for i, name in enumerate(header)]
    frame = pd.DataFrame(body, columns=columns)
    return frame if len(frame) else None


def _from_text(text: str) -> pd.DataFrame:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ExtractError("No text found in PDF")

    # comma-separated text (a csv dropped into a pdf) parses as-is.
    if sum("," in line for line in lines) >= max(2, len(lines) // 2):
        return pd.read_csv(io.StringIO("\n".join(lines)))

    # whitespace-aligned table. a header row is required — headerless text
    # needs positional mapping (not built).
    if "date" not in lines[0].lower():
        raise ExtractError("PDF text has no header row")
    split = [re.split(r"\s{2,}", line) for line in lines]
    width = max(len(row) for row in split)
    rows = [row + [""] * (width - len(row)) for row in split]
    return pd.DataFrame(rows[1:], columns=[name.strip() for name in rows[0]])
