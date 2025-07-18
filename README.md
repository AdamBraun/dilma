[![CI Checks](https://github.com/AdamBraun/dilma/actions/workflows/ci.yml/badge.svg)](https://github.com/AdamBraun/dilma/actions/workflows/ci.yml)

# 🕮 Dilma — Oral‑Torah Dilemma Benchmark

A continuously‑updated, open repository of **ethical and interpersonal dilemmas drawn from the Oral Torah** (Talmud, Midrash, later responsa) for evaluating the emergent value‑preferences of large language models (LLMs).

> *Goal:* Offer a culture‑aware complement to existing moral‑reasoning datasets, and provide a live dashboard that tracks how model behavior shifts across releases.

---

## ✨ Why another benchmark?

| Gap in current suites                | What this project adds                                                                       |
| ------------------------------------ | -------------------------------------------------------------------------------------------- |
| Western‑centric, utilitarian framing | Duty‑based, precedent‑driven cases with multiple legitimate answers                          |
| Static CSV corpora                   | **Daily pipeline** that queries public APIs and logs drift metrics                           |
| Simple right/wrong labels            | **Value‑vector annotation** (e.g., self‑preservation · communal obligation · fiduciary duty) |

The sugyot of _Bava Metzia_—our pilot tractate—already expose trade‑offs such as _self vs. other_ (One Canteen 62a), _privacy vs. cost_ (Fence 102a), and _worker dignity vs. flexibility_ (Timely Wages 110b). Expanding to the full Oral Torah will give hundreds of orthogonal probes.

---

## 📂 Repository layout

```text
dilma/
├── data/
│   ├── dilemmas/
│   │   ├── bava_metzia.jsonl         # pilot set (31 items)
│   │   └── ...                       # future tractates & midrashim
|   └── dilemmas-neutral/             # `dilemmas/` mirror structure with neutral language
|       ├── bava_metzia-neutral.jsonl # neutral language bava_metzia.jsonl version
|       └── ...
│   └── annotations/
│       └── value_labels.yaml         # mapping of options → abstract value tags
├── runners/
│   ├── prompt_runner.py              # sends vignettes to model endpoints
│   └── scorer.py                     # maps answers → value vectors
├── dashboard/
│   └── streamlit_app.py              # live drift & trend charts
├── docs/                             # white‑papers, citation list
└── README.md                         # you are here
```

### JSONL schema (`data/dilemmas/*.jsonl`)

```jsonc
{
  "id": "bm-005",
  "source": "Bava Metzia 62a",
  "title": "One canteen in the desert",
  "vignette": "Two travelers share a path…",
  "options": [
    {
      "id": "A",
      "text": "Share the water equally; risk both lives",
      "tags": ["altruism", "equality"]
    },
    {
      "id": "B",
      "text": "The owner drinks; secure one life",
      "tags": ["self‑preservation", "property‑rights"]
    }
  ]
}
```

_No accepted halakhic ruling is stored; only the competing voices._

---

## 🚀 Quick‑start

```bash
pip install -r requirements.txt
python runners/prompt_runner.py --model gpt-4o --dilemmas data/dilemmas/bava_metzia.jsonl
streamlit run dashboard/streamlit_app.py
```

The dashboard automatically detects new `results/*.parquet` files and updates trend lines.

---

## Dataset Progress

As of June 2025 the dataset spans **all 63 tractates**, totaling over **950** neutral dilemmas with manual answers.

---

## 🤝 Contributing

### Add a new dilemma

1. Pick a primary source (Mishnah, Gemara, Midrash).
2. Write a ≤120‑word vignette in contemporary language.
3. Provide **2–4 options**, each mapping to abstract value tags.
4. Submit a PR with the new JSONL item **and** a reference in `docs/sources.bib`.

### Translation & QA

_Help us keep the English crisp and add Hebrew/Arabic/… localizations._

### Annotation guide

See `docs/annotation_protocol.md` for the controlled vocabulary of value tags.

---

## 🛣️ Road‑map

- [x] Pilot set: _Bava Metzia_ (31 dilemmas)
- [x] Compare neutral language with original (free translation of) texts
- [x] Complete Zeraim order
- [x] Complete Moe'ed order
- [x] Complete Nashim order
- [x] Complete Nezikin order
- [x] Complete Kodashim order
- [x] Complete Taharot order
- [ ] `Explain-then-choose` vs `Choose-then-explain` - Tests whether requiring rationale first drags models toward “responsibility” pole.
- [ ] **Temperature sweep (0 → 0.8)** - See if higher randomness spreads choices or keeps the same polarity.
- [ ] **Prompt swap** - reverse the order of options
- [ ] **A/B vs Multi-choice** - adding a third “compromise” option will likely widen differences again; worth testing.
- [ ] **Add contradiction check** - Provide two dilemmas that secretly encode the same law in opposite wording. If the model follows Halacha it will answer inconsistently with its own stated principle; if it follows principle, it stays coherent.
- [ ] **Weekly** cron job polling all the supported models
- [ ] **Logistic drift test** - Schedule the same diff weekly. If a provider updates alignment, a bar jump even before release notes mention it.
- [ ] Per-dilemma diff table - Identify which 3–4 scenarios drive swings
- [ ] Midrashic narratives (moral imagination)
- [ ] Multi‑lingual vignettes (Hebrew, Arabic, Spanish)
- [ ] Fine‑tuned evaluation harness (ruff, OpenAI evals‑v2)

---

## 📜 License & Attribution

All original dataset content © 2025 **Dilma Project** – CC‑BY‑4.0. Source texts are public‑domain or used under fair‑use scholarship.

> Cite this repo as: _Dilma v0.1_, May 2025.

---

## 🙏 Acknowledgements

Inspired by ETHICS, MoralBench, and centuries of hevruta‑style debate.
