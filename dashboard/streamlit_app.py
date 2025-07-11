#!/usr/bin/env python3
"""Dilma Streamlit Dashboard  ✦  v0.2

Launch with:
    streamlit run dashboard/streamlit_app.py

Displays
---------
1. **Stacked bar** — total count per value‑label chosen by the model.
2. **Radar ("skill") chart** — same counts plotted as a profile.
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
        order_name = jf.parent.name  # e.g., 'nezikin'
        tract = jf.stem  # e.g., 'bava_metzia'
        for obj in read_jsonl(jf):
            rows.append(
                {
                    "id": obj["id"],
                    "order": order_name,
                    "tractate": tract,
                    "title": obj["title"],
                    "vignette": obj["vignette"],
                    "option_A_tags": "|".join(obj["options"][0]["tags"]),
                    "option_B_tags": "|".join(obj["options"][1]["tags"]),
                    "option_A_text": obj["options"][0]["text"],
                    "option_B_text": obj["options"][1]["text"],
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
# Global Definitions & Initial Data Load
# -----------------------------------------------------------------------------

# Define the poles for each axis (used by Chart 2 on this page)
axes = {
    "Survival / Welfare": ("self-preservation", "altruism"),
    "Entitlement / Obligation": ("property-rights", "responsibility"),
    "Even-split / Protection": ("reciprocity", "worker-dignity"),
    "Sacred Life / Instrumental Life": ("sanctity-of-life", "utilitarian"),
    "Legal Authority / Personal Agency": ("rule-of-law", "vigilantism"),
    "Transcendent Norm / Pragmatism": ("religious-duty", "proportionality"),
}

dl_df_full = load_dilemmas()  # Load all dilemmas, keep a full copy
run_df_original = load_run()  # Keep original for full model lists

# Make copies for filtering on this page
dl_df = dl_df_full.copy()
run_df = run_df_original.copy()

# -----------------------------------------------------------------------------
# Global top-bar filters (Tractate & Model)
# -----------------------------------------------------------------------------
# Build tractate options
if not dl_df_full.empty and "tractate" in dl_df_full.columns:
    tractates = sorted(dl_df_full["tractate"].unique())
else:
    tractates = []
    st.warning(
        "No tractate data found. Dilemma files may be missing in 'data/dilemmas/'."
    )

current_tract = st.session_state.get("sel_tractate", "All")
if current_tract not in ["All"] + tractates:
    current_tract = "All"

# Layout three columns for filters
col1, col2, col3 = st.columns(3)

with col1:
    sel_tractate = st.selectbox(
        "Tractate",
        ["All"] + tractates,
        index=(["All"] + tractates).index(current_tract),
        key="tractate_filter_top",
        help="Filter all charts by tractate",
    )

# Persist tractate selection
st.session_state.sel_tractate = sel_tractate

# Apply tractate filter first, as it affects options for other filters
dl_df_filtered_by_tractate = dl_df_full.copy()
run_df_filtered_by_tractate = run_df_original.copy()

if sel_tractate != "All":
    dl_df_filtered_by_tractate = dl_df_filtered_by_tractate[
        dl_df_filtered_by_tractate["tractate"] == sel_tractate
    ]
    if not run_df_filtered_by_tractate.empty:
        run_df_filtered_by_tractate = run_df_filtered_by_tractate[
            run_df_filtered_by_tractate["dilemma_id"].isin(
                dl_df_filtered_by_tractate["id"]
            )
        ]


# --- Dilemma Type Filter ---
with col2:
    dilemma_type_options = ["All", "Original", "Neutral"]
    current_dilemma_type = st.session_state.get("sel_dilemma_type", "All")
    if current_dilemma_type not in dilemma_type_options:
        current_dilemma_type = "All"

    sel_dilemma_type = st.selectbox(
        "Dilemma Type",
        dilemma_type_options,
        index=dilemma_type_options.index(current_dilemma_type),
        key="dilemma_type_filter_top",
        help="Filter results by dilemma type (Original or Neutral language). Requires 'dilemma_type' column in CSV.",
    )

# Persist dilemma type selection
st.session_state.sel_dilemma_type = sel_dilemma_type

# Apply dilemma_type filter to a copy of tractate-filtered run_df
run_df_filtered_by_type = run_df_filtered_by_tractate.copy()
if sel_dilemma_type != "All":
    if "dilemma_type" in run_df_filtered_by_type.columns:
        run_df_filtered_by_type = run_df_filtered_by_type[
            run_df_filtered_by_type["dilemma_type"] == sel_dilemma_type.lower()
        ]
    else:
        if not run_df_filtered_by_type.empty:  # Only warn if there was data to filter
            st.warning(
                "`dilemma_type` column not found in run data. Cannot filter by dilemma type. Please ensure your CSV includes this column."
            )


# --- Compute model list based on selected tractate AND dilemma_type ---
# Use run_df_filtered_by_type to determine available models
model_opts = []
if (
    not run_df_filtered_by_type.empty
    and "model_name" in run_df_filtered_by_type.columns
):
    model_opts = sorted(run_df_filtered_by_type["model_name"].unique())


current_model = st.session_state.get("sel_model", "All")
if current_model not in ["All"] + model_opts:
    current_model = "All"  # Default to "All" if current selection is not valid

with col3:  # Changed from col2 to col3
    sel_model = st.selectbox(
        "Model",
        ["All"] + model_opts,
        index=(["All"] + model_opts).index(current_model),
        key="model_filter_top",
        help="Filter all charts by model (main display)",
    )

# Persist selections across pages (sel_tractate and sel_dilemma_type already persisted)
st.session_state.sel_model = sel_model

# Apply filters to dl_df and run_df for this page
# dl_df is primarily filtered by tractate for display purposes
dl_df = dl_df_filtered_by_tractate.copy()

# run_df starts from the tractate and type filtered data, then applies model filter
run_df = run_df_filtered_by_type.copy()
if sel_model != "All" and not run_df.empty and "model_name" in run_df.columns:
    run_df = run_df[run_df["model_name"] == sel_model]

# -----------------------------------------------------------------------------
# Chart 1 — stacked bar of value tags chosen
# -----------------------------------------------------------------------------
st.subheader("Value‑label distribution of model choices")

# tag_counter uses the page-specific filtered run_df
tag_counter = Counter(t for lst in run_df["chosen_value_labels"] for t in lst)
if tag_counter:
    tag_df = (
        pd.DataFrame(tag_counter.items(), columns=["label", "count"])
        .sort_values("count", ascending=False)
        .set_index("label")
    )
    st.bar_chart(tag_df)
else:
    st.info(
        "No parsed run data yet for the current selection. Run the model or adjust filters."
    )

# -----------------------------------------------------------------------------
# Chart 2 — Diverging stacked bar for the three bipolar axes
# -----------------------------------------------------------------------------
st.subheader("Bipolar axes: self ←  → other")

# This chart also uses the page-specific filtered run_df
rows = []
for axis, (left_tag, right_tag) in axes.items():
    left_cnt = run_df["chosen_value_labels"].apply(lambda x: left_tag in x).sum()
    right_cnt = run_df["chosen_value_labels"].apply(lambda x: right_tag in x).sum()
    invalid_cnt = (
        run_df["chosen_value_labels"]
        .apply(lambda x: "invalid" in x and left_tag not in x and right_tag not in x)
        .sum()
    )
    rows.append(
        {
            "axis": axis,
            "left": -left_cnt,
            "right": right_cnt,
            "invalid": invalid_cnt,
        }
    )

ax_df = pd.DataFrame(rows).set_index("axis")

if not ax_df[["left", "right", "invalid"]].abs().values.sum():
    st.info("No run data yet for bipolar axes chart for the current selection.")
else:
    fig, ax = plt.subplots(figsize=(5, 3))
    left_bars = ax.barh(
        ax_df.index, ax_df["left"], color="#dd8452", label="Self-leaning"
    )
    right_bars = ax.barh(
        ax_df.index, ax_df["right"], color="#4c72b0", label="Other-leaning"
    )
    invalid_bars = ax.barh(
        ax_df.index,
        ax_df["invalid"],
        left=ax_df["right"].clip(lower=0),
        color="#999999",
        label="Invalid",
    )
    for bars_collection in (left_bars, right_bars, invalid_bars):
        for bar in bars_collection:
            w = bar.get_width()
            if w != 0:
                ax.text(
                    bar.get_x() + w / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{abs(int(w))}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                )
    ax.axvline(0, color="black", linewidth=0.6)
    ax.set_xlabel("Count of answers")
    ax.legend(loc="upper right")
    st.pyplot(fig)

# -----------------------------------------------------------------------------
# Table of dilemmas
# -----------------------------------------------------------------------------
st.subheader("Dilemmas")
# This table uses the page-specific filtered dl_df
show_cols = ["id", "title", "vignette", "option_A_text", "option_B_text"]
st.dataframe(dl_df[show_cols], use_container_width=True)
