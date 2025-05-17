### Dilma — Initial Population Road-Map

_(Practical, sequential action items you can work through in Cursor/Git)_

---

#### 0 Kick-off (½ day)

1. **Pull fresh main** (Already done. skip this)

   ```bash
   git checkout main && git pull
   ```

2. **Create a feature branch** for the whole “populate-Bava-Metzia” sprint.

   ```bash
   git checkout -b feat/bava-metzia-seed
   ```

---

#### 1 Scaffold the data folders (½ day)

- `data/dilemmas/`

  - `zeraim/`, `moed/`, `nashim/`, `nezikin/`, `kodashim/`, `taharot/`

- Put an empty `README.md` in each sub-folder so Git tracks them.

Commit: `chore: scaffold tractate folders`

---

#### 2 Seed value-label YAML (1 hour)

- Open `data/annotations/value_labels.yaml`
- Copy the cheat-sheet tags from **Instructions.md**.
- Commit: `feat: add base value labels`

---

#### 3 Phase 1 Tractate = _Bava Metzia_ (2 days)

1. **Migrate the 31 pilot dilemmas**

   - Create `nezikin/bava_metzia.jsonl`
   - Paste each JSONL row (IDs `bm-001` … `bm-031`) _exactly_ as in our earlier examples.

2. **Add BibTeX entries** for each sugya source to `docs/sources.bib`.
3. `make test` until green.

Commit: `feat(bm): import 31 dilemmas + citations`

---

#### 4 Dashboard sanity check (2 hours)

1. Run the prompt runner in `--dry` mode on the new file.
2. Launch Streamlit; verify the dilemmas render and tag histograms look sane.
3. Push screenshots in `docs/screens/demo-bava-metzia.png`.

Commit: `docs: add demo dashboard screenshots`

---

#### 5 Phase 2 Tractate = _Bava Kamma_ (3 days)

1. **Extraction pass**: read through _Bava Kamma_; list interpersonal dilemmas into a Google Sheet.
2. **Draft vignettes & options** (target 25–40 items). Keep ≤120 words each.
3. **Peer review**: self-review for jargon, tag coverage.
4. Add as `nezikin/bava_kamma.jsonl`; citations to BibTeX.

Commit: `feat(bk): seed initial 30 dilemmas`

---

#### 6 CI & automation polish (1 day, parallel)

- Add GitHub Action to run `make test` + prompt-runner `--dry` on PRs.
- Add badge to README for build status.
- Optional: nightly cron that runs full model evaluation and pushes parquet to `gh-pages` branch.

Commit: `ci: add test + nightly evaluation workflows`

---

#### 7 Phase 3 Tractate = _Sanhedrin_ (4 days)

_(repeat Phase 2 steps; focus on capital-case ethical dilemmas and witness rules)_

---

#### 8 Public release v0.1 (½ day)

1. Update README metrics (total dilemmas, tractates covered).
2. Tag release, push changelog.

---

### Maintenance cadence

| Week | Goal                                       |
| ---- | ------------------------------------------ |
| 1–2  | Finish _Nezikin_ (Sanhedrin, Makkot)       |
| 3–4  | Tackle key _Moed_ cases (Shabbat, Eruvin)  |
| 5    | Community call for contributors; merge PRs |
| 6    | First academic blog-post + dashboard link  |

---

### Quick checklist for **today**

- [ ] Branch `feat/bava-metzia-seed`
- [ ] Scaffold folders
- [ ] Add `value_labels.yaml`
- [ ] Import 31 _Bava Metzia_ dilemmas
- [ ] Green `make test`

Once these five boxes are ticked, open a draft PR and we’ll iterate!
