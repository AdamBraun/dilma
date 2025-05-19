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
# Global Definitions & Initial Data Load
# -----------------------------------------------------------------------------

# Define the poles for each axis (used by model comparison and Chart 2)
axes = {
    "Survival / Welfare": ("self-preservation", "altruism"),
    "Entitlement / Obligation": ("property-rights", "responsibility"),
    "Even-split / Protection": ("reciprocity", "worker-dignity"),
    "Sacred Life / Instrumental Life": ("sanctity-of-life", "utilitarian"),
    "Legal Authority / Personal Agency": ("rule-of-law", "vigilantism"),
    "Transcendent Norm / Pragmatism": ("religious-duty", "proportionality"),
}

dl_df = load_dilemmas()
run_df_original = load_run()  # Keep original for full model lists
run_df = run_df_original.copy()  # This copy will be filtered for main display

# -----------------------------------------------------------------------------
# Sidebar filters - Stage 1 (Tractate Filter)
# -----------------------------------------------------------------------------
tractates = sorted(dl_df["tractate"].unique())
sel_tractate = st.sidebar.selectbox("Filter by tractate", ["All"] + tractates)

# Apply tractate filter to dl_df and the main run_df
if sel_tractate != "All":
    dl_df = dl_df[dl_df["tractate"] == sel_tractate]
    if not run_df.empty:  # Check before filtering
        run_df = run_df[run_df["dilemma_id"].isin(dl_df["id"])]

# -----------------------------------------------------------------------------
# Model-vs-Model comparison
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")  # Visual separator in sidebar
st.sidebar.subheader("Model Comparison")

# Use run_df_original for populating model choices to ensure all models are available
model_ids_for_comparison = []
if not run_df_original.empty and "model_name" in run_df_original.columns:
    model_ids_for_comparison = sorted(run_df_original["model_name"].unique())

if (
    not model_ids_for_comparison or len(model_ids_for_comparison) < 1
):  # Need at least one model to select
    st.sidebar.info("Not enough model data in results CSV for comparison.")
else:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        model_a = st.selectbox(
            "Model A", model_ids_for_comparison, index=0, key="model_a_select"
        )
    with col2:
        # Ensure index for model_b is valid, especially if only one model exists
        model_b_index = min(1, len(model_ids_for_comparison) - 1)
        if (
            len(model_ids_for_comparison) == 1
        ):  # If only one model, default to same as model_a
            model_b_index = 0
        model_b = st.selectbox(
            "Model B",
            model_ids_for_comparison,
            index=model_b_index,
            key="model_b_select",
        )

    # run_df here is already filtered by tractate from the main filter
    # comp_df will be based on this tractate-filtered run_df, further filtered by model_a and model_b
    comp_df_source = run_df  # Use the (potentially) tractate-filtered run_df

    if not comp_df_source.empty and model_a != model_b:
        comp_df = comp_df_source[comp_df_source["model_name"].isin([model_a, model_b])]

        data = []
        for axis, (left_tag, right_tag) in axes.items():
            for mid_model_name in (model_a, model_b):
                subset = comp_df[comp_df["model_name"] == mid_model_name]

                current_axis_self_n = (
                    subset["chosen_value_labels"].apply(lambda x: left_tag in x).sum()
                )
                current_axis_other_n = (
                    subset["chosen_value_labels"].apply(lambda x: right_tag in x).sum()
                )
                # Total invalid responses for this model (not strictly per axis, but per model for this comparison)
                model_total_invalid_n = (subset["choice_id"] == "INVALID").sum()

                data.append(
                    {
                        "axis": axis,
                        "model_name": mid_model_name,  # Changed from "model" to "model_name"
                        "self": current_axis_self_n,
                        "other": current_axis_other_n,
                        "invalid": model_total_invalid_n,
                    }
                )

        if data:  # Ensure data was actually populated
            pivot = (
                pd.DataFrame(data).set_index(["axis", "model_name"]).unstack()
            )  # Changed from "model"
            if (
                not pivot.empty
                and model_b in pivot.columns.levels[1]
                and model_a in pivot.columns.levels[1]
            ):  # Check if models are in pivot
                diff = pivot.xs(model_b, level="model_name", axis=1) - pivot.xs(
                    model_a, level="model_name", axis=1
                )
                diff.columns = pd.MultiIndex.from_product([["Δ"], diff.columns])

                table = pd.concat([pivot, diff], axis=1).sort_index(
                    axis=1
                )  # Sort columns for consistent display
                st.subheader(f"Model diff: {model_b} – {model_a}")
                st.dataframe(table.style.format(precision=0), use_container_width=True)

                # Optional bar chart of Δ other vs Δ self
                fig_comp, ax_comp = plt.subplots(figsize=(5, 3))
                ax_comp.barh(
                    diff.index,
                    diff[("Δ", "other")],
                    color="#4c72b0",
                    label="Other-leaning Δ",
                )
                # For self-leaning delta, ensure it's plotted on the negative side if diff is positive
                ax_comp.barh(
                    diff.index,
                    -diff[("Δ", "self")],
                    color="#dd8452",
                    label="Self-leaning Δ",
                )
                ax_comp.axvline(0, color="k", linewidth=0.6)
                ax_comp.set_xlabel("Δ count (B – A)")
                ax_comp.legend()
                st.pyplot(fig_comp)
            else:
                st.info(
                    f"Not enough data to compare {model_a} and {model_b} for the selected tractate."
                )
        else:
            st.info(
                f"No comparable data found for {model_a} and {model_b} with current filters."
            )

    elif model_a == model_b:
        st.info("Select two different models to see differences.")
    # Removed the 'else' for comp_df_source.empty as it's covered by not model_ids_for_comparison

st.sidebar.markdown("---")  # Visual separator
st.sidebar.subheader("Main Display Filter")

# -----------------------------------------------------------------------------
# Sidebar filters - Stage 2 (Main Model Filter for subsequent charts)
# -----------------------------------------------------------------------------
# model_names = [] # This was the old way
# if "model_name" in run_df.columns: # This run_df is tractate-filtered
# model_names = sorted(run_df["model_name"].unique())

# Use model_ids_for_comparison for consistency in available models, or derive from current run_df
# If run_df is empty due to tractate filter, model_names will be empty
if not run_df.empty and "model_name" in run_df.columns:
    model_names_for_main_display = sorted(run_df["model_name"].unique())
else:
    model_names_for_main_display = []


if not model_names_for_main_display:
    sel_model = None
    st.sidebar.info(
        "No model data for the current tractate to filter by for main display."
    )
elif len(model_names_for_main_display) == 1:
    sel_model = model_names_for_main_display[0]
    st.sidebar.markdown(
        f"**Model:** {sel_model} (only one available for this tractate)"
    )
else:
    sel_model = st.sidebar.selectbox(
        "Filter by model (main display)",
        ["All"] + model_names_for_main_display,
        key="sel_model_main",
    )

# Apply main model filter to run_df (which is already tractate-filtered)
if (
    sel_model
    and sel_model != "All"
    and not run_df.empty  # ensure run_df is not empty before trying to filter
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
            "left": -left_cnt,  # negative = self-leaning
            "right": right_cnt,  # positive = other-leaning
            "invalid": invalid_cnt,
        }  # keep positive, plot to the right of 'right'
    )

ax_df = pd.DataFrame(rows).set_index("axis")

if not ax_df[["left", "right", "invalid"]].abs().values.sum():
    st.info("No run data yet for bipolar axes chart.")
else:
    fig, ax = plt.subplots(figsize=(5, 3))

    # plot self-leaning
    left_bars = ax.barh(
        ax_df.index, ax_df["left"], color="#dd8452", label="Self-leaning"
    )

    # plot other-leaning
    right_bars = ax.barh(
        ax_df.index, ax_df["right"], color="#4c72b0", label="Other-leaning"
    )

    # plot invalid, immediately to the right of the other-leaning segment
    invalid_bars = ax.barh(
        ax_df.index,
        ax_df["invalid"],
        left=ax_df["right"].clip(lower=0),
        color="#999999",
        label="Invalid",
    )

    # numeric labels
    for bars in (left_bars, right_bars, invalid_bars):
        for bar in bars:
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
show_cols = ["id", "title", "vignette"]
st.dataframe(dl_df[show_cols], use_container_width=True)
