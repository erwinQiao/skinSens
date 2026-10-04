#!/usr/bin/env python3
r"""Safe text-formula -> LaTeX conversions for plain Markdown output.

Why a rule table: each rule is independently auditable and a new conversion
is one added row. The old converter mixed live rules with no-op rules and a
dangerous `(\d+)\s*\+` rule that turned ordinary prose into unbalanced `$`
math; everything kept here is conservative.

Target format notes:
  - `$...$` inline math renders in GitHub and Obsidian, so plain LaTeX
    survives without any document build system.
  - Digit-unit spacing uses a real U+00A0 character, not the LaTeX `~`
    (a bare tilde shows literally in plain Markdown renderers).
"""

from __future__ import annotations

import re

NBSP = "\u00a0"

RULES: list[tuple[re.Pattern[str], str]] = [
    # Endpoint notation: IC50 / EC50 / LC50 in their typed variants
    (
        re.compile(r"\b(IC|EC|LC)\s*[-_]?\s*50\b", re.IGNORECASE),
        r"$\1_{50}$",
    ),
    (
        re.compile(r"\b(IC|EC|LC)\s*\(\s*50\s*\)", re.IGNORECASE),
        r"$\1_{50}$",
    ),
    # Simple chemical formulas
    (re.compile(r"\bCO2\b"), r"$CO_2$"),
    (re.compile(r"\bH2O\b"), r"$H_2$O"),
    (re.compile(r"\bO2\b"), r"$O_2$"),
    # Units: bind digit to unit with a non-breaking space
    (re.compile(r"(\d+)\s*(µg/mL|μg/mL)\b"), rf"\1{NBSP}\2"),
    (re.compile(r"(\d+)\s*(µM|μM|mM|nM)\b"), rf"\1{NBSP}\2"),
    (re.compile(r"(\d+)\s*°\s*C\b"), rf"\1{NBSP}°C"),
    (re.compile(r"(\d+)\s*(nm|µm|min|h)\b"), rf"\1{NBSP}\2"),
    # Irradiation units carry a superscript
    (re.compile(r"(\d+)\s*mW/cm2\b"), rf"\1{NBSP}mW/cm$^2$"),
    (re.compile(r"(\d+)\s*J/cm2\b"), rf"\1{NBSP}J/cm$^2$"),
    (re.compile(r"(\d+)\s*W/cm2\b"), rf"\1{NBSP}W/cm$^2$"),
]


def convert_line(text: str) -> str:
    """Apply formula rules to one non-heading, non-placeholder line.

    Lines that already contain `$` are left untouched: mixing rules into
    hand-written math is how unbalanced delimiters get created.
    """
    if "$" in text:
        return text
    for pattern, replacement in RULES:
        text = pattern.sub(replacement, text)
    return text


if __name__ == "__main__":
    examples = [
        "The IC50 value was calculated",
        "IC 50 and EC-50 variants",
        "CO2 and H2O production",
        "5 J/cm2 and 1.7 mW/cm2 irradiation",
        "50 µg/mL, 37 °C, 24 h incubation",
        "Already math $IC_{50}$ stays untouched",
        "Cells at 370C typo stays as-is",
        "3 + 4 arithmetic is never touched",
    ]
    for line in examples:
        print(f"  {line!r:55} -> {convert_line(line)!r}")
