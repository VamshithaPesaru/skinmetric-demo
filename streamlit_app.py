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

st.set_page_config(page_title="SkinMetric", page_icon="🧴")

import urllib.parse

def _svg_uri(svg):
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg)

def _scene():
    """Original, generic mini skincare products (serum, tube, jar, pump): no brand names, no logos."""
    g = lambda i, c1, c2: f'<linearGradient id="{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>'
    rim = lambda x, y, h: f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="#fff" fill-opacity=".65"/>'
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="470" height="230" viewBox="0 0 470 230">
<defs>{g('sg','#E3EEE7','#9CBFAF')}{g('iv','#FFFBF0','#E9DCC0')}{g('em','#3F7566','#1F3A34')}{g('sa','#F3E3D8','#DDBBA6')}{g('go','#F1DCA8','#B8935A')}{g('wh','#FFFFFF','#F6F1E8')}
<filter id="b"><feGaussianBlur stdDeviation="7"/></filter></defs>
<ellipse cx="235" cy="219" rx="220" ry="9" fill="#2F5B4F" fill-opacity=".28" filter="url(#b)"/>
<g stroke="#fff" stroke-opacity=".85" stroke-width="1.2"><rect x="28" y="84" width="78" height="128" rx="20" fill="url(#sg)"/><rect x="50" y="54" width="34" height="34" fill="#C9A66B"/>
<rect x="54" y="14" width="26" height="44" rx="12" fill="url(#go)"/></g>{rim(38,100,86)}
<ellipse cx="67" cy="152" rx="21" ry="26" fill="url(#wh)" fill-opacity=".95"/><path d="M67 136 C75 147 75 158 67 168 C59 158 59 147 67 136Z" fill="#B8935A"/>
<g stroke="#fff" stroke-opacity=".85" stroke-width="1.2"><path d="M132 212 L142 90 L216 90 L226 212 Z" fill="url(#em)"/><rect x="138" y="62" width="84" height="30" rx="8" fill="url(#go)"/>
<rect x="152" y="38" width="56" height="26" rx="8" fill="#A9814A"/></g><rect x="149" y="118" width="64" height="46" rx="10" fill="url(#iv)" fill-opacity=".96"/>
<path d="M181 128 C190 136 190 148 181 156 C172 148 172 136 181 128Z" fill="none" stroke="#B8935A" stroke-width="2"/><path d="M181 134 L181 152" stroke="#B8935A" stroke-width="1.6"/>
<g stroke="#fff" stroke-opacity=".85" stroke-width="1.2"><rect x="250" y="136" width="100" height="76" rx="18" fill="url(#iv)"/><rect x="244" y="108" width="112" height="34" rx="13" fill="url(#go)"/></g>
<rect x="258" y="118" width="84" height="6" rx="3" fill="#fff" fill-opacity=".6"/>{rim(262,148,48)}
<circle cx="302" cy="176" r="15" fill="url(#wh)" fill-opacity=".95"/><circle cx="302" cy="176" r="8" fill="none" stroke="#B8935A" stroke-width="2"/>
<g stroke="#fff" stroke-opacity=".85" stroke-width="1.2"><rect x="376" y="92" width="68" height="120" rx="18" fill="url(#sa)"/><rect x="400" y="60" width="20" height="36" fill="#C9A66B"/>
<rect x="388" y="44" width="52" height="18" rx="9" fill="url(#go)"/><rect x="376" y="48" width="18" height="10" rx="4" fill="url(#go)"/></g>{rim(386,106,80)}
<circle cx="410" cy="152" r="14" fill="url(#wh)" fill-opacity=".95"/><path d="M410 142 C416 148 416 156 410 162 C404 156 404 148 410 142Z" fill="#2F5B4F"/>
</svg>"""
    return _svg_uri(svg)

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600&family=Jost:wght@300;400;500;600&display=swap');
html, body, .stApp, .stApp button, .stApp input, .stApp textarea {font-family: 'Jost', 'Helvetica Neue', Arial, sans-serif; font-weight: 400; letter-spacing: .2px;}
.stApp {background:
    radial-gradient(1000px 640px at 0% 0%, rgba(205,224,212,.85) 0%, rgba(205,224,212,0) 62%),
    radial-gradient(900px 640px at 100% 4%, rgba(236,220,186,.7) 0%, rgba(236,220,186,0) 62%),
    radial-gradient(1000px 700px at 100% 100%, rgba(226,205,190,.6) 0%, rgba(226,205,190,0) 62%),
    radial-gradient(900px 600px at 0% 100%, rgba(214,230,224,.7) 0%, rgba(214,230,224,0) 62%),
    linear-gradient(170deg, #FBF8F1 0%, #F6F3EA 100%);
  background-attachment: fixed; color-scheme: light;}
.stApp::after {content: ""; position: fixed; right: 26px; bottom: 14px; width: 440px; height: 215px; pointer-events: none; z-index: 0;
  background: url("__SCENE__") no-repeat right bottom / contain; filter: drop-shadow(0 18px 24px rgba(31,58,52,.22));
  animation: floaty 8s ease-in-out infinite; opacity: .82;}
@keyframes floaty {0%,100% {transform: translateY(0);} 50% {transform: translateY(-8px);}}
@media (max-width: 1100px) {.stApp::after {display: none;}}
.stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp div[data-testid="stMarkdownContainer"], .stApp h2, .stApp h3,
.stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricLabel"], .stApp summary, .stApp th, .stApp td {color: #2B3A36;}
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p {color: #6E7C76;}
.stApp a {color: #1F6B5B !important; text-decoration-color: rgba(184,147,90,.8);}
.stApp [data-testid="stHeader"] {background: transparent;}
.stApp [data-testid="stHeader"] * {color: #55655F !important;}
.block-container {padding-top: 2.8rem; position: relative; z-index: 1; max-width: 840px;}
h1 {font-family: 'Cormorant Garamond', Georgia, serif !important; font-size: 5.4rem !important; font-weight: 600 !important; letter-spacing: 1px; line-height: 1 !important;
    background: linear-gradient(100deg, #17302A 0%, #2F5B4F 55%, #B8935A 100%); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; padding-bottom: 6px;}
h2, h3 {font-family: 'Cormorant Garamond', Georgia, serif !important; font-weight: 600 !important; font-size: 2rem !important; color: #1F3A34 !important;
    border-bottom: 1px solid rgba(184,147,90,.55); padding-bottom: 6px;}
.tagline {font-family: 'Jost', sans-serif; font-size: .95rem; font-weight: 500; letter-spacing: 6px; color: #A9814A; margin: 2px 0 4px 4px;}
.rule {width: 84px; height: 2px; background: linear-gradient(90deg, #B8935A, rgba(184,147,90,0)); margin: 8px 0 14px 4px;}
[data-testid="stSidebar"] {background: linear-gradient(185deg, #1F3A34 0%, #17302A 60%, #12261F 100%); border-right: 1px solid rgba(184,147,90,.6); box-shadow: 8px 0 34px rgba(18,38,31,.28);}
.stApp [data-testid="stSidebar"] * {color: #EFE9DA;}
.stApp [data-testid="stSidebar"] h2, .stApp [data-testid="stSidebar"] h3 {font-size: 1.55rem !important; color: #F1DCA8 !important; border-bottom: 1px solid rgba(241,220,168,.4);}
.stApp [data-testid="stSidebar"] [data-testid="stCaptionContainer"], .stApp [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color: #AFC2B8;}
.stApp textarea, .stApp input {background: rgba(255,255,255,.95) !important; color: #2B3A36 !important; border-radius: 12px !important; border: 1px solid rgba(184,147,90,.55) !important;}
.stApp [data-testid="stSidebar"] input, .stApp [data-testid="stSidebar"] textarea {color: #2B3A36 !important;}
.stApp [data-testid="stTextInputRootElement"], .stApp [data-testid="stTextInputRootElement"] > div, .stApp [data-testid="stTextArea"] > div, .stApp [data-testid="stTextArea"] > div > div,
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="textarea"] {background: rgba(255,255,255,.95) !important; border-radius: 12px !important;}
[data-testid="stExpander"] details, [data-testid="stExpander"] summary, [data-testid="stExpander"] summary:hover {background: transparent !important; color: #2B3A36 !important;}
.stApp textarea:focus, .stApp input:focus {border-color: #B8935A !important; box-shadow: 0 0 0 3px rgba(184,147,90,.22) !important;}
.stApp textarea::placeholder, .stApp input::placeholder {color: #9AA6A0 !important; opacity: 1;}
[data-testid="stChatInput"], [data-testid="stChatInput"] > div {background: rgba(255,255,255,.97) !important; border-radius: 16px !important;}
[data-testid="stChatInput"] {border: 1px solid rgba(184,147,90,.6); box-shadow: 0 10px 30px rgba(31,58,52,.14);}
[data-testid="stChatInput"] textarea {box-shadow: none !important; border: none !important; background: transparent !important;}
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] {background: transparent !important;}
[data-testid="stChatMessage"], [data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stMetric"] {
    background: rgba(255,255,255,.72) !important; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(184,147,90,.35) !important; border-radius: 16px !important; box-shadow: 0 10px 30px rgba(31,58,52,.08);}
[data-testid="stChatMessage"] {padding: 14px 18px; margin-bottom: 12px;}
[data-testid="stMetric"] {padding: 10px 16px; border-left: 4px solid #B8935A !important;}
[data-testid="stMetricValue"] {font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 600;}
[data-testid="stAlert"], [data-testid="stAlertContainer"], [data-testid="stAlert"] > div, div[role="alert"] {border-radius: 14px; background: rgba(255,255,255,.78) !important;
    border: 1px solid rgba(184,147,90,.35); box-shadow: 0 6px 22px rgba(31,58,52,.06);}
[data-testid="stTable"] table {border-collapse: collapse; background: rgba(255,255,255,.75); border-radius: 12px; overflow: hidden;}
[data-testid="stTable"] th {background: #DDE9E1; color: #1F3A34; font-weight: 600;}
[data-testid="stTable"] td, [data-testid="stTable"] th {border: 1px solid rgba(184,147,90,.28) !important; padding: 8px 12px;}
div.stButton > button {background: rgba(255,255,255,.85); color: #1F3A34; border: 1px solid rgba(184,147,90,.9); border-radius: 12px; font-weight: 500; letter-spacing: .4px;
    transition: all .2s ease;}
div.stButton > button:hover {background: #1F3A34; color: #F1DCA8; border-color: #1F3A34; transform: translateY(-1px); box-shadow: 0 10px 22px rgba(31,58,52,.25);}
div.stButton > button[kind="primary"] {background: linear-gradient(100deg, #1F3A34 0%, #2F5B4F 100%); color: #F1DCA8; border: 1px solid #B8935A; font-weight: 600; box-shadow: 0 8px 20px rgba(31,58,52,.28);}
.stApp [data-testid="stSidebar"] div.stButton > button {background: rgba(255,255,255,.05); color: #EFE9DA; border: 1px solid rgba(241,220,168,.55);}
.stApp [data-testid="stSidebar"] div.stButton > button:hover {background: #F1DCA8; color: #1F3A34; border-color: #F1DCA8;}
div.stButton > button * {color: #1F3A34;}
div.stButton > button:hover *, div.stButton > button[kind="primary"] * {color: #F1DCA8 !important;}
.stApp [data-testid="stSidebar"] div.stButton > button * {color: #EFE9DA;}
.stApp [data-testid="stSidebar"] div.stButton > button:hover * {color: #1F3A34 !important;}
[data-testid="stProgressBarTrack"] {background: rgba(31,58,52,.1) !important; border-radius: 999px;}
[data-testid="stProgressBarTrack"] > div {background: linear-gradient(90deg, #7FB59F, #D9BE7E, #C9705F) !important; border-radius: 999px;}
.badge {display: inline-block; padding: 7px 22px; border-radius: 999px; color: #fff !important; font-weight: 600; font-size: 1rem; letter-spacing: 1.4px; box-shadow: 0 6px 16px rgba(31,58,52,.15);}
.badge-low {background: linear-gradient(100deg, #2F7F66, #6FB59A);} .badge-medium {background: linear-gradient(100deg, #C9A24E, #E6CC8E); color: #3B2E0E !important;} .badge-high {background: linear-gradient(100deg, #B9503F, #D98471);}

/* ---- premium polish ---- */
[data-testid="stToolbar"], #MainMenu, footer, [data-testid="stDecoration"] {visibility: hidden; height: 0;}
::selection {background: rgba(184,147,90,.35);}
* {scrollbar-width: thin; scrollbar-color: #C9A66B transparent;}
@keyframes riseIn {from {opacity: 0; transform: translateY(14px);} to {opacity: 1; transform: translateY(0);}}
.block-container > div > div, .block-container [data-testid="stVerticalBlock"] > div {animation: riseIn .7s cubic-bezier(.2,.7,.2,1) both;}
[data-testid="stChatMessage"], [data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stMetric"], [data-testid="stAlert"], [data-testid="stAlertContainer"] {
    background: linear-gradient(rgba(255,253,248,.93), rgba(255,253,248,.93)) padding-box, linear-gradient(135deg, #F1DCA8 0%, #B8935A 45%, #EBD9A8 100%) border-box !important;
    border: 1px solid transparent !important; box-shadow: 0 18px 40px -18px rgba(31,58,52,.35), 0 2px 6px rgba(31,58,52,.05) !important;}
[data-testid="stAlert"] > div, div[role="alert"] {background: transparent !important; border: none !important; box-shadow: none !important;}
[data-testid="stMetric"] {border-left: 1px solid transparent !important;}
[data-testid="stMetricLabel"] p {text-transform: uppercase; letter-spacing: 2.2px; font-size: .72rem !important; color: #A9814A !important; font-weight: 500;}
[data-testid="stMetricValue"] {font-size: 2.6rem !important;}
.stApp textarea, .stApp input {box-shadow: inset 0 2px 6px rgba(31,58,52,.06) !important;}
.hero-divider {display: flex; align-items: center; gap: 12px; margin: 6px 0 18px 2px;}
.hero-divider .l {height: 1px; width: 90px; background: linear-gradient(90deg, #B8935A, rgba(184,147,90,0));}
.hero-divider .d {width: 8px; height: 8px; background: #B8935A; transform: rotate(45deg);}
.brand {font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-weight: 600; font-size: 1.9rem; letter-spacing: 1px; color: #F1DCA8 !important; margin: 4px 0 2px;}
.brand-sub {font-size: .68rem; letter-spacing: 4px; color: #AFC2B8 !important; margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px solid rgba(241,220,168,.35);}
[class*="st-key-welcome_"] button {justify-content: flex-start !important; text-align: left; padding: 16px 22px; border-radius: 14px; background: linear-gradient(rgba(255,253,248,.95), rgba(255,253,248,.95)) padding-box, linear-gradient(135deg, #F1DCA8, #B8935A, #EBD9A8) border-box !important;
    border: 1px solid transparent !important; position: relative; box-shadow: 0 14px 30px -16px rgba(31,58,52,.4);}
[class*="st-key-welcome_"] button p {font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.28rem !important; font-weight: 600; text-align: left; width: 100%;}
[class*="st-key-welcome_"] button::after {content: "\\2192"; position: absolute; right: 22px; top: 50%; transform: translateY(-50%); color: #B8935A; font-size: 1.3rem; transition: transform .2s ease;}
[class*="st-key-welcome_"] button:hover::after {transform: translate(6px, -50%); color: #F1DCA8;}
[class*="st-key-welcome_"] button:hover {transform: translateY(-2px);}
/* ---- typography polish ---- */
.stApp p, .stApp li, .stApp label, .stApp td, .stApp th, .stApp [data-testid="stMarkdownContainer"] {font-family: 'Jost', 'Helvetica Neue', Arial, sans-serif;}
html, body, .stApp {-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility; font-feature-settings: "kern", "liga";}
.stApp p, .stApp li, .stApp label, .stApp summary, .stApp td {font-weight: 400; line-height: 1.7; letter-spacing: .25px;}
[data-testid="stChatMessage"] p {font-size: 1.04rem; line-height: 1.75;}
.stApp [data-testid="stCaptionContainer"] p {font-size: .86rem; letter-spacing: .5px; font-weight: 400;}
h2, h3 {letter-spacing: .6px; font-size: 2.1rem !important;}
.stApp [data-testid="stSidebar"] h2, .stApp [data-testid="stSidebar"] h3 {font-family: 'Jost', sans-serif !important; font-size: .78rem !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 4px; padding-bottom: 10px;}
.stApp [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p, .stApp [data-testid="stSidebar"] label p {font-size: .74rem; text-transform: uppercase; letter-spacing: 2.4px; font-weight: 500;}
.stApp [data-testid="stSidebar"] [role="radiogroup"] label p {font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.22rem !important; font-weight: 600; text-transform: none; letter-spacing: .4px;}
.stApp [data-testid="stSidebar"] div.stButton > button p {font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.12rem; font-weight: 600; letter-spacing: .3px; line-height: 1.3;}
.stApp [data-testid="stSidebar"] div.stButton > button {padding: 10px 14px; border-radius: 14px;}
div.stButton > button p {letter-spacing: .6px;}
div.stButton > button[kind="primary"] p {font-size: .82rem; font-weight: 600; text-transform: uppercase; letter-spacing: 2.4px;}
[data-testid="stChatInput"] textarea {font-size: 1.02rem; letter-spacing: .3px;}
[data-testid="stExpander"] summary p {font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.2rem; font-weight: 600; letter-spacing: .4px;}
[data-testid="stTable"] th {font-size: .74rem; text-transform: uppercase; letter-spacing: 2.2px; font-weight: 500;}
.badge {font-family: 'Jost', sans-serif; font-size: .8rem; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; padding: 8px 26px;}
.tagline {font-size: .82rem; letter-spacing: 7px; font-weight: 500;}
h4 {font-family: 'Cormorant Garamond', Georgia, serif !important; font-weight: 600 !important; font-size: 2.1rem !important; letter-spacing: .6px; color: #1F3A34 !important; border-bottom: 1px solid rgba(184,147,90,.55); padding-bottom: 6px;}
h1 {font-size: 5.6rem !important; font-weight: 500 !important; letter-spacing: 2px;}
.brand {font-weight: 500; font-size: 2.1rem;}
</style>
""".replace("__SCENE__", _scene().replace('"', "%22"))
st.markdown(STYLE, unsafe_allow_html=True)
st.title("SkinMetric")
st.markdown('<div class="tagline">SKINCARE INGREDIENT INTERACTION CHECKER</div><div class="hero-divider"><span class="l"></span><span class="d"></span></div>', unsafe_allow_html=True)
st.caption("Answers come only from our sources: EU CosIng, Open Beauty Facts and a small, sourced interaction table.")
st.info(DISCLAIMER)

if "history" not in st.session_state:
    st.session_state.history = []
if "pending" not in st.session_state:
    st.session_state.pending = None

with st.sidebar:
    st.markdown('<div class="brand">SkinMetric</div><div class="brand-sub">INGREDIENT INTELLIGENCE</div>', unsafe_allow_html=True)
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
    st.caption("Limits: interaction table has 30 pairs, and a teammate has checked each source page. "
               "A missing interaction does not mean a combination is safe.")

MAX_LABEL_CHARS, MIN_Q_CHARS, MAX_Q_CHARS = 4000, 3, 500

def question_problem(q):
    """Return a plain message if the question cannot be sent to the backend, else None."""
    q = (q or "").strip()
    if len(q) < MIN_Q_CHARS:
        return f"Please type a question of at least {MIN_Q_CHARS} characters, for example: Can I use retinol with vitamin C?"
    if len(q) > MAX_Q_CHARS:
        return f"That question is {len(q)} characters long. The limit is {MAX_Q_CHARS}. Please shorten it."
    return None

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
    lvl = risk["level"] if risk["level"] in RISK_COLOR else "medium"
    st.markdown(f'<span class="badge badge-{lvl}">{lvl.upper()} RISK (estimate)</span>', unsafe_allow_html=True)
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
        st.table([{"On label": x["label_name"], "Matched to": x["cosing_inci"] or x["matched_as"],
                   "Function (EU CosIng)": x["function"], "EU restriction": x["eu_restriction"]}
                  for x in res["recognized"]])
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
        elif len(text) > MAX_LABEL_CHARS:
            st.session_state["label_error"] = (f"That list is {len(text)} characters long. The limit is {MAX_LABEL_CHARS}. "
                                               "Paste only the ingredient list, not the whole label.")
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
        problem = question_problem(question)
        if problem:
            result, error = None, problem
        else:
            with st.spinner("Searching sources..."):
                result, error = ask(question)
        if error:
            st.error(error)
        else:
            show_result(result)
    st.session_state.history.append({"question": question, "result": result, "error": error})
