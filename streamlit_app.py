"""
Streamlit frontend for the Skincare Ingredient Interaction Checker.
Talks to the FastAPI backend (app.py):  POST {API_URL}/query   GET {API_URL}/health
Run:  API_URL=http://127.0.0.1:8000 streamlit run streamlit_app.py
"""
import os
import requests
import streamlit as st

DEFAULT_API = os.environ.get("API_URL", "http://127.0.0.1:8000")


@st.cache_resource(show_spinner="Starting the backend (the first load takes a minute or two)...")
def start_embedded_backend(port=8001):
    """For hosts that run only one process (Streamlit Community Cloud): run the FastAPI backend in a thread of this app."""
    import threading, time, urllib.request
    import uvicorn
    import app as backend
    server = uvicorn.Server(uvicorn.Config(backend.create_app(), host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            return f"http://127.0.0.1:{port}"
        except Exception:
            time.sleep(2)
    raise RuntimeError("The embedded backend did not start in time.")


if os.environ.get("EMBED_BACKEND") == "1":      # set EMBED_BACKEND = "1" in the host's secrets to use this mode
    DEFAULT_API = start_embedded_backend()
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
    mode = st.radio("What do you want to do?", ["Ask a question", "Check an ingredient list"])
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
    st.caption("Limits: interaction table has 30 pairs, and the team has not yet verified every source. "
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
    pairs = [x for x in res["sources"] if x["type"] == "interaction" and x.get("cited")]
    if pairs:
        n_ver = sum(bool(x.get("verified")) for x in pairs)
        st.caption(f"Interaction sources used: {len(pairs)}. Verified by the team: {n_ver} of {len(pairs)}. "
                   "Open the sources below to read the original pages.")
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

LABEL_EXAMPLE = "Aqua, Glycerin, Retinol 0.5%, Niacinamide, Phenoxyethanol, Parfum"

def check_label(text, endpoint="label"):
    """Call POST /label (or /explain); return (result_dict, error_message)."""
    try:
        r = requests.post(f"{api_url}/{endpoint}", json={"ingredients": text}, timeout=60)
    except requests.exceptions.ConnectionError:
        return None, "Could not connect to the backend. Is the FastAPI server running, and is the URL in the sidebar right?"
    except requests.exceptions.Timeout:
        return None, "The backend took too long to answer. Try again."
    if r.status_code == 200:
        return r.json(), None
    if r.status_code == 422:
        return None, "Please paste an ingredient list (at least a few characters, at most 4000)."
    if r.status_code == 503:
        return None, "The risk model is not loaded on the backend (risk_model.joblib is missing)."
    if r.status_code == 502:
        return None, "The language model could not be reached. Check the OpenAI key and credit on the backend."
    return None, f"The backend returned an error ({r.status_code})."

RISK_COLOR = {"low": "green", "medium": "orange", "high": "red"}

def show_risk(risk):
    st.subheader("Estimated irritation risk")
    c1, c2 = st.columns(2)
    c1.metric("Level", risk["level"].capitalize())
    c2.metric("Score (0 to 100)", risk["score"])
    st.progress(min(max(risk["score"], 0), 100) / 100)
    p = risk["probabilities"]
    st.caption("Model confidence: " + " · ".join(f"{k} {int(round(100 * p.get(k, 0)))}%" for k in ("low", "medium", "high")))
    flagged = risk["flagged_allergens"] + risk["flagged_irritants"]
    if flagged:
        st.write("**Ingredients flagged by our rule:** " + ", ".join(flagged) +
                 f"  (rule-based level from these flags: {risk['rule_level']})")
    else:
        st.write("**No fragrance allergens or common irritants from our reference list were found.**")
    for n in risk["notes"]:
        st.warning(n)
    st.caption(risk["basis"])

def show_pair(p):
    status = "source verified by team" if p.get("verified") else "source not yet verified"
    st.markdown(f"**{p['ingredients']}** (`{p['pair_id']}`)  \n"
                f"Type: {p['interaction_type']} · Severity: {p['severity']} · Evidence: {p['evidence_strength']} · {status}")
    st.write(p["explanation"])
    if p.get("caveat"):
        st.caption("Caveat: " + p["caveat"])
    for u in [x.strip() for x in str(p.get("source_url", "")).split("|") if x.strip()]:
        st.markdown(f"- [{u}]({u})")

def show_label_result(res):
    n_rec, n_unrec = len(res["recognized"]), len(res["unrecognized"])
    st.markdown(f"**{res['n_items']} items found: {n_rec} recognised, {n_unrec} not recognised.**")
    if res.get("risk"):
        show_risk(res["risk"])
    st.subheader("Documented interactions between these ingredients")
    if res["pairs"]:
        for p in res["pairs"]:
            with st.container(border=True):
                show_pair(p)
    else:
        st.info("No documented interaction between these ingredients was found in our table.")
    st.warning(res["note"])
    if res["condition_notes"]:
        st.subheader("Sun exposure and other notes")
        for p in res["condition_notes"]:
            with st.container(border=True):
                show_pair(p)
    st.subheader("Recognised ingredients")
    if res["recognized"]:
        st.dataframe([{"On label": x["label_name"], "Matched to": x["cosing_inci"] or x["matched_as"],
                       "Function (EU CosIng)": x["function"], "EU restriction": x["eu_restriction"]}
                      for x in res["recognized"]], hide_index=True)
    if res["unrecognized"]:
        st.subheader("Not recognised")
        st.write(", ".join(res["unrecognized"]))
        st.caption("These are not in our ingredient data, so we cannot say anything about them.")
    st.caption(f"Checked in {res['latency_ms']} ms · {res['disclaimer']}")

if mode == "Check an ingredient list":
    st.subheader("Check a product's ingredient list")
    st.write("Copy the ingredient list from a product label and paste it here. "
             "We look up each ingredient and show any documented interactions between them.")
    def use_example():
        st.session_state["label_box"] = LABEL_EXAMPLE
    text = st.text_area("Ingredient list", height=160, placeholder=LABEL_EXAMPLE, key="label_box")
    c1, c2 = st.columns(2)
    c2.button("Use an example", on_click=use_example)
    if c1.button("Check list", type="primary"):
        st.session_state.pop("label_explain", None)
        st.session_state.pop("label_error", None)
        if not text.strip():
            st.session_state["label_error"] = "Paste an ingredient list first."
            st.session_state.pop("label_res", None)
        else:
            with st.spinner("Checking ingredients..."):
                res, err = check_label(text)
            if err:
                st.session_state["label_error"] = err
                st.session_state.pop("label_res", None)
            else:
                st.session_state["label_res"] = res
                st.session_state["label_text_checked"] = text
    if st.session_state.get("label_error"):
        st.error(st.session_state["label_error"])
    res = st.session_state.get("label_res")
    if res:
        show_label_result(res)
        st.divider()
        st.subheader("Explain it in plain language")
        st.write("The chatbot explains the risk estimate and any documented interactions, using only the data shown above.")
        if st.button("Explain this product"):
            with st.spinner("Writing the explanation..."):
                ex, err = check_label(st.session_state["label_text_checked"], endpoint="explain")
            if err:
                st.error(err)
            else:
                st.session_state["label_explain"] = ex
        ex = st.session_state.get("label_explain")
        if ex:
            st.markdown(ex["answer"])
            used = [s for s in ex["sources"] if s.get("cited")]
            if used:
                with st.expander("Sources used"):
                    for s in used:
                        extra = f" · {s['source_url']}" if s.get("source_url") else ""
                        st.markdown(f"- **[{s['tag']}]** {s['name']} ({s['type']}){extra}")
            st.caption(f"{ex['latency_ms']} ms · {ex['disclaimer']}")
    st.stop()

if not st.session_state.history and not st.session_state.pending:
    st.markdown("#### Ask about a skincare ingredient or a combination")
    st.write("I answer only from our sources, cite them, and say so when I have no documented information. "
             "To check a whole product, switch to **Check an ingredient list** in the sidebar.")
    for ex in EXAMPLES[:3]:
        if st.button(ex, key="welcome_" + ex, use_container_width=True):
            st.session_state.pending = ex
            st.rerun()

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
