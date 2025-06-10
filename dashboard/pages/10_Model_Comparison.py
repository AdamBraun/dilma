#!/usr/bin/env python3
"""Dilma Streamlit Dashboard — Model Comparison Page"""
from __future__ import annotations

import json
import pathlib
from typing import Dict, List

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Import shared configuration
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))
from shared_config import axes

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


def load_dilemmas(dilemma_type="original") -> pd.DataFrame:
    rows: List[Dict] = []
    # Choose directory based on dilemma type
    if dilemma_type == "neutral":
        dilemma_dir = ROOT / "data" / "dilemmas-neutral"
    else:
        dilemma_dir = ROOT / "data" / "dilemmas"
    
    for jf in dilemma_dir.rglob("*.jsonl"):
        order_name = jf.parent.name
        tract = jf.stem
        # Remove "-neutral" suffix from tract name if present
        if tract.endswith("-neutral"):
            tract = tract[:-8]  # Remove "-neutral"
        # Remove number prefix if present (e.g., "16-yoma" -> "yoma")
        if "-" in tract and tract.split("-")[0].isdigit():
            tract = "-".join(tract.split("-")[1:])
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

# Load run data (this stays the same)
run_df_full = load_run()  # Load all run data

# -----------------------------------------------------------------------------
# Global top-bar tractate filter (shared between pages)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Dilemma Type Filter (synced with main page)
# -----------------------------------------------------------------------------
# Add Dilemma Type filter, similar to the main page
dilemma_type_options = ["All", "Original", "Neutral"]
current_dilemma_type = st.session_state.get(
    "sel_dilemma_type", "All"
)  # Get from session state
if current_dilemma_type not in dilemma_type_options:
    current_dilemma_type = "All"

sel_dilemma_type = st.selectbox(
    "Dilemma Type",
    dilemma_type_options,
    index=dilemma_type_options.index(current_dilemma_type),
    key="dilemma_type_filter_comp",  # Unique key for this page
    help="Filter results by dilemma type (Original or Neutral language). Affects model comparison.",
)

# Persist selection for all pages
st.session_state.sel_dilemma_type = sel_dilemma_type

# Load dilemmas based on the selected dilemma type
if sel_dilemma_type == "Neutral":
    dl_df_full = load_dilemmas("neutral")
elif sel_dilemma_type == "Original":
    dl_df_full = load_dilemmas("original")
else:  # "All" - default to original for display purposes
    dl_df_full = load_dilemmas("original")

# Set up tractate filter options based on loaded dilemmas
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

# Filter data based on tractate AND dilemma_type
current_dl_df = dl_df_full.copy()
current_run_df = run_df_full.copy()

if sel_tractate != "All":
    current_dl_df = current_dl_df[current_dl_df["tractate"] == sel_tractate]
    if not current_run_df.empty:
        current_run_df = current_run_df[
            current_run_df["dilemma_id"].isin(current_dl_df["id"])
        ]

# Apply dilemma_type filter to current_run_df
if sel_dilemma_type != "All":
    if "dilemma_type" in current_run_df.columns:
        current_run_df = current_run_df[
            current_run_df["dilemma_type"] == sel_dilemma_type.lower()
        ]
    else:
        if not current_run_df.empty:  # Only warn if there was data to filter
            st.warning(
                "`dilemma_type` column not found in run data for model comparison. "
                "Please ensure your CSV includes this column."
            )

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
            for axis, (left_tags, right_tags) in axes.items():
                for mid_model_name in (model_a, model_b):
                    subset = comp_df[comp_df["model_name"] == mid_model_name]
                    current_axis_self_n = (
                        subset["chosen_value_labels"]
                        .apply(lambda x: any(tag in x for tag in left_tags))
                        .sum()
                    )
                    current_axis_other_n = (
                        subset["chosen_value_labels"]
                        .apply(lambda x: any(tag in x for tag in right_tags))
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
                                any(tag in tags_a for tag in left_tags)
                                or any(tag in tags_a for tag in right_tags)
                                or any(tag in tags_b for tag in left_tags)
                                or any(tag in tags_b for tag in right_tags)
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
                    
                    # Reorder the pivot columns to respect model selection order (A then B)
                    # But keep the original structure with invalid/self/other as top-level categories
                    ordered_pivot = pivot.reindex(columns=[model_a, model_b], level=1)
                    table = pd.concat([ordered_pivot, diff], axis=1)

                    st.header(f"Aggregate Diff: {model_a} → {model_b}")

                    with st.expander(
                        "ℹ️ Axis Legend: Self ↔ Other Poles", expanded=False
                    ):
                        st.markdown(
                            """
The "Self" pole generally prioritizes the actor's own stake, rights, or adherence to personal principles.
The "Other" pole focuses on the welfare, rights, or protection of another party, or a broader societal/communal good.

-   **Survival / Welfare**:
    -   Self (`self-preservation`): Actor prioritizes their own life, safety, or well-being.
    -   Other (`altruism`): Actor sacrifices personal benefit for another's welfare.
-   **Entitlement / Obligation**:
    -   Self (`property-rights`): Actor upholds their existing ownership and legal title.
    -   Other (`responsibility`): Actor is obligated to make victims whole for harms caused.
-   **Even-split / Protection**:
    -   Self (`reciprocity`): Actor seeks mutual fairness or an even split of costs/benefits.
    -   Other (`worker-dignity`): Focus on ensuring fair treatment and rights for laborers.
-   **Sacred Life / Instrumental Life**:
    -   Self (`sanctity-of-life`): A specific human life is considered inviolable and not to be used instrumentally.
    -   Other (`utilitarian`): Decisions favor the greatest overall benefit, even if at individual expense.
-   **Legal Authority / Personal Agency**:
    -   Self (`rule-of-law`): Actor operates within established legal frameworks and authority.
    -   Other (`vigilantism`): Actor takes justice into their own hands or acts on personal judgment, outside formal legal authority.
-   **Transcendent Norm / Pragmatism**:
    -   Self (`religious-duty`): Actor follows obligations from a divine command or deeply held moral/religious commitment.
    -   Other (`proportionality`): Actions and responses are measured and pragmatic, fitting the specifics of the situation.
"""
                        )

                    st.dataframe(
                        table.style.format(precision=0), use_container_width=True
                    )

                    fig_comp, ax_comp = plt.subplots(figsize=(8, 3))
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
                    ax_comp.set_xlabel(f"Δ count ({model_b} – {model_a})")
                    # Move legend to top with padding to avoid overlap with bars
                    ax_comp.legend(bbox_to_anchor=(0.85, 1.15), loc='center', ncol=1)
                    plt.tight_layout()
                    plt.subplots_adjust(top=0.8)  # Add padding at the top
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

                    # Create comprehensive tag-to-pole mapping from shared_config.py axes
                    tag_to_pole_info = {}
                    for axis_name, (self_tags, other_tags) in axes.items():
                        for tag in self_tags:
                            tag_to_pole_info[tag] = ("self", axis_name)
                        for tag in other_tags:
                            tag_to_pole_info[tag] = ("other", axis_name)

                    if not comp_df.empty:
                        # Ensure no duplicates for pivot operation based on dilemma_id and model_name
                        comp_df_for_pivot = comp_df.drop_duplicates(
                            subset=["dilemma_id", "model_name"], keep="first"
                        )
                        pivot_q = comp_df_for_pivot.pivot(
                            index="dilemma_id", columns="model_name", values="choice_id"
                        )
                        if model_a in pivot_q.columns and model_b in pivot_q.columns:
                            diff_q = pivot_q[
                                pivot_q[model_a] != pivot_q[model_b]
                            ].copy()
                            if not diff_q.empty:

                                def get_pole_for_choice(choice_letter, dilemma_id):
                                    if choice_letter == "INVALID":
                                        return "invalid"

                                    tags_for_choice = letter_to_tags.get(
                                        dilemma_id, {}
                                    ).get(choice_letter, [])

                                    # Find the most specific pole match
                                    pole_matches = []
                                    for tag in tags_for_choice:
                                        if tag in tag_to_pole_info:
                                            pole_type, axis_name = tag_to_pole_info[tag]
                                            pole_matches.append((pole_type, axis_name))

                                    if pole_matches:
                                        # If we have matches, use the first one (could be enhanced to handle multiple matches)
                                        pole_type, axis_name = pole_matches[0]
                                        # Create a more descriptive pole name
                                        if pole_type == "self":
                                            return f"self ({axis_name})"
                                        else:
                                            return f"other ({axis_name})"

                                    return "n/a"

                                diff_q["Δ_pole_viz"] = [
                                    f"{get_pole_for_choice(b_choice, did)} ← {get_pole_for_choice(a_choice, did)}"
                                    for did, (a_choice, b_choice) in diff_q[
                                        [model_a, model_b]
                                    ].iterrows()
                                ]

                                # Prepare current_dl_df for merge by selecting necessary columns and dropping duplicates
                                dl_df_for_merge = current_dl_df[
                                    [
                                        "id",
                                        "title",
                                        "option_A_tags",
                                        "option_B_tags",
                                        "option_A_text",
                                        "option_B_text",
                                    ]
                                ].drop_duplicates(subset=["id"])

                                diff_q = diff_q.merge(
                                    dl_df_for_merge,
                                    left_index=True,  # diff_q's index is dilemma_id
                                    right_on="id",  # dl_df_for_merge's dilemma identifier
                                    how="left",  # Keep all rows from diff_q
                                )

                                # Define helper to get actual choice text
                                def get_choice_text(
                                    row, model_key, option_a_text_key, option_b_text_key
                                ):
                                    choice_id = row.get(
                                        model_key
                                    )  # e.g., model_a column which has 'A', 'B', 'INVALID'
                                    text_a = row.get(option_a_text_key)
                                    text_b = row.get(option_b_text_key)

                                    if choice_id == "A":
                                        return (
                                            text_a
                                            if pd.notna(text_a)
                                            else "A (text unavailable)"
                                        )
                                    elif choice_id == "B":
                                        return (
                                            text_b
                                            if pd.notna(text_b)
                                            else "B (text unavailable)"
                                        )
                                    elif choice_id == "INVALID":
                                        return "INVALID"
                                    return f"Unknown ({choice_id})"

                                # Add choice text columns
                                # Check if option_A_text and option_B_text columns exist after merge
                                if (
                                    "option_A_text" in diff_q.columns
                                    and "option_B_text" in diff_q.columns
                                ):
                                    diff_q[f"{model_a}_choice_text"] = diff_q.apply(
                                        get_choice_text,
                                        args=(
                                            model_a,
                                            "option_A_text",
                                            "option_B_text",
                                        ),
                                        axis=1,
                                    )
                                    diff_q[f"{model_b}_choice_text"] = diff_q.apply(
                                        get_choice_text,
                                        args=(
                                            model_b,
                                            "option_A_text",
                                            "option_B_text",
                                        ),
                                        axis=1,
                                    )
                                else:
                                    st.warning(
                                        "Option text columns ('option_A_text', 'option_B_text') not found after merge. Displaying choice IDs instead of text."
                                    )
                                    # Fallback to choice IDs if text columns are missing
                                    diff_q[f"{model_a}_choice_text"] = diff_q[model_a]
                                    diff_q[f"{model_b}_choice_text"] = diff_q[model_b]

                                # Apply axis filter AFTER choice texts have been generated
                                if sel_axis_filter != "All":
                                    # Ensure tag columns are present before attempting to filter
                                    if (
                                        "option_A_tags" in diff_q.columns
                                        and "option_B_tags" in diff_q.columns
                                    ):
                                        axis_left_tags, axis_right_tags = axes[
                                            sel_axis_filter
                                        ]

                                        def check_dilemma_axis_tags(
                                            row, l_tags, r_tags
                                        ):
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
                                            return (
                                                any(tag in tags_a for tag in l_tags)
                                                or any(tag in tags_a for tag in r_tags)
                                                or any(tag in tags_b for tag in l_tags)
                                                or any(tag in tags_b for tag in r_tags)
                                            )

                                        diff_q = diff_q[
                                            diff_q.apply(
                                                check_dilemma_axis_tags,
                                                args=(axis_left_tags, axis_right_tags),
                                                axis=1,
                                            )
                                        ]
                                    else:
                                        st.warning(
                                            "Tag columns ('option_A_tags', 'option_B_tags') missing. Cannot apply axis filter."
                                        )

                                if not diff_q.empty:
                                    display_columns = [
                                        "id",
                                        "title",  # Relies on the merge being successful
                                        f"{model_a}_choice_text",
                                        f"{model_b}_choice_text",
                                        "Δ_pole_viz",
                                    ]

                                    # Ensure all columns intended for display actually exist in diff_q
                                    # Particularly, 'title' might be missing if a dilemma_id in diff_q was not in current_dl_df
                                    # and choice text columns if the fallback was hit.
                                    actual_display_columns = [
                                        col
                                        for col in display_columns
                                        if col in diff_q.columns
                                    ]

                                    if "title" not in actual_display_columns:
                                        # If title is missing, it's a data integrity issue from the merge
                                        # Add a placeholder or remove it from display
                                        if (
                                            "id" in actual_display_columns
                                        ):  # Check if id exists for a placeholder
                                            diff_q["title"] = diff_q["id"].apply(
                                                lambda x: f"Title unavailable for ID: {x}"
                                            )
                                            if "title" not in actual_display_columns:
                                                actual_display_columns.insert(
                                                    1, "title"
                                                )  # try to add it back
                                        # Or, decide to not show title if it's missing, by ensuring it's not in actual_display_columns

                                    if not diff_q[actual_display_columns].empty:
                                        # Drop rows where 'id' is NaN, as 'id' is crucial.
                                        # Title NaNs might be handled by the placeholder logic above or accepted.
                                        diff_q_display = diff_q[
                                            actual_display_columns
                                        ].dropna(subset=["id"])

                                        st.dataframe(
                                            diff_q_display.rename(
                                                columns={
                                                    f"{model_a}_choice_text": f"Choice Text ({model_a})",
                                                    f"{model_b}_choice_text": f"Choice Text ({model_b})",
                                                    "Δ_pole_viz": "Δ Pole (B ← A)",
                                                    "title": "Dilemma Title",  # Ensure title column is nicely named
                                                }
                                            ),
                                            use_container_width=True,
                                        )
                                    else:
                                        st.info(
                                            "No dilemma differences to show after filtering and preparing display data (empty or missing key columns)."
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
