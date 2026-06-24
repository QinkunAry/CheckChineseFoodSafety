from __future__ import annotations

import re

RULES: dict[str, tuple[str, ...]] = {
    "microbiological": (
        r"\bsalmonella\b", r"\blisteria\b", r"\bbacteria\b", r"\bpathogen",
        r"\bfilthy\b", r"\bdecomposed\b", r"\bmold\b", r"\bmicrobial\b",
        r"\bbacillus\b", r"\be\.?\s*coli\b", r"\bcoliform\b", r"\bmould\b",
    ),
    "chemical": (
        r"\bpesticide", r"\bchemical", r"\bmelamine\b", r"\blead\b",
        r"\bcadmium\b", r"\bmercury\b", r"\bdrug residue",
        r"\bunsafe color", r"\bpoisonous\b",
    ),
    "allergen": (
        r"\bmajor food allergen", r"\bundeclared allergen", r"\ballergen labeling",
        r"\bcontains an allergen",
    ),
    "labeling": (r"\blabel", r"\bmisbrand", r"\bnutrition", r"\bfalse and misleading"),
    "adulteration": (r"\badulter", r"\bsubstitute", r"\bunfit for food"),
}


def classify_reasons(reasons: list[str]) -> list[str]:
    text = " ".join(reasons).casefold()
    tags = [tag for tag, patterns in RULES.items() if any(re.search(pattern, text) for pattern in patterns)]
    return tags or ["other_or_unclassified"]
