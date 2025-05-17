# Dilma — quick Streamlit dashboard
# Launch with:
#   streamlit run dashboard/streamlit_app.py

import json
import pathlib
from collections import Counter
from typing import List, Dict

import pandas as pd
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_dilemmas(root: pathlib.Path) -> List[Dict]:
    """Walk data/dilemmas, parse every JSONL row into one flat dict."""
    rows = []
    for jf in (root / "data" / "dilemmas").rglob("*.jsonl"):
        tractate = jf.parent.name  # e.g. bava_metzia
        for line in jf.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            combined_tags = [t for opt in obj["options"] for t in opt["tags"]]
            rows.append(
                {
                    "id": obj["id"],
                    "tractate": tractate,
                    "title": obj["title"],
                    "vignette": obj["vignette"],
                    "tags": combined_tags,
                }
            )
    return rows


def main() -> None:
    st.set_page_config(page_title="Dilma Dashboard", layout="wide")
    st.title("Dilma — Dilemma Dataset Overview")

    rows = load_dilemmas(ROOT)
    df = pd.DataFrame(rows)

    tractates = sorted(df["tractate"].unique())
    choice = st.sidebar.selectbox("Filter by tractate", ["All"] + tractates)
    if choice != "All":
        df = df[df["tractate"] == choice]

    # Tag distribution
    tag_counter = Counter(t for tags in df["tags"] for t in tags)
    tag_df = (
        pd.DataFrame(tag_counter.items(), columns=["tag", "count"])
        .sort_values("count", ascending=False)
        .set_index("tag")
    )

    st.subheader("Tag distribution")
    st.bar_chart(tag_df)

    st.subheader("Dilemmas table")
    st.dataframe(df[["id", "title", "vignette"]], use_container_width=True)


if __name__ == "__main__":
    main()
