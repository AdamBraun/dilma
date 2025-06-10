#!/usr/bin/env python3
"""Shared configuration for Dilma Streamlit Dashboard"""

# Define the poles for each axis (used by charts across multiple pages)
axes = {
    # 1 ⬛ Survival / Welfare
    "Survival / Welfare": (
        [  # SELF-leaning tags
            "self-preservation",
            "self-defense",
            "self-sacrifice",
            "self-control",
            "self-discipline",
            "financial-sacrifice",
        ],
        [  # OTHER-leaning tags
            "altruism",
            "duty-to-rescue",
            "defense-of-others",
            "compassion",
            "family-loyalty",
            "collective-responsibility",
        ],
    ),
    # 2 🟥 Entitlement / Obligation
    "Entitlement / Obligation": (
        ["property-rights", "legalism", "tradition", "simplification"],
        [
            "responsibility",
            "restitution",
            "prudence",
            "fairness",
            "parental-responsibility",
            "environmental-stewardship",
        ],
    ),
    # 3 🟧 Even-split / Protection
    "Even-split / Protection": (
        ["reciprocity", "trust", "collaboration"],
        ["worker-dignity", "prudence", "integrity", "humility"],
    ),
    # 4 🟨 Sacred-Life / Instrumental-Life
    "Sacred Life / Instrumental Life": (
        [
            "sanctity-of-life",
            "life",
            "maternal-health",
            "potential-life",
            "self-sacrifice",
        ],
        [
            "utilitarian",
            "property-vs-life",
            "public-safety",
            "deterrence",
            "preemptive-justice",
        ],
    ),
    # 5 🟩 Legal Authority / Personal Agency
    "Legal Authority / Personal Agency": (
        ["rule-of-law", "due-process", "authority", "public-safety"],
        ["vigilantism", "personal-agency", "innovation", "peer-pressure"],
    ),
    # 6 🟦 Transcendent Norm / Pragmatism
    "Transcendent Norm / Pragmatism": (
        [
            "religious-duty",
            "public-sanctification",
            "absolutism",
            "defense-of-values",
            "tradition",
        ],
        [
            "proportionality",
            "prudence",
            "simplification",
            "innovation",
            "reconciliation",
            "hospitality",
        ],
    ),
}
