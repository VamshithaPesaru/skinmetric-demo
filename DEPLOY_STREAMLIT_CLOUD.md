# Free public deployment (Streamlit Community Cloud)

Hugging Face now asks new free accounts to pay for Docker Spaces, so use this instead. It needs only a GitHub account and a free Streamlit Community Cloud account. The FastAPI backend runs inside the same app (set by one secret), so there is only one thing to host.

**Status: written and checked offline (the app starts its own backend and the ingredient-list screen works with a stand-in embedder), but NOT yet tried on Streamlit Community Cloud.** Treat the first deploy as the test.

## What must be in the GitHub repository (repo root)

`streamlit_app.py`, `app.py`, `risk_score.py`, `risk_model.py`, `risk_model.joblib` (about 21.6 MB, under GitHub's 25 MB web-upload limit), `ingredient_corpus.jsonl`, `interaction_dataset_draft.csv`, `requirements.txt`

The repo may also hold the README, tests and the other project files. **Never put the OpenAI key in any file.**

## Steps

1. Push or upload the files above to a GitHub repository.
2. Go to share.streamlit.io and sign in with GitHub (create the account yourself).
3. Click **Create app**, pick the repository and branch, and set the main file to `streamlit_app.py`.
4. Open **Advanced settings > Secrets** and paste exactly these two lines, with your own key:
   ```
   OPENAI_API_KEY = "paste-your-key-here"
   EMBED_BACKEND = "1"
   ```
5. Deploy. The first start takes a few minutes (it installs packages, downloads the small embedding model and builds the search index).
6. Test: in the sidebar press "Check backend" (should report 2,063 ingredients and 30 interaction rows). Ask "Can I use retinol and vitamin C together?", then switch to "Check an ingredient list", use the example, press "Check list" and "Explain this product".

## Warnings

- **A public link lets anyone spend your OpenAI credit** on the chat screen. Set a monthly spending limit on the key in your OpenAI account before sharing the link.
- Free apps go to sleep when unused. Open the link a few minutes before a demo.
- Free apps have limited memory. If the app crashes while starting with a memory error, tell the team; the fallback is to demo from Colab (the notebook can expose the app through ngrok) and describe deployment as "prepared, not completed".

## If it does not work

- **Build fails on packages:** copy the last 20 lines of the log.
- **App says it cannot reach the backend:** check that the secret `EMBED_BACKEND = "1"` is spelled exactly like that, then open **Manage app > Logs** and look for a Python error.
- **Answers fail with an OpenAI error:** check the key name `OPENAI_API_KEY` and that the account has credit.
