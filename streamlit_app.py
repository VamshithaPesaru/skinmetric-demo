"""
Streamlit frontend for the Skincare Ingredient Interaction Checker.
Talks to the FastAPI backend (app.py):  POST {API_URL}/query   GET {API_URL}/health
Run:  API_URL=http://127.0.0.1:8000 streamlit run streamlit_app.py
"""
import os
import requests
import streamlit as st

DEFAULT_API = os.environ.get("API_URL", "http://127.0.0.1:8000")
EXAMPLES = [
    "Can I use retinol and vitamin C together?",
    "Is it ok to mix niacinamide and vitamin C?",
    "Does glycolic acid make my skin sun sensitive?",
    "What is phenoxyethanol?",
    "Can I use adapalene with benzoyl peroxide?",
]
DISCLAIMER = "General information only, not medical or dermatological advice."

st.set_page_config(page_title="Skincare Ingredient Checker", page_icon="🧴")
st.title("Skincare Ingredient Interaction Checker")
st.caption("Answers come only from our sources: EU CosIng, Open Beauty Facts and a small, sourced interaction table.")
st.info(DISCLAIMER)

if "history" not in st.session_state:
    st.session_state.history = []
if "pending" not in st.session_state:
    st.session_state.pending = None

with st.sidebar:
    st.header("Settings")
    api_url = st.text_input("Backend URL", DEFAULT_API).rstrip("/")
    if st.button("Check backend"):
        try:
            h = requests.get(f"{api_url}/health", timeout=10).json()
            st.success(f"Backend OK: {h['ingredient_entries']} ingredients, {h['interaction_rows']} interaction rows")
        except Exception as e:
            st.error(f"Cannot reach backend: {type(e).__name__}")
    st.header("Try an example")
    for ex in EXAMPLES:
        if st.button(ex, key="ex_" + ex):
            st.session_state.pending = ex
    if st.button("Clear conversation"):
        st.session_state.history = []
    st.caption("Limits: interaction table has 17 pairs, some sources are not yet verified. "
               "A missing interaction does not mean a combination is safe.")

def ask(question):
    """Call the backend; return (result_dict, error_message)."""
    try:
        r = requests.post(f"{api_url}/query", json={"question": question}, timeout=60)
    except requests.exceptions.ConnectionError:
        return None, "Could not connect to the backend. Is the FastAPI server running, and is the URL in the sidebar right?"
    except requests.exceptions.Timeout:
        return None, "The backend took too long to answer. Try again."
    if r.status_code == 200:
        return r.json(), None
    if r.status_code == 422:
        return None, "Please type a question between 3 and 500 characters."
    detail = ""
    try:
        detail = r.json().get("detail", "")
    except Exception:
        pass
    return None, f"The backend returned an error ({r.status_code}). {detail}"

def show_source(s):
    if s["type"] == "interaction":
        status = "verified" if s.get("verified") else "source not yet verified"
        st.markdown(f"**[{s['tag']}] {s['name']}**  \nEvidence: {s.get('evidence_strength', '?')} · {status}")
        for u in [x.strip() for x in str(s.get("source_url", "")).split(";") if x.strip()]:
            st.markdown(f"- [{u}]({u})")
    else:
        st.markdown(f"**[{s['tag']}] {s['name']}**  \nFrom: {s.get('origin', 'ingredient database')}")

def show_result(res):
    st.markdown(res["answer"])
    if res.get("recognized_ingredients"):
        st.caption("Ingredients recognised: " + ", ".join(res["recognized_ingredients"]))
    cited = [s for s in res["sources"] if s.get("cited")]
    other = [s for s in res["sources"] if not s.get("cited")]
    if cited:
        with st.expander(f"Sources used ({len(cited)})", expanded=True):
            for s in cited:
                show_source(s)
    if other:
        with st.expander(f"Also retrieved, not used in the answer ({len(other)})"):
            for s in other:
                show_source(s)
    st.caption(f"Answered in {res['latency_ms']} ms")

for turn in st.session_state.history:
    with st.chat_message("user"):
        st.write(turn["question"])
    with st.chat_message("assistant"):
        if turn["error"]:
            st.error(turn["error"])
        else:
            show_result(turn["result"])

typed = st.chat_input("Ask about an ingredient or a combination...")
question = typed or st.session_state.pending
st.session_state.pending = None
if question:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching sources..."):
            result, error = ask(question)
        if error:
            st.error(error)
        else:
            show_result(result)
    st.session_state.history.append({"question": question, "result": result, "error": error})
