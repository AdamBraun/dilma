#!/usr/bin/env python3
"""Dilma Streamlit Dashboard — Model Comparison Page"""
from __future__ import annotations

import json
import pathlib
from typing import Dict, List

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Define ROOT, DILEMMA_DIR, RUN_CSV relative to this file's new location
# Assuming 'pages' is a subfolder of the Streamlit app's root where dashboard_streamlit_app.py was
ROOT = pathlib.Path(__file__).resolve().parents[2]
DILEMMA_DIR = ROOT / "data" / "dilemmas"
RUN_CSV = ROOT / "results" / "value_label_distribution.csv"

st.set_page_config(page_title="Dilma Model Comparison", layout="wide")
st.title("Dilma — Model vs. Model Comparison")

# -----------------------------------------------------------------------------
# Helpers (Copied from main app)
# -----------------------------------------------------------------------------


def read_jsonl(fp: pathlib.Path):
    for line in fp.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def load_dilemmas() -> pd.DataFrame:
    rows: List[Dict] = []
    for jf in DILEMMA_DIR.rglob("*.jsonl"):
        order_name = jf.parent.name
        tract = jf.stem
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

    def _split(s: str):
        if not s:
            return []
        return [
            x.strip() for part in s.split("|") for x in part.split(",") if x.strip()
        ]

    df["chosen_value_labels"] = df["chosen_value_labels"].fillna("").apply(_split)
    return df


# -----------------------------------------------------------------------------
# Global Definitions & Initial Data Load for this page
# -----------------------------------------------------------------------------

axes = {
    "Survival / Welfare": ("self-preservation", "altruism"),
    "Entitlement / Obligation": ("property-rights", "responsibility"),
    "Even-split / Protection": ("reciprocity", "worker-dignity"),
    "Sacred Life / Instrumental Life": ("sanctity-of-life", "utilitarian"),
    "Legal Authority / Personal Agency": ("rule-of-law", "vigilantism"),
    "Transcendent Norm / Pragmatism": ("religious-duty", "proportionality"),
}

dl_df_full = load_dilemmas()  # Load all dilemmas
run_df_full = load_run()  # Load all run data

# -----------------------------------------------------------------------------
# Global top-bar tractate filter (shared between pages)
# -----------------------------------------------------------------------------
if not dl_df_full.empty and "tractate" in dl_df_full.columns:
    tractate_options = ["All"] + sorted(dl_df_full["tractate"].unique())
else:
    tractate_options = ["All"]
    st.warning(
        "No tractate data found. Dilemma files may be missing in 'data/dilemmas/'."
    )

current_tract = st.session_state.get("sel_tractate", "All")
if current_tract not in tractate_options:
    current_tract = "All"

sel_tractate = st.selectbox(
    "Tractate",
    tractate_options,
    index=tractate_options.index(current_tract),
    key="tractate_filter_comp",
    help="Filter all charts by tractate",
)

# Persist selection for all pages
st.session_state.sel_tractate = sel_tractate

# -----------------------------------------------------------------------------
# Session State & Context Display
# -----------------------------------------------------------------------------
# Other filters that may come from the main page (e.g., model)
sel_model_from_main = st.session_state.get("sel_model", None)

# Filter data based on tractate
current_dl_df = dl_df_full.copy()
current_run_df = run_df_full.copy()

if sel_tractate != "All":
    current_dl_df = current_dl_df[current_dl_df["tractate"] == sel_tractate]
    if not current_run_df.empty:
        current_run_df = current_run_df[
            current_run_df["dilemma_id"].isin(current_dl_df["id"])
        ]

# -----------------------------------------------------------------------------
# Model Comparison Setup
# -----------------------------------------------------------------------------
st.sidebar.markdown("### Model Selection")

# Use current_run_df (potentially tractate-filtered) for model choices
model_ids_for_comparison = []
if not current_run_df.empty and "model_name" in current_run_df.columns:
    model_ids_for_comparison = sorted(current_run_df["model_name"].unique())

if not model_ids_for_comparison:
    st.warning(
        "No model data available for the current tractate filter. "
        "Please select a tractate with data on the Overview page."
    )
else:
    # Default to the main page's selected model if available
    default_model_a_idx = (
        model_ids_for_comparison.index(sel_model_from_main)
        if sel_model_from_main in model_ids_for_comparison
        else 0
    )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        model_a = st.selectbox(
            "Model A",
            model_ids_for_comparison,
            index=default_model_a_idx,
            key="comp_model_a_select",
        )
    with col2:
        # For model B, prefer a different model than A when possible
        remaining_models = [m for m in model_ids_for_comparison if m != model_a]
        model_b_options = (
            remaining_models if remaining_models else model_ids_for_comparison
        )
        model_b = st.selectbox(
            "Model B",
            model_b_options,
            index=0,
            key="comp_model_b_select",
        )

    # comp_df will be based on current_run_df (already tractate-filtered),
    # further filtered by model_a and model_b selected on this page.
    if not current_run_df.empty and model_a != model_b:
        comp_df = current_run_df[current_run_df["model_name"].isin([model_a, model_b])]

        if not comp_df.empty:
            data = []
            for axis, (left_tag, right_tag) in axes.items():
                for mid_model_name in (model_a, model_b):
                    subset = comp_df[comp_df["model_name"] == mid_model_name]
                    current_axis_self_n = (
                        subset["chosen_value_labels"]
                        .apply(lambda x: left_tag in x)
                        .sum()
                    )
                    current_axis_other_n = (
                        subset["chosen_value_labels"]
                        .apply(lambda x: right_tag in x)
                        .sum()
                    )
                    # Calculate axis-specific invalid count
                    count_invalid_for_this_axis = 0
                    # Get dilemmas where the current model chose "INVALID"
                    invalid_choices_df = subset[subset["choice_id"] == "INVALID"]

                    if not invalid_choices_df.empty and not current_dl_df.empty:
                        # Merge these invalid choices with the dilemma details (which have option tags)
                        # We only need 'dilemma_id' from invalid_choices_df for the merge
                        # and 'id', 'option_A_tags', 'option_B_tags' from current_dl_df
                        merged_invalids_with_dilemma_tags = pd.merge(
                            invalid_choices_df[["dilemma_id"]],
                            current_dl_df[["id", "option_A_tags", "option_B_tags"]],
                            left_on="dilemma_id",
                            right_on="id",  # 'id' is the dilemma identifier in current_dl_df
                            how="left",
                        )

                        for _idx, row in merged_invalids_with_dilemma_tags.iterrows():
                            # Safely get tag strings and split them into lists
                            tags_a_str = row.get("option_A_tags")
                            tags_b_str = row.get("option_B_tags")

                            tags_a = (
                                tags_a_str.split("|")
                                if pd.notna(tags_a_str) and tags_a_str
                                else []
                            )
                            tags_b = (
                                tags_b_str.split("|")
                                if pd.notna(tags_b_str) and tags_b_str
                                else []
                            )

                            # Check if the dilemma's options (A or B) have tags matching the current axis poles
                            if (
                                (left_tag in tags_a)
                                or (right_tag in tags_a)
                                or (left_tag in tags_b)
                                or (right_tag in tags_b)
                            ):
                                count_invalid_for_this_axis += 1

                    data.append(
                        {
                            "axis": axis,
                            "model_name": mid_model_name,
                            "self": current_axis_self_n,
                            "other": current_axis_other_n,
                            "invalid": count_invalid_for_this_axis,  # Use axis-specific count
                        }
                    )

            if data:
                pivot = pd.DataFrame(data).set_index(["axis", "model_name"]).unstack()
                if (
                    not pivot.empty
                    and model_b in pivot.columns.levels[1]
                    and model_a in pivot.columns.levels[1]
                ):
                    diff = pivot.xs(model_b, level="model_name", axis=1) - pivot.xs(
                        model_a, level="model_name", axis=1
                    )
                    diff.columns = pd.MultiIndex.from_product([["Δ"], diff.columns])
                    axes_with_diff = [
                        ax for ax in diff.index if diff.loc[ax].abs().sum() > 0
                    ]
                    table = pd.concat([pivot, diff], axis=1).sort_index(axis=1)

                    st.header(f"Aggregate Diff: {model_b} vs. {model_a}")
                    st.dataframe(
                        table.style.format(precision=0), use_container_width=True
                    )

                    fig_comp, ax_comp = plt.subplots(figsize=(5, 3))
                    ax_comp.barh(
                        diff.index,
                        diff[("Δ", "other")],
                        color="#4c72b0",
                        label="Other-leaning Δ",
                    )
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

                    # --- DILEMMA-LEVEL DIFF TABLE START ---
                    st.markdown("### Per-dilemma choice differences")
                    axis_filter_options = ["All"] + axes_with_diff
                    sel_axis_filter = st.selectbox(
                        "Filter by Bipolar Axis (for dilemma list):",
                        axis_filter_options,
                        key="comp_dilemma_diff_axis_filter",  # Unique key for this page
                    )

                    letter_to_tags = {}
                    # Use current_dl_df (already tractate-filtered)
                    for _idx, row in current_dl_df.iterrows():
                        d_id = row["id"]
                        option_a_tags_list = (
                            row["option_A_tags"].split("|")
                            if pd.notna(row["option_A_tags"]) and row["option_A_tags"]
                            else []
                        )
                        option_b_tags_list = (
                            row["option_B_tags"].split("|")
                            if pd.notna(row["option_B_tags"]) and row["option_B_tags"]
                            else []
                        )
                        letter_to_tags[d_id] = {
                            "A": option_a_tags_list,
                            "B": option_b_tags_list,
                        }

                    poles_for_dilemma_diff = {
                        "self": [
                            "self-preservation",
                            "property-rights",
                            "reciprocity",
                            "privacy",
                        ],
                        "other": ["altruism", "responsibility", "worker-dignity"],
                    }

                    if not comp_df.empty:
                        pivot_q = comp_df.pivot(
                            index="dilemma_id", columns="model_name", values="choice_id"
                        )
                        if model_a in pivot_q.columns and model_b in pivot_q.columns:
                            diff_q = pivot_q[
                                pivot_q[model_a] != pivot_q[model_b]
                            ].copy()
                            if not diff_q.empty:

                                def get_pole_for_choice(choice_letter, dilemma_id):
                                    tags_for_choice = letter_to_tags.get(
                                        dilemma_id, {}
                                    ).get(choice_letter, [])
                                    if any(
                                        t in poles_for_dilemma_diff["self"]
                                        for t in tags_for_choice
                                    ):
                                        return "self"
                                    if any(
                                        t in poles_for_dilemma_diff["other"]
                                        for t in tags_for_choice
                                    ):
                                        return "other"
                                    if choice_letter == "INVALID":
                                        return "invalid"
                                    return "n/a"

                                diff_q["Δ_pole_viz"] = [
                                    f"{get_pole_for_choice(b_choice, did)} ← {get_pole_for_choice(a_choice, did)}"
                                    for did, (a_choice, b_choice) in diff_q[
                                        [model_a, model_b]
                                    ].iterrows()
                                ]
                                diff_q = diff_q.merge(
                                    current_dl_df[
                                        [
                                            "id",
                                            "title",
                                            "option_A_tags",
                                            "option_B_tags",
                                        ]
                                    ],
                                    left_index=True,
                                    right_on="id",
                                    how="left",
                                )
                                if sel_axis_filter != "All":
                                    axis_left_tag, axis_right_tag = axes[
                                        sel_axis_filter
                                    ]

                                    def check_dilemma_axis_tags(row, l_tag, r_tag):
                                        tags_a = (
                                            row["option_A_tags"].split("|")
                                            if pd.notna(row["option_A_tags"])
                                            else []
                                        )
                                        tags_b = (
                                            row["option_B_tags"].split("|")
                                            if pd.notna(row["option_B_tags"])
                                            else []
                                        )
                                        return (
                                            (l_tag in tags_a)
                                            or (r_tag in tags_a)
                                            or (l_tag in tags_b)
                                            or (r_tag in tags_b)
                                        )

                                    diff_q = diff_q[
                                        diff_q.apply(
                                            check_dilemma_axis_tags,
                                            args=(axis_left_tag, axis_right_tag),
                                            axis=1,
                                        )
                                    ]

                                if not diff_q.empty:
                                    display_columns = [
                                        "id",
                                        "title",
                                        model_a,
                                        model_b,
                                        "Δ_pole_viz",
                                    ]
                                    diff_q_display = diff_q[display_columns].dropna(
                                        subset=["title"]
                                    )
                                    st.dataframe(
                                        diff_q_display.rename(
                                            columns={
                                                model_a: f"Choice ({model_a})",
                                                model_b: f"Choice ({model_b})",
                                                "Δ_pole_viz": "Δ Pole (B ← A)",
                                            }
                                        ),
                                        use_container_width=True,
                                    )
                                else:
                                    st.info(
                                        "No dilemma differences to show for the selected axis filter."
                                    )
                            else:
                                st.info(
                                    "Models made identical choices for all dilemmas in this set (or no common dilemmas with choices)."
                                )
                        else:
                            st.info(
                                f"One or both selected models ({model_a}, {model_b}) have no data for the current selection."
                            )
                    else:
                        st.info(
                            "No data available for dilemma-level comparison with current model selections."
                        )
                    # --- DILEMMA-LEVEL DIFF TABLE END ---
                else:
                    st.info(
                        f"Not enough data to compare {model_a} and {model_b} for the selected tractate."
                    )
            else:
                st.info(
                    f"No comparable data found for {model_a} and {model_b} with current filters."
                )
    elif model_a == model_b:
        st.info("Select two different models in the sidebar to see differences.")

# Placeholder if no model data was found for the tractate at all.
if (
    model_ids_for_comparison
    and len(model_ids_for_comparison) >= 1
    and model_a == model_b
    and len(model_ids_for_comparison) > 1
):
    pass  # Already handled by the "Select two different models" message
elif not model_ids_for_comparison:
    st.info(
        "No model data available for the current tractate filter. Please select a tractate with data on the main page."
    )
