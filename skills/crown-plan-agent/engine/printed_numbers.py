"""Validate bounded printed amounts and scale ratios without numeric guessing.

Separators are removed only after the entire numeral has passed its grammar.
These helpers interpret native text; source selection and completeness remain
the caller's responsibility.
"""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal


_NUMBER = re.compile(
    r"(?P<integer>0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+|"
    r"[1-9][0-9]{0,2}(?: [0-9]{3})+)(?P<fraction>\.[0-9]{1,12})?")
_UNITS = {"ha": r"HA", "m": r"M", "m2": r"M(?:2|\^2)"}
_RATIO_START = re.compile(r"(?<![\w.:])([+-]?[0-9][A-Z0-9_.,+-]*)\s*:\s*")
# Letters, dots, commas and further colons belong to the candidate, so an
# unsupported continuation cannot expose a shorter, apparently valid prefix.
_DENOMINATOR = re.compile(r"[^\s;/()\[\]{}]+(?:\s+(?=[0-9.,+-])[^\s;/()\[\]{}]+)*")
_NUMERIC_CONTINUATION = re.compile(r"\s*(?:[:/()\[\]{}]\s*)+(?=[+-]?(?:[0-9]|\.[0-9]))")


def _normal(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split()).upper()


def _numeral(text: str, *, integer_only: bool = False) -> str | None:
    # Eighteen digits, five grouping separators, a point and twelve decimals.
    if len(text) > 36:
        return None
    match = _NUMBER.fullmatch(text)
    if match is None or (integer_only and match["fraction"]):
        return None
    integer = match["integer"].replace(",", "").replace(" ", "")
    if len(integer) > 18:
        return None
    return integer + (match["fraction"] or "")


def parse_printed_amount(text: str, unit: str) -> Decimal | None:
    """Read one whole amount in the declared canonical unit, or abstain.

    Uniform comma or normalized-space thousands groups and one terminal unit
    period are supported. ``m2``, ``m²`` and ``m^2`` denote the same supported
    square-metre unit. This never converts units or discards extra content.
    """
    unit_pattern = _UNITS.get(unit)
    if unit_pattern is None:
        return None
    match = re.fullmatch(r"(.+?)\s*" + unit_pattern + r"\.?", _normal(text))
    numeral = _numeral(match[1]) if match else None
    return Decimal(numeral) if numeral is not None else None


def parse_scale_ratios(text: str) -> tuple[list[int], bool]:
    """Return valid denominators and whether any numeric ratio is unsupported.

    Candidate discovery is separate from validation: malformed recognized
    ratios are evidence of an unresolved value, never proof of an omission.
    Duplicate ratios remain separate observations for the caller to reject.
    """
    text = _normal(text)
    starts = list(_RATIO_START.finditer(text))
    values = []
    unsupported = False
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        match = _DENOMINATOR.match(text, start.end(), end)
        candidate = match[0] if match else ""
        # Delimiters may separate a word annotation or another independently
        # recognized ratio. A bare numeric continuation still belongs to this
        # unresolved candidate, including across spaced/nested brackets.
        continuation = match and _NUMERIC_CONTINUATION.match(text, match.end(), end)
        if candidate.endswith("."):
            candidate = candidate[:-1]
        numeral = _numeral(candidate, integer_only=True)
        if start[1] != "1" or numeral is None or continuation:
            unsupported = True
            continue
        value = int(numeral)
        if not 1 <= value <= 1_000_000_000:
            unsupported = True
            continue
        values.append(value)
    return values, unsupported
