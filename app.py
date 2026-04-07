import streamlit as st
import google.generativeai as genai
import json, os, uuid, re, sqlite3, time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from google.api_core import exceptions as google_exceptions

# Load local .env
load_dotenv()

# ── MUST BE FIRST ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DialogueBot · ABHI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed", # Hide the standard sidebar
)

# ── DATABASE & PATHS ─────────────────────────────────────────────────────────────
DATA_DIR  = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "dialogue_store.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Sessions table
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT,
        mode TEXT,
        about TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    # Messages table
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )""")
    conn.commit()
    conn.close()

init_db()

KB_FILE = DATA_DIR / "knowledge_base.json"
if not KB_FILE.exists():
    KB_FILE.write_text(json.dumps({"scripts": [], "dialogues": []}, ensure_ascii=False))

# ── CSS ──────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@300;400;500;600&display=swap');

*, html, body { font-family: 'Inter', sans-serif; box-sizing: border-box; }
#MainMenu, footer, header { visibility: hidden; }
.stApp { background: #0b0c10; color: #e2e4ed; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0f1117 !important;
    border-right: 1px solid #1c1f2e;
    padding-top: 0 !important;
}
[data-testid="stSidebar"] > div { padding: 0 !important; }

.sb-logo {
    padding: 22px 18px 14px;
    border-bottom: 1px solid #1c1f2e;
}
.sb-logo-text {
    font-family: 'Syne', sans-serif;
    font-size: 1.15rem; font-weight: 800;
    background: linear-gradient(135deg, #4f8ef7, #34c77b);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.sb-logo-sub { font-size: 0.72rem; color: #454860; margin-top: 2px; }

.sb-new-chat {
    margin: 14px 14px 10px;
}

.sb-section-label {
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: #3a3d55;
    padding: 10px 18px 6px;
}

.hist-card {
    margin: 3px 10px;
    padding: 9px 12px;
    border-radius: 8px;
    border: 1px solid transparent;
    cursor: pointer;
    transition: all 0.15s;
    background: transparent;
}
.hist-card:hover { background: #14172a; border-color: #1c1f2e; }
.hist-card.active { background: #14172a; border-color: #2a2f50; }
.hist-card-title { font-size: 0.8rem; font-weight: 500; color: #b0b3c8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hist-card-meta  { font-size: 0.68rem; color: #3a3d55; margin-top: 2px; }

/* ── Main layout ── */
.col-input  { padding-right: 16px; border-right: 1px solid #1c1f2e; }
.col-output { padding-left: 16px; }

/* ── Section labels ── */
.field-label {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #4f8ef7;
    margin-bottom: 6px; margin-top: 18px;
}
.field-label:first-child { margin-top: 0; }

/* ── Mode pills ── */
.mode-row { display: flex; gap: 8px; margin-bottom: 4px; }
.mode-pill {
    padding: 5px 14px; border-radius: 999px; font-size: 0.75rem;
    font-weight: 600; cursor: pointer; border: 1px solid #2a2f50;
    background: #14172a; color: #7a7d9a; transition: all 0.15s;
    display: inline-block;
}
.mode-pill.active-d { background: #1a2a50; color: #4f8ef7; border-color: #3a5090; }
.mode-pill.active-s { background: #1a2a20; color: #34c77b; border-color: #2a5040; }

/* ── Inputs ── */
.stTextArea textarea, .stTextInput input {
    background: #13151f !important;
    border: 1px solid #1e2235 !important;
    border-radius: 10px !important;
    color: #e2e4ed !important;
    font-size: 0.88rem !important;
    line-height: 1.6 !important;
    resize: vertical !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #4f8ef7 !important;
    box-shadow: 0 0 0 2px rgba(79,142,247,0.12) !important;
}
.stTextArea label, .stTextInput label, .stSelectbox label {
    display: none !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: #13151f !important;
    border: 1px solid #1e2235 !important;
    border-radius: 10px !important;
    color: #e2e4ed !important;
    font-size: 0.85rem !important;
}

/* ── Generate button ── */
.stButton > button {
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s !important;
    border: none !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f8ef7 0%, #34c77b 100%) !important;
    color: #fff !important;
    padding: 10px 0 !important;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(79,142,247,0.28) !important;
}
.stButton > button[kind="secondary"] {
    background: #13151f !important;
    border: 1px solid #1e2235 !important;
    color: #7a7d9a !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #4f8ef7 !important;
    color: #4f8ef7 !important;
}

/* ── Output header ── */
.out-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.05rem; font-weight: 700;
    color: #e2e4ed; margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1c1f2e;
    display: flex; align-items: center; gap: 8px;
}
.out-badge {
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; padding: 3px 8px; border-radius: 5px;
    background: #14172a; color: #4f8ef7; border: 1px solid #2a2f50;
}

/* ── Variation cards ── */
.var-wrap { margin-bottom: 10px; }
.var-card {
    border-radius: 12px;
    border: 1px solid #1e2235;
    overflow: hidden;
    transition: border-color 0.15s;
}
.var-card:hover { border-color: #2a2f50; }
.var-head {
    padding: 10px 16px;
    display: flex; align-items: center; gap: 10px;
    border-bottom: 1px solid #1e2235;
}
.var-letter {
    width: 24px; height: 24px; border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700; flex-shrink: 0;
}
.var-title-text { font-size: 0.82rem; font-weight: 600; }
.var-body { padding: 14px 16px; font-size: 0.84rem; line-height: 1.75; white-space: pre-wrap; color: #b0b3c8; }

/* variation colour themes */
.v1 .var-head { background: #0e1428; } .v1 .var-letter { background: #1a2a60; color: #4f8ef7; } .v1 .var-title-text { color: #4f8ef7; } .v1 { border-color: #1a2a60; }
.v2 .var-head { background: #0e1e18; } .v2 .var-letter { background: #1a3828; color: #34c77b; } .v2 .var-title-text { color: #34c77b; } .v2 { border-color: #1a3828; }
.v3 .var-head { background: #1e0e18; } .v3 .var-letter { background: #3a1a30; color: #d46ef7; } .v3 .var-title-text { color: #d46ef7; } .v3 { border-color: #3a1a30; }
.v4 .var-head { background: #1e1a0a; } .v4 .var-letter { background: #3a3010; color: #f7c34f; } .v4 .var-title-text { color: #f7c34f; } .v4 { border-color: #3a3010; }
.v5 .var-head { background: #0e1a1e; } .v5 .var-letter { background: #103040; color: #4fc7f7; } .v5 .var-title-text { color: #4fc7f7; } .v5 { border-color: #103040; }

/* ── Info box ── */
.info-box {
    background: #0f1117; border: 1px dashed #1e2235;
    border-radius: 12px; padding: 28px 20px;
    text-align: center; color: #3a3d55; font-size: 0.85rem; line-height: 1.7;
}
.info-box .icon { font-size: 2rem; margin-bottom: 10px; }

/* ── KB chips ── */
.kb-chip {
    font-size: 0.76rem; color: #7a7d9a;
    background: #13151f; border: 1px solid #1e2235;
    border-radius: 7px; padding: 5px 10px; margin: 2px 0;
    display: flex; align-items: center; gap: 6px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

hr { border-color: #1c1f2e !important; margin: 12px 0 !important; }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0b0c10; }
::-webkit-scrollbar-thumb { background: #1e2235; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────────
def ss(key, val):
    if key not in st.session_state:
        st.session_state[key] = val

ss("chat_id",    str(uuid.uuid4()))
ss("messages",   [])          # full conversation log
ss("mode",       "dialogue")  # "dialogue" | "script"
ss("variations", None)        # parsed list of dicts
ss("about_val",  "")
ss("instr_val",  "")
ss("lang_val",   "Hinglish (Hindi + English)")
ss("history_index", 0)
ss("llm_provider", "Gemini") # Gemini | OpenAI | Claude | Groq
ss("llm_model",    "gemini-1.5-flash")
ss("pending_new_chat", False)

# ── GEMINI ────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def discover_best_model(api_key):
    """List available models and pick the best one. Cached by API key."""
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
        
        # Priority list
        priorities = ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-pro"]
        for p in priorities:
            if p in models: return p
            
        # Fallback
        for m in models:
            if "gemini" in m.lower(): return m
        return models[0] if models else "models/gemini-1.5-flash"
    except Exception:
        return "models/gemini-1.5-flash"

@st.cache_resource
def get_model():
    # Search priority: st.secrets -> os.environ (includes .env)
    key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not key:
        key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    
    if not key:
        return None
    
    # Configure and pick the best model for this key
    best_model = discover_best_model(key)
    genai.configure(api_key=key)
    
    return genai.GenerativeModel(
        model_name=best_model,
        generation_config=genai.types.GenerationConfig(temperature=0.9, max_output_tokens=4096),
    )

# ── UNIFIED LLM ENGINE ────────────────────────────────────────────────────────────
def run_llm_request(system_prompt, user_prompt, provider=None, model=None):
    provider = provider or st.session_state.llm_provider
    
    if provider == "Gemini":
        gm = get_model()
        if not gm: return None
        try:
            resp = call_gemini_with_retry(gm.generate_content, f"{system_prompt}\n\n{user_prompt}")
            return resp.text
        except Exception as e:
            st.error(f"Gemini Error: {e}")
            return None

    elif provider == "OpenAI":
        try:
            import openai
        except ImportError:
            st.error("Model Error: 'openai' library is not installed in your venv. Run: pip install openai")
            return None
        key = os.environ.get("OPENAI_API_KEY")
        if not key: 
            st.error("Missing OPENAI_API_KEY in .env")
            return None
        client = openai.OpenAI(api_key=key)
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role":"system","content":system_prompt}, {"role":"user","content":user_prompt}]
            )
            return resp.choices[0].message.content
        except Exception as e:
            st.error(f"OpenAI Error: {e}")
            return None

    elif provider == "Claude":
        try:
            import anthropic
        except ImportError:
            st.error("Model Error: 'anthropic' library is not installed in your venv. Run: pip install anthropic")
            return None
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key: 
            st.error("Missing ANTHROPIC_API_KEY in .env")
            return None
        client = anthropic.Anthropic(api_key=key)
        try:
            resp = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role":"user","content":user_prompt}]
            )
            return resp.content[0].text
        except Exception as e:
            st.error(f"Claude Error: {e}")
            return None

    elif provider == "Groq/Meta":
        try:
            import groq
        except ImportError:
            st.error("Model Error: 'groq' library is not installed in your venv. Run: pip install groq")
            return None
        key = os.environ.get("GROQ_API_KEY")
        if not key: 
            st.error("Missing GROQ_API_KEY in .env")
            return None
        client = groq.Groq(api_key=key)
        try:
            resp = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role":"system","content":system_prompt}, {"role":"user","content":user_prompt}]
            )
            return resp.choices[0].message.content
        except Exception as e:
            st.error(f"Groq Error: {e}")
            return None
    
    return None

def call_gemini_with_retry(func, *args, **kwargs):
    """Retries a Gemini call on 429 errors."""
    max_retries = 3
    for i in range(max_retries):
        try:
            return func(*args, **kwargs)
        except google_exceptions.ResourceExhausted as e:
            if i < max_retries - 1:
                wait_time = (i + 1) * 3
                st.info(f"⏳ Rate limit hit. Retrying in {wait_time}s... (Attempt {i+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise e
        except Exception as e:
            raise e

# ── DATA HELPERS ─────────────────────────────────────────────────────────────────
# ── DATABASE HELPERS ────────────────────────────────────────────────────────────
def db_save_session(sid, title, mode, about):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO sessions (id, title, mode, about) VALUES (?, ?, ?, ?)",
              (sid, title, mode, about))
    conn.commit()
    conn.close()

def db_save_message(sid, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
              (sid, role, content))
    conn.commit()
    conn.close()

def db_get_sessions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, mode, timestamp FROM sessions ORDER BY timestamp DESC LIMIT 15")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "mode": r[2], "timestamp": r[3]} for r in rows]

def db_get_messages(sid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (sid,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def load_kb():
    try:
        return json.loads(KB_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"scripts": [], "dialogues": []}

def save_kb(kb):
    try:
        KB_FILE.write_text(json.dumps(kb, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False

def load_chat(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT title, mode, about FROM sessions WHERE id = ?", (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        st.session_state.chat_id    = chat_id
        st.session_state.messages   = db_get_messages(chat_id)
        st.session_state.mode       = row[1]
        st.session_state.about_val  = row[2]
        st.session_state.variations = None
        for m in reversed(st.session_state.messages):
            if "## VARIATION" in m["content"]:
                st.session_state.variations = parse_variations(m["content"])
                break

def start_new_chat():
    st.session_state.chat_id    = str(uuid.uuid4())
    st.session_state.messages   = []
    st.session_state.variations = None
    st.session_state.about_val  = ""
    st.session_state.instr_val  = ""
    st.session_state.history_index = 0
    # Force clear widgets
    if "about_input" in st.session_state: st.session_state.about_input = ""
    if "instr_input" in st.session_state: st.session_state.instr_input = ""

# ── PARSING ───────────────────────────────────────────────────────────────────────
VARIATION_LABELS = ["a", "b", "c", "d", "e"]
VAR_CLASSES      = ["v1", "v2", "v3", "v4", "v5"]

def parse_variations(raw: str):
    parts = re.split(r'##\s*VARIATION\s*\d+[:\.\-]?\s*', raw, flags=re.IGNORECASE)
    out = []
    for part in parts[1:]:
        lines   = part.strip().split('\n')
        title   = lines[0].strip().lstrip('#').strip()
        content = '\n'.join(lines[1:]).strip()
        out.append({"title": title, "content": content})
    return out if out else [{"title": "Output", "content": raw.strip()}]

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────────
def build_system(mode: str, kb: dict, about: str) -> str:
    today = datetime.now().strftime("%B %d, %Y")

    client_ctx = f"\n\nCLIENT CONTEXT:\n{about}" if about.strip() else ""

    kb_ref = ""
    if mode == "dialogue" and kb.get("dialogues"):
        items  = "\n\n---\n".join(f"[{d['name']}]\n{d['content']}" for d in kb["dialogues"][-5:])
        kb_ref = f"\n\nREFERENCE DIALOGUES FROM KNOWLEDGE BASE:\n{items}"
    elif mode == "script" and kb.get("scripts"):
        items  = "\n\n---\n".join(f"[{s['name']}]\n{s['content']}" for s in kb["scripts"][-5:])
        kb_ref = f"\n\nREFERENCE SCRIPTS FROM KNOWLEDGE BASE:\n{items}"

    if mode == "dialogue":
        return f"""You are a senior dialogue writer and sales communication expert for Aditya Birla Health Insurance (ABHI). Today is {today}.
You write natural, spoken-language dialogues for voice bots and human agents.{client_ctx}{kb_ref}

OUTPUT RULES — follow these exactly:
1. Always produce EXACTLY 5 dialogue variations.
2. Label every variation with this exact heading format:   ## VARIATION N: TITLE
   Where N is 1–5 and TITLE is one of: SHORT & SWEET / PROFESSIONAL / FRIENDLY & CONVERSATIONAL / PERSUASIVE / EMPATHETIC
3. Each dialogue must have realistic back-and-forth lines, NOT just an agent monologue.
4. Use {{customer_name}}, {{agent_name}}, {{policy_expiry_date}} as placeholders.
5. Use the language/tone specified by the user."""

    else:  # script
        return f"""You are an expert conversation flow script architect for ABHI voice AI systems. Today is {today}.
You build structured [STEP_X] scripts with conditional branching (→), validation rules, and dialogue templates.{client_ctx}{kb_ref}

OUTPUT RULES — follow these exactly:
1. Always produce EXACTLY 5 script variations.
2. Label every variation with this exact heading format:   ## VARIATION N: TITLE
   Where N is 1–5 and TITLE is one of: MINIMAL / COMPREHENSIVE / CUSTOMER-CENTRIC / CONVERSION-OPTIMISED / OBJECTION-RECOVERY
3. Use [STEP_X] labels, → arrows for branching, {{{{placeholders}}}}.
4. Each script must be directly implementable in a voice AI pipeline."""

# ── AI GENERATE ───────────────────────────────────────────────────────────────────
def run_generate(about, instructions, mode, kb, language):
    system = build_system(mode, kb, about)
    prompt = f"LANGUAGE: {language}\n\n{instructions if instructions.strip() else 'Generate variations.'}"
    return run_llm_request(system, prompt)

def run_chat(user_msg, about, mode, kb):
    system = build_system(mode, kb, about)
    return run_llm_request(f"[System Instruction: {system[:500]}]", user_msg)

# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Logo
    st.markdown("""
    <div class="sb-logo">
        <div class="sb-logo-text">🎯 DialogueBot</div>
        <div class="sb-logo-sub">ABHI · Powered by Gemini 1.5 Flash</div>
    </div>
    """, unsafe_allow_html=True)

    # New Chat button
    st.markdown('<div class="sb-new-chat">', unsafe_allow_html=True)
    if st.button("＋  New Chat", use_container_width=True, type="primary", key="btn_new"):
        start_new_chat()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Chat History
    st.markdown('<div class="sb-section-label">Chat History</div>', unsafe_allow_html=True)
    history = db_get_sessions()
    if not history:
        st.markdown('<div style="padding:8px 18px;font-size:0.78rem;color:#3a3d55">No chats yet. Start typing!</div>', unsafe_allow_html=True)
    else:
        for ch in history:
            is_active = ch["id"] == st.session_state.chat_id
            cls = "hist-card active" if is_active else "hist-card"
            mode_icon = "💬" if ch.get("mode") == "dialogue" else "📋"
            ts = ch.get("timestamp", "")[:10]
            col_t, col_b = st.columns([5, 1])
            with col_t:
                st.markdown(f"""
                <div class="{cls}">
                    <div class="hist-card-title">{mode_icon} {ch.get('title','Untitled')[:42]}</div>
                    <div class="hist-card-meta">{ts}</div>
                </div>""", unsafe_allow_html=True)
            with col_b:
                if st.button("›", key=f"ch_{ch['id']}", help="Open"):
                    load_chat(ch["id"])
                    st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # Knowledge Base
    st.markdown('<div class="sb-section-label">Knowledge Base</div>', unsafe_allow_html=True)
    kb = load_kb()
    kb_tab1, kb_tab2 = st.tabs(["📋 Scripts", "💬 Dialogues"])

    with kb_tab1:
        st.caption(f"{len(kb['scripts'])} saved")
        with st.expander("＋ Add Script"):
            sn = st.text_input("Name", key="sn", placeholder="e.g. Customer Regain v3")
            sc = st.text_area("Content", key="sc", height=100)
            if st.button("Save", key="btn_ks"):
                if sc.strip():
                    kb["scripts"].append({"id": str(uuid.uuid4()), "name": sn or f"Script {len(kb['scripts'])+1}", "content": sc.strip(), "added": datetime.now().isoformat()})
                    if save_kb(kb):
                        st.success("Saved!")
                        st.rerun()
        for i, s in enumerate(kb["scripts"][-6:]):
            c1, c2 = st.columns([5, 1])
            with c1: st.markdown(f'<div class="kb-chip">📄 {s["name"][:30]}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("×", key=f"ks_{i}"):
                    kb["scripts"] = [x for x in kb["scripts"] if x["id"] != s["id"]]
                    save_kb(kb); st.rerun()

    with kb_tab2:
        st.caption(f"{len(kb['dialogues'])} saved")
        with st.expander("＋ Add Dialogue"):
            dn = st.text_input("Name", key="dn", placeholder="e.g. Objection — Already Insured")
            dc = st.text_area("Content", key="dc", height=100)
            if st.button("Save", key="btn_kd"):
                if dc.strip():
                    kb["dialogues"].append({"id": str(uuid.uuid4()), "name": dn or f"Dialogue {len(kb['dialogues'])+1}", "content": dc.strip(), "added": datetime.now().isoformat()})
                    if save_kb(kb):
                        st.success("Saved!")
                        st.rerun()
        for i, d in enumerate(kb["dialogues"][-6:]):
            c1, c2 = st.columns([5, 1])
            with c1: st.markdown(f'<div class="kb-chip">💬 {d["name"][:30]}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("×", key=f"kd_{i}"):
                    kb["dialogues"] = [x for x in kb["dialogues"] if x["id"] != d["id"]]
                    save_kb(kb); st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN — two-column layout matching the sketch
# ─────────────────────────────────────────────────────────────────────────────
kb = load_kb()

# ── HEADER ──
hcol1, hcolM, hcol2 = st.columns([3, 2, 1])
with hcol1:
    st.markdown('<h1 style="font-family:\'Syne\',sans-serif;font-size:1.4rem;margin:0">DialogueBot · ABHI Optimizer</h1>', unsafe_allow_html=True)
with hcolM:
    st.session_state.llm_provider = st.selectbox(
        "Model Selector",
        options=["Gemini", "OpenAI", "Claude", "Groq/Meta"],
        index=["Gemini", "OpenAI", "Claude", "Groq/Meta"].index(st.session_state.llm_provider),
        label_visibility="collapsed"
    )
with hcol2:
    if st.button("＋ New Chat", use_container_width=True, type="primary", key="main_new"):
        start_new_chat()
        st.rerun()

st.markdown("<hr style='margin:12px 0 24px'>", unsafe_allow_html=True)

# ── 3 COLUMN LAYOUT: HISTORY | INPUT | OUTCOME ──
col_hist, col_left, col_right = st.columns([1, 2, 2], gap="large")

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 1 — Vertical History Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with col_hist:
    st.markdown('<div class="field-label" style="color:#7a7d9a">History</div>', unsafe_allow_html=True)
    sessions = db_get_sessions()
    if not sessions:
        st.markdown('<div style="font-size:0.75rem;color:#3a3d55;padding-top:10px">No history yet.</div>', unsafe_allow_html=True)
    for s in sessions:
        is_active = s["id"] == st.session_state.chat_id
        icon = "💬" if s["mode"] == "dialogue" else "📋"
        btn_style = "secondary" if not is_active else "primary"
        if st.button(f"{icon} {s['title'][:25]}...", key=f"hist_{s['id']}", use_container_width=True, type=btn_style):
            load_chat(s["id"])
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 2 — inputs
# ─────────────────────────────────────────────────────────────────────────────
with col_left:
    # ── ABOUT ──
    st.markdown('<div class="field-label">About — Define the Client</div>', unsafe_allow_html=True)
    about = st.text_area(
        "about", label_visibility="collapsed",
        value=st.session_state.about_val,
        height=120,
        placeholder=(
            "Describe the client / customer profile here…\n\n"
            "e.g. Male, 42 years, policy expired 3 months ago, last premium ₹18,000/yr, "
            "previously had individual plan with ABHI. May have switched to another provider."
        ),
        key="about_input",
    )

    # Save about to session so chat history title uses it
    if about != st.session_state.about_val:
        st.session_state.about_val = about

    # ── MODE — Script / Dialogue ──
    st.markdown('<div class="field-label">Type</div>', unsafe_allow_html=True)
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        if st.button(
            "💬 Dialogue",
            use_container_width=True,
            type="primary" if st.session_state.mode == "dialogue" else "secondary",
            key="btn_mode_d",
        ):
            if st.session_state.mode != "dialogue":
                st.session_state.mode = "dialogue"
                st.session_state.variations = None
                st.rerun()
    with m_col2:
        if st.button(
            "📋 Script",
            use_container_width=True,
            type="primary" if st.session_state.mode == "script" else "secondary",
            key="btn_mode_s",
        ):
            if st.session_state.mode != "script":
                st.session_state.mode = "script"
                st.session_state.variations = None
                st.rerun()

    # ── LANGUAGE ──
    st.markdown('<div class="field-label">Language</div>', unsafe_allow_html=True)
    language = st.selectbox(
        "lang", label_visibility="collapsed",
        options=["Hinglish (Hindi + English)", "Pure Hindi", "Pure English"],
        index=["Hinglish (Hindi + English)", "Pure Hindi", "Pure English"].index(st.session_state.lang_val),
        key="lang_select",
    )
    st.session_state.lang_val = language

    # ── INSTRUCTIONS ──
    st.markdown('<div class="field-label">Instructions — What do you want the bot to do?</div>', unsafe_allow_html=True)
    instructions = st.text_area(
        "instr", label_visibility="collapsed",
        value=st.session_state.instr_val,
        height=150,
        placeholder=(
            "Tell the bot what to generate…\n\n"
            "e.g. Generate a dialogue for when the customer says they already have LIC insurance "
            "and don't want to switch. Focus on porting benefits and the 10% discount offer."
        ),
        key="instr_input",
    )
    st.session_state.instr_val = instructions

    # ── GENERATE ──
    st.markdown("<br>", unsafe_allow_html=True)
    gen_label = f"✦ Generate {'Dialogues' if st.session_state.mode == 'dialogue' else 'Scripts'} (5 variations)"
    do_generate = st.button(gen_label, type="primary", use_container_width=True, key="btn_generate")

    # ── CHAT / REFINE SECTION ──
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="field-label">Chat & Refine</div>', unsafe_allow_html=True)

    # Show visible messages (skip meta tags)
    visible = [m for m in st.session_state.messages if not m["content"].startswith("[GENERATE")]
    
    if visible:
        # History Navigation (Show only if there's more than 1 turn to navigate)
        if len(visible) > 1:
            st.markdown('<div class="field-label">Conversation Navigator</div>', unsafe_allow_html=True)
            opts = list(range(len(visible)))
            st.session_state.history_index = st.select_slider(
                "Nav", 
                options=opts,
                value=st.session_state.history_index if st.session_state.history_index < len(visible) else len(visible)-1,
                label_visibility="collapsed",
                format_func=lambda x: f"Turn {x+1}",
                key=f"nav_select_{st.session_state.chat_id}_{len(visible)}"
            )
        else:
            st.session_state.history_index = 0

        # Display up to selected index
        for msg in visible[:st.session_state.history_index + 1]:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style="background:#14172a;border:1px solid #1e2235;border-radius:10px 10px 3px 10px;
                            padding:10px 14px;margin:6px 0 6px 24px;font-size:.85rem;color:#e2e4ed;">
                    🧑 {msg['content']}
                </div>""", unsafe_allow_html=True)
            else:
                content = msg["content"]
                # If it's the full variation block, show a summary in chat
                if "## VARIATION" in content:
                    st.markdown("""
                    <div style="background:#0f1117;border:1px dashed #2a2f50;border-radius:10px;
                                padding:8px 12px;margin:6px 24px 6px 0;font-size:.78rem;color:#4f8ef7;text-align:center;">
                        ✦ New variations generated (see right panel) ✦
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:#0f1117;border:1px solid #1c1f2e;border-radius:10px 10px 10px 3px;
                                padding:10px 14px;margin:6px 24px 6px 0;font-size:.85rem;color:#b0b3c8;white-space:pre-wrap;">
                        🤖 {content}
                    </div>""", unsafe_allow_html=True)

    follow_up = st.chat_input("Ask a follow-up or refine a variation…", key="chat_input")

# ─────────────────────────────────────────────────────────────────────────────
# HANDLE GENERATE (after UI rendered — no mid-render rerun)
# ─────────────────────────────────────────────────────────────────────────────
if do_generate:
    if not about.strip() and not instructions.strip():
        st.warning("Fill in at least the About or Instructions field first.")
    else:
        # Push about to chat history as first message if not already there
        first_msg = f"[CLIENT] {about.strip()[:120]}" if about.strip() else ""
        instr_msg = instructions.strip() or "Generate re-engagement call variations."
        combined  = f"{first_msg}\n\n[INSTRUCTIONS] {instr_msg}".strip()

        raw = run_generate(about, instructions, st.session_state.mode, kb, language)
        if raw:
            st.session_state.messages.append({"role": "user",      "content": f"[GENERATE] {combined[:100]}"})
            st.session_state.messages.append({"role": "assistant", "content": raw})
            st.session_state.variations = parse_variations(raw)
            
            # Persist to DB
            first_user = next((m["content"] for m in st.session_state.messages if m["role"] == "user"), "New Chat")
            title = re.sub(r'\[.*?\]', '', first_user).strip()[:60]
            db_save_session(st.session_state.chat_id, title, st.session_state.mode, about)
            db_save_message(st.session_state.chat_id, "user", f"[GENERATE] {combined[:100]}")
            db_save_message(st.session_state.chat_id, "assistant", raw)
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# HANDLE CHAT FOLLOW-UP
# ─────────────────────────────────────────────────────────────────────────────
if follow_up:
    st.session_state.messages.append({"role": "user", "content": follow_up})
    bot_reply = run_chat(follow_up, about, st.session_state.mode, kb)
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    db_save_message(st.session_state.chat_id, "user", follow_up)
    db_save_message(st.session_state.chat_id, "assistant", bot_reply)
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 3 — outcomes / variations
# ─────────────────────────────────────────────────────────────────────────────
with col_right:
    mode_badge = "dialogue" if st.session_state.mode == "dialogue" else "script"
    st.markdown(f"""
    <div class="out-header">
        Outcomes
        <span class="out-badge">{mode_badge} · 5 variations</span>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.variations:
        st.markdown("""
        <div class="info-box">
            <div class="icon">✦</div>
            Fill in the <strong>About</strong> and <strong>Instructions</strong> on the left,
            choose your language, then hit <strong>Generate</strong>.<br><br>
            Your 5 variations will appear here as <strong>a · b · c · d · e</strong>.
        </div>""", unsafe_allow_html=True)
    else:
        for idx, var in enumerate(st.session_state.variations[:5]):
            letter = VARIATION_LABELS[idx] if idx < len(VARIATION_LABELS) else str(idx + 1)
            vcls   = VAR_CLASSES[idx]       if idx < len(VAR_CLASSES)      else "v1"
            title  = var.get("title", f"Variation {idx+1}")
            body   = var.get("content", "")

            st.markdown(f"""
            <div class="var-wrap">
                <div class="var-card {vcls}">
                    <div class="var-head">
                        <div class="var-letter">{letter})</div>
                        <div class="var-title-text">{title}</div>
                    </div>
                    <div class="var-body">{body}</div>
                </div>
            </div>""", unsafe_allow_html=True)

            # Action buttons per card
            b1, b2, b3 = st.columns([2, 2, 3])
            with b1:
                st.download_button(
                    "⬇ Download",
                    data=f"# {title}\n\n{body}",
                    file_name=f"var_{letter}_{st.session_state.mode}_{st.session_state.chat_id[:6]}.txt",
                    mime="text/plain",
                    key=f"dl_{idx}",
                    use_container_width=True,
                )
            with b2:
                if st.button("💾 Save to KB", key=f"kb_{idx}", use_container_width=True):
                    kb_fresh = load_kb()
                    entry = {"id": str(uuid.uuid4()), "name": title, "content": body, "added": datetime.now().isoformat()}
                    if st.session_state.mode == "dialogue":
                        kb_fresh["dialogues"].append(entry)
                    else:
                        kb_fresh["scripts"].append(entry)
                    if save_kb(kb_fresh):
                        st.toast(f"Saved '{title[:30]}' to KB!")

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:32px 0 16px;font-size:.7rem;color:#2a2d45;">
    DialogueBot · ABHI Voice Bot Optimizer · Gemini 1.5 Flash
</div>""", unsafe_allow_html=True)
