#!/usr/bin/env python3
"""Dilma Streamlit Dashboard  ✦  v0.2

Launch with:
    streamlit run dashboard/streamlit_app.py

Displays
---------
1. **Stacked bar** — total count per value‑label chosen by the model.
2. **Radar (“skill”) chart** — same counts plotted as a profile.
3. Raw dilemma table.

Data sources
------------
• `data/dilemmas/**/*.jsonl`   source metadata
• `results/value_label_distribution.csv`   output from `scripts/check_dilemmas.py`
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter
from typing import Dict, List

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
DILEMMA_DIR = ROOT / "data" / "dilemmas"
RUN_CSV = ROOT / "results" / "value_label_distribution.csv"

st.set_page_config(page_title="Dilma Dashboard", layout="wide")
st.title("Dilma — Model Behaviour Dashboard")

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def read_jsonl(fp: pathlib.Path):
    for line in fp.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def load_dilemmas() -> pd.DataFrame:
    rows: List[Dict] = []
    for jf in DILEMMA_DIR.rglob("*.jsonl"):
        tract = jf.parent.name
        for obj in read_jsonl(jf):
            rows.append(
                {
                    "id": obj["id"],
                    "tractate": tract,
                    "title": obj["title"],
                    "vignette": obj["vignette"],
                    "option_A_tags": "|".join(obj["options"][0]["tags"]),
                    "option_B_tags": "|".join(obj["options"][1]["tags"]),
                }
            )
    return pd.DataFrame(rows)


def load_run() -> pd.DataFrame:
    if not RUN_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(RUN_CSV)

    # Normalize delimiters; support both "|" and "," just in case
    def _split(s: str):
        if not s:
            return []
        return [
            x.strip() for part in s.split("|") for x in part.split(",") if x.strip()
        ]

    df["chosen_value_labels"] = df["chosen_value_labels"].fillna("").apply(_split)
    return df


# -----------------------------------------------------------------------------
# Load & filter
# -----------------------------------------------------------------------------

dl_df = load_dilemmas()
run_df = load_run()

# Sidebar filters
tractates = sorted(dl_df["tractate"].unique())
sel_tractate = st.sidebar.selectbox("Filter by tractate", ["All"] + tractates)

model_names = []
if "model_name" in run_df.columns:
    model_names = sorted(run_df["model_name"].unique())

# Add "All" option only if there are models, otherwise selectbox is empty or shows first model.
# Default to first model if available, or "All" if multiple, or handle empty run_df gracefully.
if not model_names:  # No run data or model_name column missing
    sel_model = None
    st.sidebar.info("No model data found in results CSV to filter by.")
elif len(model_names) == 1:
    sel_model = model_names[0]  # Auto-select if only one model
    st.sidebar.markdown(f"**Model:** {sel_model} (only one available)")
else:
    sel_model = st.sidebar.selectbox("Filter by model", ["All"] + model_names)

# Apply tractate filter
if sel_tractate != "All":
    dl_df = dl_df[dl_df["tractate"] == sel_tractate]
    if not run_df.empty:
        run_df = run_df[run_df["dilemma_id"].isin(dl_df["id"])]

# Apply model filter (if a model is selected and run_df is not empty)
if (
    sel_model
    and sel_model != "All"
    and not run_df.empty
    and "model_name" in run_df.columns
):
    run_df = run_df[run_df["model_name"] == sel_model]

# -----------------------------------------------------------------------------
# Chart 1 — stacked bar of value tags chosen
# -----------------------------------------------------------------------------

st.subheader("Value‑label distribution of model choices")

tag_counter = Counter(t for lst in run_df["chosen_value_labels"] for t in lst)
if tag_counter:
    tag_df = (
        pd.DataFrame(tag_counter.items(), columns=["label", "count"])
        .sort_values("count", ascending=False)
        .set_index("label")
    )
    st.bar_chart(tag_df)
else:
    st.info("No parsed run data yet. Run the model first.")

# -----------------------------------------------------------------------------
# Chart 2 — Diverging stacked bar for the three bipolar axes
# -----------------------------------------------------------------------------

st.subheader("Bipolar axes: self ←  → other")

# Define the poles for each axis
axes = {
    "Survival / Welfare": ("self-preservation", "altruism"),
    "Entitlement / Obligation": ("property-rights", "responsibility"),
    "Even-split / Protection": ("reciprocity", "worker-dignity"),
    "Sacred Life / Instrumental Life": ("sanctity-of-life", "utilitarian"),
    "Legal Authority / Personal Agency": ("rule-of-law", "vigilantism"),   # or "authority" vs "personal-agency"
    "Transcendent Norm / Pragmatism": ("religious-duty", "proportionality")
}

rows = []
for axis, (left_tag, right_tag) in axes.items():
    left_cnt     = run_df["chosen_value_labels"].apply(lambda x: left_tag  in x).sum()
    right_cnt    = run_df["chosen_value_labels"].apply(lambda x: right_tag in x).sum()
    invalid_cnt  = run_df["chosen_value_labels"].apply(lambda x: "invalid" in x and
                                                       left_tag not in x and
                                                       right_tag not in x).sum()
    rows.append(
        {"axis": axis,
         "left":  -left_cnt,          # negative = self-leaning
         "right":  right_cnt,         # positive = other-leaning
         "invalid": invalid_cnt}      # keep positive, plot to the right of 'right'
    )

ax_df = pd.DataFrame(rows).set_index("axis")

if not ax_df[["left","right","invalid"]].abs().values.sum():
    st.info("No run data yet for bipolar axes chart.")
else:
    fig, ax = plt.subplots(figsize=(5, 3))

    # plot self-leaning
    left_bars = ax.barh(ax_df.index, ax_df["left"],
                        color="#dd8452", label="Self-leaning")

    # plot other-leaning
    right_bars = ax.barh(ax_df.index, ax_df["right"],
                         color="#4c72b0", label="Other-leaning")

    # plot invalid, immediately to the right of the other-leaning segment
    invalid_bars = ax.barh(ax_df.index,
                           ax_df["invalid"],
                           left=ax_df["right"].clip(lower=0),
                           color="#999999",
                           label="Invalid")

    # numeric labels
    for bars in (left_bars, right_bars, invalid_bars):
        for bar in bars:
            w = bar.get_width()
            if w != 0:
                ax.text(bar.get_x() + w/2,
                        bar.get_y() + bar.get_height()/2,
                        f"{abs(int(w))}",
                        ha="center", va="center",
                        fontsize=8, color="white")

    ax.axvline(0, color="black", linewidth=0.6)
    ax.set_xlabel("Count of answers")
    ax.legend(loc="upper right")
    st.pyplot(fig)

# -----------------------------------------------------------------------------
# Table of dilemmas
# -----------------------------------------------------------------------------

st.subheader("Dilemmas")
show_cols = ["id", "title", "vignette"]
st.dataframe(dl_df[show_cols], use_container_width=True)
