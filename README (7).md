# SkinMetric: Skincare Ingredient Interaction Checker

A Retrieval-Augmented Generation (RAG) system that answers skincare ingredient questions using only documented sources, shows which sources it used, and says so when it has no documented information.

> General information only, not medical or dermatological advice. A combination that is not listed in our table is **not** known to be safe; it means we have no documented information about it.

## What it does

- **Ask a question** (`POST /query`): "Can I use retinol and vitamin C together?" The system finds the ingredients named, looks up documented interaction pairs, adds ingredient facts from the corpus, and asks an LLM to answer *only* from that context with citations.
- **Check an ingredient list** (`POST /label`): paste a product's ingredient list. The system lists recognised ingredients (with EU CosIng function and restrictions), documented interactions between them, sun-exposure notes, and any items it could not recognise. The result now also includes an **estimated irritation-risk level and 0–100 score** from the Sprint 3 random-forest model, plus the ingredients that triggered the rule. This endpoint uses no LLM, so it cannot invent anything.
- **Explain a product** (`POST /explain`): same input as `/label`. The risk estimate, flagged ingredients and documented pairs are given to the LLM as numbered context (`[R1]`, `[I#]`, `[P##]`), and it explains them in plain language with citations. It is told never to call a product "safe" or "dangerous" and that the score is a proxy estimate, not a clinical prediction.

## Architecture

```
Streamlit app  ->  FastAPI backend  ->  hybrid retrieval  ->  Chroma (ingredient corpus + interaction table)
 (streamlit_app.py)   (app.py)            name/alias lookup       + gpt-4o-mini (for /query and /explain)
                                          + pair lookup           + RandomForest risk model (risk_score.py)
                                          + vector search            used by /label and /explain
```

How a question flows: the backend finds named ingredients (names and aliases), looks up documented pairs in the interaction table, adds ingredient entries (vector search fills the rest), numbers everything as `[I#]` / `[P##]` context, and asks the LLM to answer only from it with those tags. If the model forgets the tags the backend adds them; if the model says it has no documented information, no source is marked as used. `/label` is deterministic (no LLM).

## Data and sources

| Data | Source | Notes |
|---|---|---|
| Product ingredient lists | [Open Beauty Facts](https://world.openbeautyfacts.org) (ODbL) | Cleaned to 15,383 products; 12,659 kept after CosIng matching. Open Beauty Facts data is licensed under the Open Database License; please credit Open Beauty Facts and its contributors. |
| Ingredient function and EU restrictions | EU CosIng inventory | **2016 snapshot.** A CosIng match means "recognised cosmetic ingredient", not "proven safe". |
| Interaction pairs | `interaction_dataset_draft.csv` / `interaction_dataset.csv` | 30 hand-collected pairs with source links (consumer pages, FDA labels, StatPearls, DermNet). See "Limitations". |
| Ingredient corpus | `ingredient_corpus.jsonl` | 2,063 entries built from the above. |

## Setup

```bash
pip install fastapi uvicorn chromadb openai pandas streamlit requests
export OPENAI_API_KEY=...            # Windows: set OPENAI_API_KEY=...
export CORPUS_PATH=ingredient_corpus.jsonl
export INTERACTION_PATH=interaction_dataset_draft.csv
uvicorn app:create_app --factory --port 8001
```

In a second terminal:

```bash
API_URL=http://127.0.0.1:8001 streamlit run streamlit_app.py
```

Never commit your API key. Use an environment variable or a secrets manager.

## API

| Endpoint | Purpose |
|---|---|
| `GET /health` | Number of ingredient entries and interaction rows loaded, and whether the risk model is loaded |
| `POST /query` `{"question": "..."}` | Grounded answer with sources, recognised ingredients, latency |
| `POST /label` `{"ingredients": "Aqua, Glycerin, Retinol 0.5%, ..."}` | Recognised ingredients, documented pairs, condition notes, unrecognised items, risk estimate |
| `POST /explain` (same body) | Plain-language explanation of the risk estimate and pairs, with sources (503 if the risk model is not loaded) |

Interactive docs: `http://127.0.0.1:8001/docs`.

## Testing

```python
import system_test_50 as T
df = T.run_all(post_function)     # 62 questions: 26 original + 36 written after the Sprint 2 fixes
T.report_rates(df)                # pass rate, unsupported-answer rate, miss rate
```

- `system_test.py`: original 26 questions and the checks (citations, refusals, disclaimer, no "safe" claims).
- `system_test_50.py`: adds 30 new questions and the rate calculations.
- Result files: `test_results.csv` (run 1), `test_results_run2.csv` (after fixes), `test_results_sprint3.csv` (62 questions).
- Details and limits: `TESTING.md`.
- One command for all offline tests: `python run_tests.py`.
- Offline suites (no key needed; stand-in embedder and fake LLM, so they test plumbing and grounding rules, not real answer quality): `test_risk_integration.py` (25 checks), `test_frontend_label.py` (26), `test_error_handling.py` (82: empty, huge, unicode, injection-style and unknown-only input; LLM outage), `verify_citations.py` (displayed sources equal the context the LLM received; URLs, evidence and verified flags equal the table; cited flags follow the tags in the answer).
- Data quality: `python data_quality_check.py` writes `data_quality_report.md`.
- Risk model validation: `python validate_risk.py` writes `risk_validation_report.md`.
- Input limits: questions 3-500 characters, ingredient lists up to 4,000 characters (200 items); the app shows a plain message instead of calling the backend when a limit is broken.
- Demo and backup procedure: `DEMO.md`.
- Risk model on held-out products (brand-grouped 80/20 split): accuracy 0.783, macro-F1 0.755 (majority-class baseline 0.426). Running the app's own parsing on the same held-out products gave 0.781 / 0.752. Method and limits: `RISK_MODEL.md`.

## Limitations

Measured results and known problems are in `TESTING.md`, `data_quality_report.md` and `risk_validation_report.md`. In short:

- Live 62-question runs on gpt-4o-mini scored 60/62, 62/62, 61/62, 61/62 and 62/62 across five runs (latest: 62/62; T53 passed this time, but the closing disclaimer line is still added by the model, not the backend, so it is not guaranteed). The keyword checker is sensitive to wording, so a perfect run is not stable and does not prove every answer is correct. No run answered a question that should have been refused (0 of 23 each time). Some answers state evidence strength without repeating a row's caveat (TESTING.md sections 13 and 14).
- The risk estimate can disagree with the rule-based level (for example a short list of known allergens may be estimated low); the app shows both.
- Hydroquinone and clindamycin appear in the interaction table but have no ingredient entry.
- All 30 interaction rows are ticked `verified_by_team` (a teammate opened each source), after the assistant had read them first. P06 (niacinamide + vitamin C) rests on a physician-reviewed article that names no study (evidence rated low).

- The interaction table has **30 pairs** (P01-P17 from consumer and clinic pages, P18-P30 mostly from FDA labels, StatPearls and DermNet); the sources were read by the assistant on 2026-11-15 and 2026-11-20 (see `checked_note`), and a teammate then ticked every row in the `verified_by_team` column.
- Automatic test checks are keyword-based; they do not prove an answer is fully correct. Manual review is recorded in the `manual_review` column.
- Test questions were written by the team. The first 26 were used while fixing the system, so they are not an independent test.
- The risk model uses rule-based proxy labels (allergens and known irritants), not clinical data.
- CosIng data is a 2016 snapshot.
- Retrieval uses Chroma's default embedding model.
- The app is deployed on Streamlit Community Cloud (free tier). Public link: [https://skinmetric-demo-fhuvfrcvyuxrhrjys95hnf.streamlit.app](https://skinmetric-demo-fhuvfrcvyuxrhrjys95hnf.streamlit.app). The backend runs inside the same app (`EMBED_BACKEND=1`), and the OpenAI key is stored only in the host's secrets. Free apps go to sleep when unused and have limited memory. See `DEPLOY_STREAMLIT_CLOUD.md`. Hugging Face Docker Spaces (`deploy/`) was prepared but not used, because new free accounts are asked to pay for it.

## Repository contents

| Path | What it is |
|---|---|
| `app.py` | FastAPI backend: retrieval, LLM prompt, `/query`, `/label`, `/explain`, `/health` |
| `risk_score.py`, `risk_model.py`, `risk_model.joblib` | Risk scoring used by `/label` and `/explain` (set `RISK_MODEL_PATH` to change the file) |
| `tune_risk.py`, `RISK_MODEL.md` | Risk model tuning script and write-up |
| `test_risk_integration.py`, `test_frontend_label.py`, `test_error_handling.py`, `verify_citations.py`, `run_tests.py` | Offline tests; `run_tests.py` runs them all |
| `data_quality_check.py`, `validate_risk.py` | Data quality and risk validation scripts (write `data_quality_report.md`, `risk_validation_report.md`) |
| `DEMO.md` | Demo script, backup procedure |
| `streamlit_app.py` | Streamlit frontend (chat and ingredient-list screens) |
| `cosing_matching.py` | Matches product ingredients to CosIng |
| `ingredient_corpus.jsonl` | Ingredient corpus loaded into Chroma |
| `interaction_dataset_draft.csv` | Sourced interaction pairs (draft; being verified) |
| `system_test.py`, `system_test_50.py` | System tests |
| `TESTING.md` | Test method, results and limitations |
| `notebooks/` | Colab notebooks for each stage |

## Team

SkinMetric, CS 4920. Team members: Madhukar Reddy Kusuma, Drithi Mandhala, Gopi Krishna Reddy Bujala, Vamshitha Reddy Pesaru, Sri Sai Chowdary, Gowtham Reddy Marri.

## Manual review

Two reviewers check every test answer independently: see `MANUAL_REVIEW.md`. After both finish, `python review_summary.py manual_review_sheet.csv` writes `review_summary.md` with errors and disagreements.
